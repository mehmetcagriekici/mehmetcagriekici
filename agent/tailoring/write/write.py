# write.py
import json
import logging
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright, Playwright
from pydantic import BaseModel, TypeAdapter, ValidationError
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class WriteError(Enum):
    """Why a call didn't produce a result — a caller needs to tell these apart:
    INVALID_JSON/VALIDATION_ERROR are a broken LLM response (no content exists
    to act on). OVERFLOW is specific to write_resume()/write_cover_letter():
    real content that's too long and must route to the user for approve/reject
    (see ../README.md, ../../CLAUDE.md) — parse_application_answers() never
    produces it, since there's no page to overflow."""

    INVALID_JSON = "invalid_json"
    VALIDATION_ERROR = "validation_error"
    OVERFLOW = "overflow"


@dataclass
class WriteResult:
    path: str | None
    error: WriteError | None = None


@dataclass
class ParseResult:
    answers: dict[str, str] | None
    error: WriteError | None = None


# The application call's field_ids are posting-specific (whatever form fields
# that job's application asks) — there's no fixed schema like RESUME_SCHEMA to
# name a pydantic model's fields after, so this validates only the structural
# shape the prompt actually promises (prompts/application.py: "a JSON object
# mapping each field_id to its answer as a string").
_ApplicationAnswers = TypeAdapter(dict[str, str])


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


# Mirrors RESUME_SCHEMA in prompts/resume.py — validates the LLM's JSON
# response before it reaches the template, instead of a raw KeyError/TypeError
# surfacing from inside Jinja rendering on a malformed field.
class Project(BaseModel):
    name: str
    dates: str
    tech: str
    description: str
    bullets: list[str]
    status: str | None = None
    repo: str | None = None


class Certification(BaseModel):
    name: str
    dates: str
    details: str
    verification_url: str | None = None


class Resume(BaseModel):
    summary: str
    skills: dict[str, list[str]]
    projects: list[Project]
    certifications: list[Certification] = []


# Mirrors COVER_LETTER_SCHEMA in prompts/cover_letter.py.
class CoverLetter(BaseModel):
    opening: str
    experience: str
    closing: str
    gaps: str | None = None


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


async def _render_to_pdf(html_content: str, output_path: str) -> WriteResult:
    async with async_playwright() as playwright:
        await _render(playwright, html_content, output_path)

    # @page only sets the printed page's size — it doesn't clip. Templates leave
    # content free to flow past one page; overflow is *detected* here (page-count
    # check), never silently truncated, since a resume cut off mid-sentence must
    # never ship unnoticed.
    page_count = len(PdfReader(output_path).pages)
    if page_count != 1:
        # One page is a hard constraint (../README.md, ../../CLAUDE.md) — an
        # overflow must route to the user for review, never ship or auto-retry.
        # That routing (email + approve/reject) isn't built yet; for now this
        # only refuses to hand back a path for a document that doesn't qualify.
        logger.warning(
            "write: %s rendered to %d pages, expected exactly 1", output_path, page_count
        )
        return WriteResult(path=None, error=WriteError.OVERFLOW)

    return WriteResult(path=output_path)


async def write_resume(
    llm_response: str,
    personal: dict,
    output_path: str = "resume.pdf",
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

    return await _render_to_pdf(html_content, output_path)


def parse_application_answers(llm_response: str) -> ParseResult:
    """llm_response: the application call's raw JSON string ({field_id: answer},
    see prompts/application.py). No template, no PDF — form_automation/ (not yet
    built) is the intended consumer of the returned dict."""
    try:
        answers = _ApplicationAnswers.validate_python(json.loads(llm_response))
    except json.JSONDecodeError as e:
        logger.warning("parse_application_answers: invalid JSON: %s", e)
        return ParseResult(answers=None, error=WriteError.INVALID_JSON)
    except ValidationError as e:
        logger.warning("parse_application_answers: schema validation failed: %s", e)
        return ParseResult(answers=None, error=WriteError.VALIDATION_ERROR)

    return ParseResult(answers=answers)


async def write_cover_letter(
    llm_response: str,
    personal: dict,
    company: str | None = None,
    output_path: str = "cover_letter.pdf",
) -> WriteResult:
    """llm_response: the cover letter call's raw JSON string (COVER_LETTER_SCHEMA, see
    prompts/cover_letter.py).
    personal: profile.json's "personal" block (name/email/phone/location/github/linkedin)."""
    try:
        letter = CoverLetter.model_validate(json.loads(llm_response))
    except json.JSONDecodeError as e:
        logger.warning("write_cover_letter: invalid JSON: %s", e)
        return WriteResult(path=None, error=WriteError.INVALID_JSON)
    except ValidationError as e:
        logger.warning("write_cover_letter: schema validation failed: %s", e)
        return WriteResult(path=None, error=WriteError.VALIDATION_ERROR)

    template = _env.get_template("cover_letter.html")
    html_content = template.render(
        letter=letter,
        personal=personal,
        company=company,
        today=_today(),
        margin_mm=MARGIN_MM,
        base_font_pt=BASE_FONT_PT,
    )

    return await _render_to_pdf(html_content, output_path)
