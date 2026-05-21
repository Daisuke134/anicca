#!/usr/bin/env python3
"""
PlantUMLファイルからPDFを生成するスクリプト
オンラインのPlantUMLサーバーを使用してSVGを取得し、PDFに変換
"""

import subprocess
import sys
import os
import base64
import zlib
import urllib.parse

def plantuml_to_svg_url(plantuml_code):
    """PlantUMLコードをSVG URLに変換"""
    # PlantUMLコードを圧縮してエンコード
    compressed = zlib.compress(plantuml_code.encode('utf-8'))
    encoded = base64.urlsafe_b64encode(compressed).decode('ascii').rstrip('=')
    return f"http://www.plantuml.com/plantuml/svg/{encoded}"

def download_svg(url, output_path):
    """SVGをダウンロード"""
    try:
        import urllib.request
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        print(f"エラー: {e}")
        return False

def svg_to_pdf(svg_path, pdf_path):
    """SVGをPDFに変換（macOSのsipsまたはcairosvgを使用）"""
    # macOSのsipsを使用
    if os.path.exists('/usr/bin/sips'):
        try:
            # SVGをPNGに変換してからPDFに変換
            png_path = svg_path.replace('.svg', '.png')
            subprocess.run(['/usr/bin/sips', '-s', 'format', 'png', svg_path, '--out', png_path], check=True)
            subprocess.run(['/usr/bin/sips', '-s', 'format', 'pdf', png_path, '--out', pdf_path], check=True)
            if os.path.exists(png_path):
                os.remove(png_path)
            return True
        except subprocess.CalledProcessError:
            pass
    
    # cairosvgを使用
    try:
        import cairosvg
        cairosvg.svg2pdf(url=svg_path, write_to=pdf_path)
        return True
    except ImportError:
        print("cairosvgがインストールされていません。pip install cairosvg でインストールしてください。")
    except Exception as e:
        print(f"PDF変換エラー: {e}")
    
    return False

def main():
    puml_files = [
        'library-management-usecase.puml',
        'library-management-class.puml',
        'library-management-sequence-borrow.puml',
        'library-management-sequence-return.puml',
        'library-management-statemachine-user.puml',
        'library-management-statemachine-book.puml'
    ]
    
    pdf_files = []
    
    for puml_file in puml_files:
        if not os.path.exists(puml_file):
            print(f"警告: {puml_file} が見つかりません")
            continue
        
        print(f"処理中: {puml_file}")
        
        # PlantUMLコードを読み込み
        with open(puml_file, 'r', encoding='utf-8') as f:
            plantuml_code = f.read()
        
        # SVG URLを生成
        svg_url = plantuml_to_svg_url(plantuml_code)
        
        # SVGをダウンロード
        svg_path = puml_file.replace('.puml', '.svg')
        if download_svg(svg_url, svg_path):
            print(f"  SVGをダウンロード: {svg_path}")
            
            # PDFに変換
            pdf_path = puml_file.replace('.puml', '.pdf')
            if svg_to_pdf(svg_path, pdf_path):
                print(f"  PDFを生成: {pdf_path}")
                pdf_files.append(pdf_path)
            else:
                print(f"  PDF変換に失敗: {svg_path}")
        else:
            print(f"  SVGダウンロードに失敗: {svg_url}")
    
    if pdf_files:
        print(f"\n生成されたPDFファイル:")
        for pdf in pdf_files:
            print(f"  - {pdf}")
        print("\nこれらのPDFファイルを手動で統合してください。")
        print("macOSの場合: Previewアプリで開いて、ドラッグ&ドロップで統合できます。")

if __name__ == '__main__':
    main()










