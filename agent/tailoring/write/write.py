from playwright.async_api import async_playwright, Playwright

async def run(playwright: Playwright):
    browser = await playwright.chromium.launch()
    context = await browser.new_context()
    page = await context.new_page()

    await page.emulate_media(media="print")
    await page.pdf(path="page.pdf")

    await context.close()
    await browser.close()

async def write():
    async with async_playwright() as playwright:
        await run(playwright)
