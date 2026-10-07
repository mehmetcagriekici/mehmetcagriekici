import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from pypdf.errors import PyPdfError

from matching.matcher.matcher import is_fit_fact
from tailoring.gaps.gaps import GapDecision, decide_gaps
from tailoring.llm.client import OllamaError, OutputTooLongError, PromptTooLongError, llm_ollama
from tailoring.prompts.application import build_application_prompt
from tailoring.prompts.cover_letter import build_cover_letter_prompt
from tailoring.prompts.resume import build_resume_prompt
from tailoring.prompts.system_prompt import SYSTEM_PROMPT
from tailoring.write.write import (
    RESUME_JSON_SCHEMA,
    ParseResult,
    WriteError,
    WriteResult,
    application_answers_schema,
    cover_letter_schema,
    parse_application_answers,
    write_cover_letter,
    write_resume,
)

logger = logging.getLogger(__name__)


@dataclass
class GenerateResult:
    # None means that step was never reached (aborted earlier, or the LLM
    # call itself failed) -- a WriteResult/ParseResult with .error set means
    # it was reached and failed. See write/README.md's WriteError note.
    resume: WriteResult | None = None
    cover_letter: WriteResult | None = None
    application: ParseResult | None = None
    # every known gap's applies/doesn't-apply decision and why (gaps/gaps.py),
    # for the review email and review_gate/ -- set before any LLM call
    gap_decisions: list[GapDecision] = field(default_factory=list)


# A broken LLM response has no content to show anyone, and there are no
# retries (see write/README.md) -- so the application is dead, and spending
# the single Ollama slot on its remaining calls would only delay every other
# posting queued behind it. OVERFLOW is deliberately not here: that content is
# real and goes to the user for approve/reject, so generation continues. (For
# what each failure means for the posting afterwards -- excluded or retried
# next run -- see write.py's CONTENT_FAILURES / INFRASTRUCTURE_FAILURES.)
_BROKEN_RESPONSE = (WriteError.INVALID_JSON, WriteError.VALIDATION_ERROR)


# Facts kept out of the resume and cover letter prompts: exactly the ones
# matching doesn't count as fit (matching.matcher.is_fit_fact) -- known_gap:*
# (the cover letter gets the gaps that apply in their own block), education
# (GPA, degree status), professional_experience, job_preference:* (screening
# answers like visa and salary), and the logistics preferences (work_mode,
# regions...: "remote preferred" doesn't belong in a letter for an on-site
# role). Otherwise a fact search happened to return could put a gap the
# posting never asked about straight back into the letter. One definition,
# shared with matching, instead of a second list here that drifted from it.
# The application call keeps all facts -- a free-text answer about experience
# or education must stay honest.
def _writing_facts(facts: list[dict]) -> list[dict]:
    return [f for f in facts if is_fit_fact(f["doc_id"])]


# Job posting IDs come from outside (ATS data), so they're encoded into a safe
# filename stem before touching the filesystem -- an ID containing "/" or ".."
# must not be able to escape output_dir. Letters, digits, "_" and "-" stay;
# every other character becomes "~" plus its UTF-8 bytes in hex (":" -> "~3a").
# "~" itself is always encoded, so the mapping is reversible: two different
# IDs can never share a stem. (Replacing with "_" made "greenhouse:acme_co:1"
# and "greenhouse:acme:co_1" collide -- in tracking/, which keys its files by
# this stem, that would be a silent false "already applied".) tracking/ (not
# yet built) should reuse this function.
_FILENAME_SAFE = re.compile(r"[A-Za-z0-9_-]")


def filename_stem(posting_id: object) -> str:
    text = str(posting_id)
    if not re.search(r"[A-Za-z0-9]", text):
        raise ValueError(f"job posting id {posting_id!r} has no letters or digits")
    return "".join(
        char if _FILENAME_SAFE.fullmatch(char) else "".join(f"~{b:02x}" for b in char.encode())
        for char in text
    )


# One LLM call, with every failure llm_ollama() can raise mapped to its
# WriteError -- explicitly, by type. Returns (response, None) or (None, error).
async def _call_llm(step: str, prompt: str, schema: dict) -> tuple[str | None, WriteError | None]:
    try:
        return await llm_ollama(prompt, SYSTEM_PROMPT, schema), None
    except PromptTooLongError:
        logger.exception("generate: %s prompt too long", step)
        return None, WriteError.PROMPT_TOO_LONG
    except OutputTooLongError:
        logger.exception("generate: %s output hit the token cap", step)
        return None, WriteError.OUTPUT_TOO_LONG
    except OllamaError:
        logger.exception("generate: %s LLM call failed", step)
        return None, WriteError.LLM_FAILURE


# When a later step kills the application (a content or infrastructure
# failure), PDFs already rendered for it are useless -- the application has
# concluded -- so they're deleted here rather than left for a caller that may
# never come. Their parsed text stays in .content.
def _discard_rendered(result: GenerateResult) -> GenerateResult:
    for written in (result.resume, result.cover_letter):
        if written is not None and written.path is not None:
            Path(written.path).unlink(missing_ok=True)
            written.path = None
    return result


