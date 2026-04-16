"""
Playwright PDF Generator — Production RICS Report Engine
Replaces PyMuPDF chunked approach with Chromium-based rendering.

Supports:
- 250+ page documents with embedded photos
- Full CSS (grid, flexbox, print media queries)
- Photo optimization (resize to max 800px before embedding)
- Headers/footers with RICS branding
- A4 format with configurable margins

Usage (standalone):
    python3 playwright_pdf_generator.py <html_path> <output_pdf_path> [reference]

Usage (module):
    from services.playwright_pdf_generator import generate_pdf_playwright
    path = await generate_pdf_playwright(html_content, output_path, reference)
"""

import os
import re
import sys
import asyncio
import logging
import base64
from pathlib import Path

logger = logging.getLogger("playwright_pdf_generator")


def optimize_images_in_html(html_content: str, max_width: int = 800) -> str:
    """
    Find all <img src="file://..."> or <img src="/path/..."> tags
    and convert them to base64-embedded images with size optimization.
    This ensures Chromium can access local files and keeps PDF size reasonable.
    """
    try:
        from PIL import Image
        import io
        has_pil = True
    except ImportError:
        has_pil = False
        logger.warning("Pillow not installed — images will not be optimized")

    def replace_img(match):
        full_tag = match.group(0)
        src = match.group(1)

        # Clean file:// prefix
        file_path = src.replace("file://", "")

        if not os.path.exists(file_path):
            logger.warning(f"Image not found: {file_path}")
            return full_tag

        try:
            if has_pil:
                img = Image.open(file_path)
                # Resize if wider than max_width
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_size = (max_width, int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)

                # Convert to JPEG for compression
                buf = io.BytesIO()
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                img.save(buf, format='JPEG', quality=75, optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode()
                mime = "image/jpeg"
            else:
                with open(file_path, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode()
                ext = file_path.lower().split('.')[-1]
                mime = f"image/{ext}" if ext in ('png', 'jpeg', 'jpg', 'gif') else "image/jpeg"

            # Replace src with base64 data URI
            new_tag = full_tag.replace(src, f"data:{mime};base64,{b64}")
            logger.debug(f"Embedded image: {file_path} ({len(b64) // 1024}KB)")
            return new_tag

        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {e}")
            return full_tag

    # Match <img src="..." ...>
    pattern = r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*>'
    result = re.sub(pattern, replace_img, html_content)
    return result


async def generate_pdf_playwright(
    html_content: str,
    output_path: str,
    reference: str = "",
    optimize_images: bool = True,
    image_max_width: int = 800,
) -> str:
    """
    Convert HTML content to PDF using Playwright/Chromium.

    Args:
        html_content: Full HTML string (with <style> tags)
        output_path: Where to save the PDF
        reference: Project reference for header
        optimize_images: Whether to resize/compress images
        image_max_width: Max width for image optimization

    Returns:
        Path to generated PDF
    """
    from playwright.async_api import async_playwright

    # Optimize images (convert file paths to base64)
    if optimize_images:
        logger.info("Optimizing images for PDF embedding...")
        html_content = optimize_images_in_html(html_content, image_max_width)

    # Save HTML to temp file
    html_path = output_path.replace(".pdf", "_temp.html")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            page = await browser.new_page()

            # Load HTML file (file:// allows local resource access)
            await page.goto(f"file://{html_path}", wait_until="networkidle")

            # Generate PDF with RICS formatting
            header_template = ""
            footer_template = f"""
            <div style="width:100%; font-size:7pt; font-family:Arial; padding:0 18mm; display:flex; justify-content:space-between;">
                <span style="color:#4D2D69;">{reference}</span>
                <span style="color:#231F20;">RICS Home Survey – Level 3</span>
                <span style="color:#231F20;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
            </div>
            """

            await page.pdf(
                path=output_path,
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template='<div></div>',
                footer_template=footer_template,
                margin={
                    "top": "20mm",
                    "bottom": "25mm",
                    "left": "18mm",
                    "right": "18mm",
                },
            )

            await browser.close()

        # Cleanup temp HTML
        if os.path.exists(html_path):
            os.unlink(html_path)

        pdf_size = os.path.getsize(output_path) // 1024
        page_count = _count_pdf_pages(output_path)
        logger.info(f"PDF generated: {output_path} ({page_count} pages, {pdf_size}KB)")

        return output_path

    except Exception as e:
        logger.error(f"Playwright PDF generation failed: {e}")
        # Keep HTML as fallback
        logger.info(f"HTML saved as fallback: {html_path}")
        raise


def _count_pdf_pages(pdf_path: str) -> int:
    """Count pages in a PDF file using PyMuPDF (fitz)."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def generate_pdf_sync(
    html_content: str,
    output_path: str,
    reference: str = "",
) -> str:
    """Synchronous wrapper for generate_pdf_playwright."""
    return asyncio.run(
        generate_pdf_playwright(html_content, output_path, reference)
    )


# ── CLI Entry Point ──
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 playwright_pdf_generator.py <html_path> <output_pdf_path> [reference]")
        sys.exit(1)

    html_path = sys.argv[1]
    output_path = sys.argv[2]
    reference = sys.argv[3] if len(sys.argv) > 3 else ""

    with open(html_path, "r") as f:
        html_content = f.read()

    try:
        path = generate_pdf_sync(html_content, output_path, reference)
        pdf_size = os.path.getsize(path) // 1024
        page_count = _count_pdf_pages(path)
        print(f"OK|{page_count}|{pdf_size}")
    except Exception as e:
        print(f"ERROR|{e}")
        sys.exit(1)
