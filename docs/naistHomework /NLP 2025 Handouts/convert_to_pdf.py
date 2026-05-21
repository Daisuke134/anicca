#!/usr/bin/env python3
"""
Convert HTML file to PDF using playwright
"""
import sys
import os
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: playwright is not installed.")
    print("Please install it by running: pip3 install playwright")
    print("Then install browser: playwright install chromium")
    sys.exit(1)

def html_to_pdf(html_path, pdf_path):
    """Convert HTML file to PDF"""
    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path).resolve()
    
    if not html_path.exists():
        print(f"Error: HTML file not found: {html_path}")
        sys.exit(1)
    
    print(f"Converting {html_path} to {pdf_path}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Load HTML file
        page.goto(f"file://{html_path}")
        
        # Wait for content to load
        page.wait_for_load_state("networkidle")
        
        # Generate PDF
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={
                "top": "1cm",
                "right": "1cm",
                "bottom": "1cm",
                "left": "1cm"
            }
        )
        
        browser.close()
    
    print(f"Successfully created PDF: {pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 convert_to_pdf.py <html_file> [pdf_file]")
        sys.exit(1)
    
    html_file = sys.argv[1]
    if len(sys.argv) >= 3:
        pdf_file = sys.argv[2]
    else:
        pdf_file = Path(html_file).with_suffix('.pdf')
    
    html_to_pdf(html_file, pdf_file)

