import os
import asyncio
from playwright.async_api import async_playwright

async def compile_to_pdf(html_content: str, output_path: str):
    """
    Compiles an HTML string into a static PDF using headless Chromium.
    Ensures strict RICS CSS pagination and layout are maintained.
    """
    print(f"Compiling PDF via Playwright to: {output_path}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Using A4 dimensions and standard print backgrounds
        page = await browser.new_page()
        
        # Load content -> We can either set content directly or write to a temp file and navigate.
        # Direct set_content is usually fine for self-contained HTML
        await page.set_content(html_content, wait_until="networkidle")
        
        # Generate the PDF
        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "2cm", "bottom": "2cm", "left": "1cm", "right": "1cm"}
        )
        
        await browser.close()
        
    print(f"PDF Successfully compiled to: {output_path}")
    return output_path
