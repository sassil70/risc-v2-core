"""
Standalone PDF generator — Chunked approach for large RICS reports.
Splits HTML at section boundaries and renders each chunk separately,
then merges into a single PDF. This prevents MuPDF Story API timeouts
on large documents.

Usage: python3 pdf_generator.py <html_path> <output_pdf_path> <project_reference>
"""
import sys
import os
import re
import fitz  # PyMuPDF


def extract_css_and_body(html_content: str):
    """Extract CSS from <style> and body content."""
    css_match = re.search(r'<style>(.*?)</style>', html_content, re.DOTALL)
    css = css_match.group(1) if css_match else ""
    body_match = re.search(r'<body>(.*?)</body>', html_content, re.DOTALL)
    body = body_match.group(1) if body_match else html_content
    return css, body


def split_sections(body_html: str):
    """Split HTML body into sections at section-header divs."""
    # Split at each section-header div
    parts = re.split(r'(<div class="section-header"[^>]*>)', body_html)
    
    sections = []
    current = ""
    for part in parts:
        if part.startswith('<div class="section-header"'):
            if current.strip():
                sections.append(current)
            current = part
        else:
            current += part
    if current.strip():
        sections.append(current)
    
    return sections if sections else [body_html]


def render_chunk_to_pages(css: str, html_chunk: str, mediabox, margins):
    """Render one HTML chunk to a list of PDF pages (as fitz.Document)."""
    full_html = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><style>{css}</style></head><body>{html_chunk}</body></html>'
    
    story = fitz.Story(full_html)
    # Use an in-memory document
    writer_path = f"/tmp/chunk_{id(html_chunk)}.pdf"
    writer = fitz.DocumentWriter(writer_path)
    more = True
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(margins)
        story.draw(dev)
        writer.end_page()
    writer.close()
    
    return writer_path


def generate_pdf(html_path: str, output_path: str, reference: str = ""):
    """Convert HTML file to PDF using chunked approach."""
    with open(html_path, "r") as f:
        html_content = f.read()

    css, body = extract_css_and_body(html_content)
    sections = split_sections(body)
    
    MEDIABOX = fitz.paper_rect("a4")
    WHERE = MEDIABOX + (36, 40, -36, -50)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Render each section separately
    chunk_pdfs = []
    for i, section in enumerate(sections):
        try:
            chunk_path = render_chunk_to_pages(css, section, MEDIABOX, WHERE)
            chunk_pdfs.append(chunk_path)
        except Exception as e:
            print(f"WARN|Section {i} failed: {e}", file=sys.stderr)
    
    if not chunk_pdfs:
        print("ERROR|No sections rendered")
        sys.exit(1)
    
    # Merge all chunk PDFs
    final_doc = fitz.open()
    for chunk_path in chunk_pdfs:
        try:
            chunk_doc = fitz.open(chunk_path)
            final_doc.insert_pdf(chunk_doc)
            chunk_doc.close()
            os.unlink(chunk_path)
        except Exception as e:
            print(f"WARN|Merge failed for {chunk_path}: {e}", file=sys.stderr)
    
    # Add headers / footers / page numbers
    total_pages = len(final_doc)
    for i, page in enumerate(final_doc):
        rect = page.rect
        # Footer left: RICS branding
        page.insert_text(
            fitz.Point(36, rect.height - 20),
            "RICS Home Survey \u2013 Level 3",
            fontsize=7, color=(0.14, 0.12, 0.13)
        )
        # Footer right: page number
        page.insert_text(
            fitz.Point(rect.width - 60, rect.height - 20),
            f"Page {i + 1} of {total_pages}",
            fontsize=7, color=(0.14, 0.12, 0.13)
        )
        # Header: skip first page (cover)
        if i > 0 and reference:
            page.insert_text(
                fitz.Point(36, 20),
                reference,
                fontsize=7, color=(0.30, 0.18, 0.41)
            )
    
    final_doc.save(output_path)
    final_doc.close()

    pdf_size = os.path.getsize(output_path) // 1024
    print(f"OK|{total_pages}|{pdf_size}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 pdf_generator.py <html_path> <output_pdf_path> [reference]")
        sys.exit(1)
    
    html_path = sys.argv[1]
    output_path = sys.argv[2]
    reference = sys.argv[3] if len(sys.argv) > 3 else ""
    
    try:
        generate_pdf(html_path, output_path, reference)
    except Exception as e:
        print(f"ERROR|{e}")
        sys.exit(1)
