# write.py
import logging
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright, Playwright
from pypdf import PdfReader

logger = logging.getLogger(__name__)

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


async def _render_to_pdf(html_content: str, output_path: str) -> str | None:
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
        return None

    return output_path


async def write_resume(
    resume: dict,
    personal: dict,
    output_path: str = "resume.pdf",
) -> str | None:
    """resume: RESUME_SCHEMA-shaped dict (see prompts/resume.py).
    personal: profile.json's "personal" block (name/email/phone/location/github/linkedin)."""
    skills_grouped = [
        (_category_label(category), items) for category, items in resume["skills"].items()
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


async def write_cover_letter(
    letter: dict,
    personal: dict,
    company: str | None = None,
    output_path: str = "cover_letter.pdf",
) -> str | None:
    """letter: COVER_LETTER_SCHEMA-shaped dict (see prompts/cover_letter.py).
    personal: profile.json's "personal" block (name/email/phone/location/github/linkedin)."""
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
