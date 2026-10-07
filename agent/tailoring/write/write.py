import copy
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import Playwright, async_playwright
from pydantic import AfterValidator, BaseModel, BeforeValidator, TypeAdapter, ValidationError
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class WriteError(Enum):
    """Why a call didn't produce a usable result — a caller needs to tell these apart:
    INVALID_JSON/VALIDATION_ERROR are a broken LLM response (no content exists
    to act on) — this includes a "not provided" placeholder in a required
    resume/cover-letter field, and application answers whose keys don't match
    the questions asked. OVERFLOW is specific to write_resume()/write_cover_letter():
    real content that's too long and must route to the user for approve/reject
    (see ../README.md) — the result still carries the parsed
    content and the rendered file's path, for the review email and tracking/.
    parse_application_answers() never produces it, since there's no page to
    overflow. UNANSWERED/ANSWER_TOO_LONG are its counterparts: real answers exist
    (returned alongside the error) but at least one says "not provided" or is
    over the question's max_length, so the application needs human review
    before anything is submitted. RENDER_FAILURE is an
    infrastructure failure during rendering itself (Playwright/Chromium, or an
    unreadable output PDF) — not raised by write.py, which doesn't catch these;
    a caller that does catch playwright.async_api.Error / pypdf.errors.PyPdfError
    around a write_*() call constructs this value itself (see tailoring/generate.py).
    LLM_FAILURE is earlier still: the Ollama call itself never produced a
    response (llm.client.OllamaError) — there's no LLM output at all to pass to
    write_*()/parse_application_answers(), so those functions never see this
    case either; a caller catches OllamaError and constructs this value itself,
    same pattern as RENDER_FAILURE."""

    INVALID_JSON = "invalid_json"
    VALIDATION_ERROR = "validation_error"
    OVERFLOW = "overflow"
    RENDER_FAILURE = "render_failure"
    LLM_FAILURE = "llm_failure"
    UNANSWERED = "unanswered"
    ANSWER_TOO_LONG = "answer_too_long"
    # the prompt might not fit Ollama's context window (llm.client.PromptTooLongError),
    # caught before anything was sent -- a caller constructs this, like LLM_FAILURE
    PROMPT_TOO_LONG = "prompt_too_long"
    # the model hit NUM_PREDICT before finishing (llm.client.OutputTooLongError)
    # -- a caller constructs this, like LLM_FAILURE
    OUTPUT_TOO_LONG = "output_too_long"


# How a failure affects the posting (decided 2026-10-07). Content failures are
# about *this posting* -- the model produced bad output for it, or its prompt
# can't fit -- and would likely repeat, so they warrant a permanent exclusion
# in tracking/. Infrastructure failures are about the machine (Ollama down or
# timing out, Chromium crashing): the posting itself is fine and comes back
# next run, and a runner should stop the run rather than keep failing through
# its best-ranked postings. OVERFLOW/UNANSWERED/ANSWER_TOO_LONG are neither --
# real content that routes to the user's review.
CONTENT_FAILURES = frozenset(
    {
        WriteError.INVALID_JSON,
        WriteError.VALIDATION_ERROR,
        WriteError.PROMPT_TOO_LONG,
        # same facts, temperature 0.2: it would most likely overflow again --
        # as an infrastructure failure it would stop every future run from the
        # top of the ranking
        WriteError.OUTPUT_TOO_LONG,
    }
)
INFRASTRUCTURE_FAILURES = frozenset({WriteError.LLM_FAILURE, WriteError.RENDER_FAILURE})


# content is the parsed Resume/CoverLetter whenever the LLM response parsed and
# validated — including on OVERFLOW, where path also points at the rendered
# (too-long) file. The review email and tracking/ need the full text, and the
# on-disk PDF is deleted once the application concludes (../../tracking/README.md), so
# the text can't be recovered from the file later.
@dataclass
class WriteResult:
    path: str | None
    error: WriteError | None = None
    content: "Resume | CoverLetter | None" = None


# flagged: per-field reason for UNANSWERED/ANSWER_TOO_LONG, so the review email
# can point at the exact questions that need attention.
@dataclass
class ParseResult:
    answers: dict[str, str] | None
    error: WriteError | None = None
    flagged: dict[str, WriteError] = field(default_factory=dict)


