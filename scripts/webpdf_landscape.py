"""
Export a Jupyter notebook to a landscape A4 PDF.
Steps:
  1. nbconvert --to html  (handles attachments, MathJax, --no-input)
  2. Inject @page CSS for A4 landscape
  3. Playwright prints the HTML → PDF

Usage: python webpdf_landscape.py <notebook.ipynb> <output_name> <output_dir>
"""
import sys
import asyncio
import os
import subprocess
import tempfile

PRINT_CSS = """
<style>
@page {
    size: A4 landscape;
    margin: 12mm;
}
/* Keep headings glued to the content below them */
h1, h2, h3, h4 { page-break-after: avoid; }
/* Don't split a cell across pages */
.jp-Cell { page-break-inside: avoid; }
img, svg, figure { max-width: 100% !important; page-break-inside: avoid; }
</style>
"""


async def print_pdf(html_path: str) -> bytes:
    """Return raw PDF bytes — caller writes to disk (avoids UNC path issues)."""
    from playwright.async_api import async_playwright

    uri = "file:///" + html_path.replace("\\", "/").lstrip("/")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.emulate_media(media="print")
        await page.goto(uri, wait_until="networkidle")
        # Give MathJax time to finish typesetting
        await page.wait_for_timeout(3000)
        pdf_bytes = await page.pdf(
            format="A4",
            landscape=True,
            print_background=True,
            margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"},
        )
        await browser.close()
    return pdf_bytes


def main():
    if len(sys.argv) < 4:
        print("Usage: python webpdf_landscape.py <notebook.ipynb> <output_name> <output_dir>")
        sys.exit(1)

    nb_path   = sys.argv[1]
    out_name  = sys.argv[2]
    out_dir   = sys.argv[3]

    os.makedirs(out_dir, exist_ok=True)

    # --- Step 1: export HTML via nbconvert (handles images + MathJax correctly) ---
    html_path = os.path.join(out_dir, out_name + ".html")
    pdf_path  = os.path.join(out_dir, out_name + ".pdf")

    print(f"Exporting HTML: {nb_path}")
    subprocess.check_call([
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "html",
        "--no-input",
        "--output", out_name,
        "--output-dir", out_dir,
        nb_path,
    ])

    # --- Step 2: inject landscape CSS ---
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    if "</head>" in html:
        html = html.replace("</head>", PRINT_CSS + "</head>", 1)
    else:
        html = PRINT_CSS + html

    # Write to a temp file so file:// URI works on UNC paths too
    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    tmp.write(html)
    tmp.close()

    # --- Step 3: Playwright prints to PDF (writes locally, then copies to dest) ---
    print("Printing PDF (landscape A4)...")
    try:
        pdf_bytes = asyncio.run(print_pdf(tmp.name))
    finally:
        os.unlink(tmp.name)
        os.unlink(html_path)   # remove intermediate HTML

    # Remove stale/locked PDF if it exists, then write fresh copy
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"PDF: {pdf_path}")


if __name__ == "__main__":
    main()
