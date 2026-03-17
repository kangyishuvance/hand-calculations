#!/usr/bin/env python3
"""
Convert all Jupyter notebooks directly to PDF, excluding input cells.
Uses temporary HTML as intermediate, then converts to PDF and deletes HTML.
"""

import subprocess
import os
from pathlib import Path

def convert_notebooks_to_pdf(root_dir=None):
    """
    Find all .ipynb files and convert to PDF in the same folder as each notebook.

    Args:
        root_dir: Root directory to search. Defaults to current working directory.
                  Can also be a path to a single .ipynb file.
    """
    if root_dir is None:
        root_dir = Path.cwd()
    else:
        root_dir = Path(root_dir)

    # If a notebook file was passed directly, use its parent directory
    if root_dir.is_file() and root_dir.suffix == ".ipynb":
        notebook_files = [root_dir]
        root_dir = root_dir.parent
    else:
        # Find all notebook files
        notebook_files = list(root_dir.rglob("*.ipynb"))
    
    if not notebook_files:
        print(f"No Jupyter notebooks found in {root_dir}")
        return
    
    print(f"Found {len(notebook_files)} notebooks. Starting conversion...\n")
    
    failed = []
    succeeded = []
    
    for notebook in sorted(notebook_files):
        # Skip checkpoints
        if "checkpoint" in notebook.parts:
            continue
        
        relative_path = notebook.relative_to(root_dir)
        print(f"Converting: {relative_path}")

        # Output PDF sits next to the notebook
        output_pdf = notebook.parent / f"{notebook.stem}.pdf"
        temp_html = notebook.parent / f"{notebook.stem}_temp.html"
        
        try:
            # Step 1: Convert notebook to temporary HTML
            convert_cmd = [
                "jupyter",
                "nbconvert",
                "--to",
                "html",
                str(notebook),
                "--output",
                str(temp_html),
                "--no-input",
                "--allow-errors"
            ]
            
            result = subprocess.run(convert_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise Exception(f"HTML conversion failed: {result.stderr[:200]}")
            
            # clean the HTML to guarantee no input cells remain
            try:
                from bs4 import BeautifulSoup
                with open(temp_html, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f, 'html.parser')
                for selector in ['div.input', 'div.jp-Input', 'div.prompt']:
                    for node in soup.select(selector):
                        node.decompose()
                with open(temp_html, 'w', encoding='utf-8') as f:
                    f.write(str(soup))
            except ImportError:
                # bs4 not available, skip cleaning
                pass
            
            # Step 2: Convert HTML to PDF using playwright
            try:
                from playwright.sync_api import sync_playwright
                
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page()
                    page.goto(f"file:///{temp_html.absolute()}")
                    # wait for network idle to ensure all scripts (MathJax) have loaded
                    page.wait_for_load_state("networkidle")
                    # try triggering MathJax typesetting if available
                    page.evaluate("""
                        if (window.MathJax && MathJax.typeset) {
                            MathJax.typeset();
                        }
                    """)
                    # give MathJax a moment to finish
                    page.wait_for_timeout(1000)
                    page.pdf(path=str(output_pdf))
                    browser.close()
                
                print(f"  ✓ Success: {output_pdf.name}\n")
                succeeded.append(relative_path)
            
            except ImportError:
                raise Exception("Playwright not installed. Run: pip install playwright && playwright install chromium")
        
        except subprocess.TimeoutExpired:
            print(f"  ✗ Timeout\n")
            failed.append((relative_path, "Timeout"))
        except Exception as e:
            print(f"  ✗ Failed: {str(e)}\n")
            failed.append((relative_path, str(e)))
        
        finally:
            # Clean up temporary HTML file
            if temp_html.exists():
                try:
                    temp_html.unlink()
                except:
                    pass
    
    # Summary
    print("\n" + "="*60)
    print(f"CONVERSION SUMMARY")
    print("="*60)
    print(f"Succeeded: {len(succeeded)}/{len(notebook_files)}")
    print(f"Failed: {len(failed)}/{len(notebook_files)}\n")
    
    if failed:
        print("Failed conversions:")
        for notebook, error in failed:
            print(f"  - {notebook}\n")

if __name__ == "__main__":
    import sys
    
    root = sys.argv[1] if len(sys.argv) > 1 else None
    convert_notebooks_to_pdf(root)