# The placeholder the system prompt tells the model to use when the facts don't
# cover a question (prompts/system_prompt.py). Legitimate only in application
# form answers; in a resume or cover letter it would be printed straight into
# the PDF, so optional fields drop it and required fields reject it.
NOT_PROVIDED = "not provided"


def _is_placeholder(value: str) -> bool:
    return value.strip().rstrip(".").lower() in ("", NOT_PROVIDED)


def _reject_placeholder(value: str) -> str:
    if _is_placeholder(value):
        raise ValueError(f"placeholder {value!r} in a required field")
    return value


def _placeholder_to_none(value: object) -> object:
    if isinstance(value, str) and _is_placeholder(value):
        return None
    return value


RequiredText = Annotated[str, AfterValidator(_reject_placeholder)]
OptionalText = Annotated[str | None, BeforeValidator(_placeholder_to_none)]


# The application call's field_ids are posting-specific (whatever form fields
# that job's application asks) — there's no fixed schema like RESUME_SCHEMA to
# name a pydantic model's fields after, so this validates only the structural
# shape the prompt actually promises (prompts/application.py: "a JSON object
# mapping each field_id to its answer as a string").
_ApplicationAnswers = TypeAdapter(dict[str, str])


# Structured-output schema for the application call, built per posting: exactly
# one required string per real field_id, nothing else allowed -- so the model
# can't return the prompt example's placeholder keys ("field_id_1") the way the
# 2026-08-05 run did. max_length is deliberately left out: constrained decoding
# would enforce it by cutting the answer off mid-sentence, silently -- it needs
# a real check after generation instead.
def application_answers_schema(questions: list[dict]) -> dict:
    # as strings: JSON object keys always are, so an integer id would never match
    field_ids = [str(q["field_id"]) for q in questions]
    return {
        "type": "object",
        "properties": {field_id: {"type": "string"} for field_id in field_ids},
        "required": field_ids,
        "additionalProperties": False,
    }


# A4 page size, matching the root cover-letter workflow's page geometry
PAGE_WIDTH_MM = 210
PAGE_HEIGHT_MM = 297
MARGIN_MM = 15
BASE_FONT_PT = 10.5

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


# Links in profile data may lack a scheme ("boot.dev/u/..."); in an href that's
# a relative link, which goes nowhere in a PDF. Every template href goes
# through this, so the data doesn't have to be perfect.
def _ensure_scheme(url: str) -> str:
    return url if re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I) else f"https://{url}"


_env.filters["ensure_scheme"] = _ensure_scheme


# Mirrors RESUME_SCHEMA in prompts/resume.py — validates the LLM's JSON
# response before it reaches the template, instead of a raw KeyError/TypeError
# surfacing from inside Jinja rendering on a malformed field.
class Project(BaseModel):
    name: RequiredText
    dates: RequiredText
    tech: RequiredText
    description: RequiredText
    bullets: list[RequiredText]
    status: OptionalText = None
    repo: OptionalText = None


class Certification(BaseModel):
    name: RequiredText
    dates: RequiredText
    details: RequiredText
    verification_url: OptionalText = None


class Resume(BaseModel):
    summary: RequiredText
    skills: dict[str, list[RequiredText]]
    projects: list[Project]
    certifications: list[Certification] = []


# Mirrors COVER_LETTER_SCHEMA in prompts/cover_letter.py.
# What the model writes for a cover letter: only the parts that need judgment
# about this posting. Everything fixed is written by code (write_cover_letter):
# the opening sentence naming the role and company, the gaps paragraph (the
# user's own known-gaps.json `text`, word for word), and the closing. Left to
# the model, those slots drew genre filler ("I am excited to apply...") and,
# once, an instruction from the gaps file copied into a letter. Field order is
# generation order under Ollama's constrained decoding.
class CoverLetterDraft(BaseModel):
    # 1-2 sentences continuing the code-written opening: why this role,
    # linking a specific fact to a specific requirement
    why: RequiredText
    experience: RequiredText
    # one sentence naming a narrower, stack-specific experience gap for the
    # posting's quoted requirement -- only allowed (in the schema) when one
    # was quoted, and optional even then
    stack_gap: OptionalText = None


# The letter as sent -- assembled from code-written parts and the draft. Kept
# as WriteResult.content, so the review email and tracking/ get the full text.
class CoverLetter(BaseModel):
    opening: str
    experience: str
    gaps: str | None = None
    closing: str