async def generate(
    facts: list[dict],
    job_posting: dict,
    profile: dict,
    questions: list[dict],
    known_gaps: list[dict],
    output_dir: str,
) -> GenerateResult:
    # No implicit None-checks: llm_ollama raises OllamaError instead of
    # returning None on failure (see llm/client.py), and write_resume/
    # write_cover_letter raise playwright.async_api.Error/pypdf.errors.PyPdfError
    # for the failure modes they don't fully resolve into a WriteResult
    # themselves (bad JSON/failed validation/overflow do; a Chromium crash or an
    # unreadable output PDF don't). Both are caught here, explicitly, and turned
    # into the matching WriteError. Anything else is a genuine bug and is left
    # to propagate rather than being caught and hidden.
    result = GenerateResult()
    # profile.json: its `personal` block fills both documents' headers, its
    # `summary` (the candidate's own words) anchors the resume summary
    personal = profile["personal"]

    # known_gaps is known-gaps.json's full list, independent of hybrid_search's
    # ranking (option (b), ../CLAUDE.md). Empty means the caller didn't load it
    # -- every gap would silently count as "doesn't apply".
    if not known_gaps:
        raise ValueError("generate: known_gaps is empty -- load known-gaps.json")
    # Which gaps the cover letter raises is decided here, in code, before any
    # LLM call: only the ones the posting actually asks about.
    result.gap_decisions = decide_gaps(job_posting, known_gaps)
    gaps_to_raise = [d for d in result.gap_decisions if d.applies]
    writing_facts = _writing_facts(facts)

    # Per-application filenames, keyed by job posting ID (the same convention
    # tracking/ is designed to use for its per-application JSON files -- see
    # ../tracking/README.md; not built yet). Without this, every call to generate()
    # would write to the same "resume.pdf"/"cover_letter.pdf", silently
    # overwriting whatever the previous posting produced. A missing "id" is a
    # malformed job_posting -- let the KeyError propagate rather than papering
    # over it with a fallback name. output_dir is required so files never land
    # in whatever directory the process happens to run from.
    stem = filename_stem(job_posting["id"])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    resume_path = str(out / f"{stem}_resume.pdf")
    cover_letter_path = str(out / f"{stem}_cover_letter.pdf")

    # generate resume
    response, error = await _call_llm(
        "resume",
        build_resume_prompt(writing_facts, job_posting, profile["summary"]),
        RESUME_JSON_SCHEMA,
    )
    if error:
        result.resume = WriteResult(path=None, error=error)
        return result
    try:
        result.resume = await write_resume(response, personal, resume_path)
    except (PlaywrightError, PyPdfError):
        logger.exception("generate: rendering the resume failed")
        # a crashed render may have left a partial file behind
        Path(resume_path).unlink(missing_ok=True)
        result.resume = WriteResult(path=None, error=WriteError.RENDER_FAILURE)
        return result
    if result.resume.error in _BROKEN_RESPONSE:
        return result

    # generate cover letter
    response, error = await _call_llm(
        "cover letter",
        build_cover_letter_prompt(writing_facts, job_posting, gaps_to_raise),
        cover_letter_schema(stack_gap_allowed=any(d.requirements for d in gaps_to_raise)),
    )
    if error:
        result.cover_letter = WriteResult(path=None, error=error)
        return _discard_rendered(result)
    try:
        result.cover_letter = await write_cover_letter(
            response,
            personal,
            output_path=cover_letter_path,
            # each applicable gap's own text, word for word; the model's
            # stack_gap sentence goes right after the gap that quoted the
            # posting's years requirement
            gap_texts=[(d.text, bool(d.requirements)) for d in gaps_to_raise],
            role=job_posting.get("title"),
            company=job_posting.get("company"),
        )
    except (PlaywrightError, PyPdfError):
        logger.exception("generate: rendering the cover letter failed")
        Path(cover_letter_path).unlink(missing_ok=True)
        result.cover_letter = WriteResult(path=None, error=WriteError.RENDER_FAILURE)
        return _discard_rendered(result)
    if result.cover_letter.error in _BROKEN_RESPONSE:
        return _discard_rendered(result)

    # generate form answers -- skipped when the form has no free-text
    # questions, rather than spending a full LLM call on an empty object
    if not questions:
        result.application = ParseResult(answers={})
        return result
    response, error = await _call_llm(
        "application",
        build_application_prompt(facts, job_posting, questions),
        application_answers_schema(questions),
    )
    if error:
        result.application = ParseResult(answers=None, error=error)
        return _discard_rendered(result)
    # parse_application_answers is sync -- no rendering, so no Playwright/pypdf
    # failure mode to catch here the way write_resume/write_cover_letter have.
    result.application = parse_application_answers(response, questions)
    if result.application.error in _BROKEN_RESPONSE:
        return _discard_rendered(result)

    return result
