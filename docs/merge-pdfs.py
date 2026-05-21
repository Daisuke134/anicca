#!/usr/bin/env python3
"""
複数のPDFファイルを1つに統合
"""

try:
    from pypdf import PdfWriter, PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfWriter, PdfReader
    except ImportError:
        print("エラー: pypdfまたはPyPDF2が必要です")
        print("インストール: pip install pypdf")
        sys.exit(1)

import sys
import os

def merge_pdfs(pdf_files, output_path):
    """複数のPDFファイルを統合"""
    writer = PdfWriter()
    
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            print(f"追加中: {pdf_file}")
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                writer.add_page(page)
        else:
            print(f"警告: {pdf_file} が見つかりません")
    
    with open(output_path, 'wb') as output_file:
        writer.write(output_file)
    
    print(f"\n統合PDFを生成: {output_path}")

if __name__ == '__main__':
    pdf_files = [
        'library-management-usecase.pdf',
        'library-management-class.pdf',
        'library-management-sequence-borrow.pdf',
        'library-management-sequence-return.pdf',
        'library-management-statemachine-user.pdf',
        'library-management-statemachine-book.pdf'
    ]
    
    output_path = 'library-management-diagrams.pdf'
    
    merge_pdfs(pdf_files, output_path)