# JSON schemas for Ollama structured outputs (llm/client.py's response_schema):
# the same models that validate a response also constrain its generation, so
# the two can't drift apart.
RESUME_JSON_SCHEMA = Resume.model_json_schema()


# The cover letter draft's schema, built per call: stack_gap exists only when
# the posting quoted a years requirement for it to address -- otherwise the
# model has no field to put a gap in at all.
def cover_letter_schema(stack_gap_allowed: bool) -> dict:
    schema = copy.deepcopy(CoverLetterDraft.model_json_schema())
    if not stack_gap_allowed:
        del schema["properties"]["stack_gap"]
    return schema


# The one sentence of the opening that code writes; the model's `why` follows.
def opening_sentence(role: str | None, company: str | None) -> str:
    if role and company:
        return f"I'm applying for the {role} role at {company}."
    if role:
        return f"I'm applying for the {role} role."
    if company:
        return f"I'm applying for the open role at {company}."
    return "I'm applying for this role."


CLOSING = "Thank you for considering my application."


def _today() -> str:
    today = date.today()
    return f"{today:%B} {today.day}, {today:%Y}"


# Known source_of_truth skill categories (see profile.json) whose label isn't
# just Title Case of the key with underscores turned to spaces.
_CATEGORY_LABELS = {
    "ai_ml": "AI/ML",
    "devops": "DevOps",
}


def _category_label(category: str) -> str:
    return _CATEGORY_LABELS.get(category, category.replace("_", " ").title())


async def _render(playwright: Playwright, html_content: str, output_path: str) -> None:
    browser = await playwright.chromium.launch()
    context = await browser.new_context()
    page = await context.new_page()

    await page.set_content(html_content, wait_until="networkidle")
    await page.emulate_media(media="print")

    await page.pdf(
        path=output_path,
        width=f"{PAGE_WIDTH_MM}mm",
        height=f"{PAGE_HEIGHT_MM}mm",
        print_background=True,
        margin={
            "top": f"{MARGIN_MM}mm",
            "bottom": f"{MARGIN_MM}mm",
            "left": f"{MARGIN_MM}mm",
            "right": f"{MARGIN_MM}mm",
        },
        # Prefer the CSS @page size we defined
        prefer_css_page_size=True,
    )

    await context.close()
    await browser.close()


async def _render_to_pdf(
    html_content: str, output_path: str, content: "Resume | CoverLetter"
) -> WriteResult:
    async with async_playwright() as playwright:
        await _render(playwright, html_content, output_path)

    # @page only sets the printed page's size — it doesn't clip. Templates leave
    # content free to flow past one page; overflow is *detected* here (page-count
    # check), never silently truncated, since a resume cut off mid-sentence must
    # never ship unnoticed.
    page_count = len(PdfReader(output_path).pages)
    if page_count != 1:
        # One page is a hard constraint (../README.md) — an
        # overflow must route to the user for review, never ship or auto-retry.
        # That routing (email + approve/reject) isn't built yet. The path is
        # still returned: the file stays on disk until the user answers.
        logger.warning(
            "write: %s rendered to %d pages, expected exactly 1", output_path, page_count
        )
        return WriteResult(path=output_path, error=WriteError.OVERFLOW, content=content)

    return WriteResult(path=output_path, content=content)


async def write_resume(
    llm_response: str,
    personal: dict,
    output_path: str,
) -> WriteResult:
    """llm_response: the resume call's raw JSON string (RESUME_SCHEMA, see prompts/resume.py).
    personal: profile.json's "personal" block (name/email/phone/location/github/linkedin)."""
    try:
        resume = Resume.model_validate(json.loads(llm_response))
    except json.JSONDecodeError as e:
        logger.warning("write_resume: invalid JSON: %s", e)
        return WriteResult(path=None, error=WriteError.INVALID_JSON)
    except ValidationError as e:
        logger.warning("write_resume: schema validation failed: %s", e)
        return WriteResult(path=None, error=WriteError.VALIDATION_ERROR)

    skills_grouped = [
        (_category_label(category), items) for category, items in resume.skills.items()
    ]

    template = _env.get_template("resume.html")
    html_content = template.render(
        resume=resume,
        personal=personal,
        skills_grouped=skills_grouped,
        margin_mm=MARGIN_MM,
        base_font_pt=BASE_FONT_PT,
    )

    return await _render_to_pdf(html_content, output_path, resume)


