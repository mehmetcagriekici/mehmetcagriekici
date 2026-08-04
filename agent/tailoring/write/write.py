# write.py
import logging
from html import escape

from playwright.async_api import async_playwright, Playwright
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# A4 page size, matching the root cover-letter workflow's page geometry
PAGE_WIDTH_MM = 210
PAGE_HEIGHT_MM = 297
MARGIN_MM = 15


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


async def write(
    llm_text: str,
    output_path: str = "page.pdf",
) -> str | None:
    # HTML-escape untrusted LLM output before it reaches the page — deterministic
    # code's job, not the model's (see ../README.md, prompts/README.md).
    escaped = escape(llm_text).replace("\n", "<br>")

    # @page only sets the printed page's size — it doesn't clip. Content is left
    # free to flow past one page here; overflow is *detected* after rendering
    # (page-count check below), never silently truncated, since a resume cut off
    # mid-sentence must never ship unnoticed.
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>LLM Response</title>
  <style>
    @page {{
      size: A4;
      margin: {MARGIN_MM}mm;
    }}

    body {{
      margin: 0;
      padding: 0;
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      font-size: 11pt;
      line-height: 1.45;
      color: #222;
    }}

    h1, h2, h3 {{
      margin: 0.6em 0 0.3em;
      page-break-after: avoid;
    }}

    p {{
      margin: 0.4em 0;
    }}

    pre, code {{
      background: #f4f4f4;
      border-radius: 3px;
      font-family: ui-monospace, monospace;
      font-size: 9.5pt;
    }}

    pre {{
      padding: 0.6em;
      white-space: pre-wrap;
      word-break: break-word;
    }}
  </style>
</head>
<body>
  {escaped}
</body>
</html>"""

    async with async_playwright() as playwright:
        await _render(playwright, html, output_path)

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