def parse_application_answers(llm_response: str, questions: list[dict]) -> ParseResult:
    """llm_response: the application call's raw JSON string ({field_id: answer},
    see prompts/application.py). questions: the same list the prompt was built
    from ({field_id, question, max_length?}). No template, no PDF —
    form_automation/ (not yet built) is the intended consumer of the returned dict."""
    try:
        answers = _ApplicationAnswers.validate_python(json.loads(llm_response))
    except json.JSONDecodeError as e:
        logger.warning("parse_application_answers: invalid JSON: %s", e)
        return ParseResult(answers=None, error=WriteError.INVALID_JSON)
    except ValidationError as e:
        logger.warning("parse_application_answers: schema validation failed: %s", e)
        return ParseResult(answers=None, error=WriteError.VALIDATION_ERROR)

    # The structured-output schema already forces exactly these keys; this
    # guards against a model/Ollama version that doesn't honor it.
    expected = {str(q["field_id"]) for q in questions}
    if set(answers) != expected:
        logger.warning(
            "parse_application_answers: field_id mismatch, missing=%s unexpected=%s",
            sorted(expected - set(answers)),
            sorted(set(answers) - expected),
        )
        return ParseResult(answers=None, error=WriteError.VALIDATION_ERROR)

    flagged: dict[str, WriteError] = {}
    for question in questions:
        field_id = str(question["field_id"])
        answer = answers[field_id]
        max_length = question.get("max_length")
        if _is_placeholder(answer):
            flagged[field_id] = WriteError.UNANSWERED
        elif max_length and len(answer) > max_length:
            flagged[field_id] = WriteError.ANSWER_TOO_LONG

    if flagged:
        # One error per result: ANSWER_TOO_LONG wins, since the platform would
        # reject or truncate it outright; per-field detail stays in flagged.
        if WriteError.ANSWER_TOO_LONG in flagged.values():
            error = WriteError.ANSWER_TOO_LONG
        else:
            error = WriteError.UNANSWERED
        logger.warning("parse_application_answers: %s: %s", error.value, flagged)
        return ParseResult(answers=answers, error=error, flagged=flagged)

    return ParseResult(answers=answers)


async def write_cover_letter(
    llm_response: str,
    personal: dict,
    output_path: str,
    gap_texts: list[tuple[str, bool]],
    role: str | None = None,
    company: str | None = None,
) -> WriteResult:
    """llm_response: the cover letter call's raw JSON string (a CoverLetterDraft,
    see prompts/cover_letter.py).
    personal: profile.json's "personal" block (name/email/phone/location/github/linkedin).
    gap_texts: for each known gap that applies to this posting, in order, its
    known-gaps.json `text` and whether the model's stack_gap sentence belongs
    right after it (the gap that quoted the posting's years requirement).
    role, company: the posting's title and company, for the opening sentence."""
    try:
        draft = CoverLetterDraft.model_validate(json.loads(llm_response))
    except json.JSONDecodeError as e:
        logger.warning("write_cover_letter: invalid JSON: %s", e)
        return WriteResult(path=None, error=WriteError.INVALID_JSON)
    except ValidationError as e:
        logger.warning("write_cover_letter: schema validation failed: %s", e)
        return WriteResult(path=None, error=WriteError.VALIDATION_ERROR)

    # The per-call schema already forbids this; checked again so a model that
    # ignores the schema can't add a gap sentence nobody asked for.
    stack_gap_allowed = any(wants for _, wants in gap_texts)
    if draft.stack_gap is not None and not stack_gap_allowed:
        logger.warning("write_cover_letter: stack_gap present but no requirement was quoted")
        return WriteResult(path=None, error=WriteError.VALIDATION_ERROR)

    gap_sentences = []
    for text, wants_stack_gap in gap_texts:
        gap_sentences.append(text)
        if wants_stack_gap and draft.stack_gap is not None:
            gap_sentences.append(draft.stack_gap)
    letter = CoverLetter(
        opening=f"{opening_sentence(role, company)} {draft.why}",
        experience=draft.experience,
        gaps=" ".join(gap_sentences) or None,
        closing=CLOSING,
    )

    template = _env.get_template("cover_letter.html")
    html_content = template.render(
        letter=letter,
        personal=personal,
        company=company,
        today=_today(),
        margin_mm=MARGIN_MM,
        base_font_pt=BASE_FONT_PT,
    )

    return await _render_to_pdf(html_content, output_path, letter)
