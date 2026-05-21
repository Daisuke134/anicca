#!/usr/bin/env python3
"""
図書館管理システム設計モデル PDF生成スクリプト
PlantUMLファイルからPDFを生成し、1つのPDFファイルに統合
"""

import os
import sys
import base64
import zlib
import urllib.request
import urllib.error
import subprocess
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
os.chdir(SCRIPT_DIR)

PLANTUML_FILES = [
    "library-management-usecase.puml",
    "library-management-class.puml",
    "library-management-sequence-borrow.puml",
    "library-management-sequence-return.puml",
    "library-management-statemachine-user.puml",
    "library-management-statemachine-book.puml",
]

def deflate_and_encode(plantuml_text):
    """PlantUMLの公式エンコーディング実装（python-plantumlから）"""
    import string
    # PlantUMLの文字マッピング
    plantuml_alphabet = string.digits + string.ascii_uppercase + string.ascii_lowercase + '-_'
    # 標準base64の文字マッピング
    base64_alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits + '+/'
    # バイト列用の文字マッピングテーブルを作成
    b64_to_plantuml = bytes.maketrans(base64_alphabet.encode('utf-8'), plantuml_alphabet.encode('utf-8'))
    
    # zlib圧縮（ヘッダーとフッターを削除）
    zlibbed_str = zlib.compress(plantuml_text.encode('utf-8'))
    compressed_string = zlibbed_str[2:-4]  # ヘッダー（2バイト）とフッター（4バイト）を削除
    
    # base64エンコードして文字マッピングを変換
    return base64.b64encode(compressed_string).translate(b64_to_plantuml).decode('utf-8')

def plantuml_to_svg_url(plantuml_code):
    """PlantUMLコードをSVG URLに変換（DEFLATEエンコーディング）"""
    # PlantUMLの標準エンコーディング: UTF-8 → DEFLATE圧縮 → PlantUML専用base64エンコード
    encoded = deflate_and_encode(plantuml_code)
    # デフォルトのDEFLATEエンコーディングを使用（プレフィックスなし）
    return f"http://www.plantuml.com/plantuml/svg/{encoded}"

def download_svg(url, output_path, max_retries=3, timeout=30):
    """SVGをダウンロード（リトライ機能付き）"""
    for attempt in range(max_retries):
        try:
            # タイムアウト付きリクエスト
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (compatible; PlantUML-PDF-Generator/1.0)')
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                # HTTPステータスコードを確認
                if response.status == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.read())
                    return True
                else:
                    print(f"  警告: HTTPステータスコード {response.status}")
        except urllib.error.HTTPError as e:
            if e.code == 520 and attempt < max_retries - 1:
                # HTTP 520エラーの場合はリトライ
                wait_time = 2 ** attempt  # 指数バックオフ: 1秒、2秒、4秒
                print(f"  HTTP {e.code} エラー。{wait_time}秒後にリトライします... (試行 {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                print(f"  HTTPエラー {e.code}: {e.reason}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"  {wait_time}秒後にリトライします... (試行 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
        except urllib.error.URLError as e:
            print(f"  URLエラー: {e.reason}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  {wait_time}秒後にリトライします... (試行 {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
        except Exception as e:
            print(f"  エラー: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"  {wait_time}秒後にリトライします... (試行 {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
    
    return False

def generate_svg_local(puml_path, svg_path, plantuml_jar="plantuml.jar"):
    """ローカルのPlantUML JARを使用してSVGを生成"""
    jar_path = Path(plantuml_jar)
    if not jar_path.exists():
        return False
    
    try:
        # Javaが利用可能か確認
        result = subprocess.run(['java', '-version'], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              timeout=5)
        # java -versionは常にexit code 0を返すので、エラー時は例外で捕捉される
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    
    try:
        # PlantUMLでSVGを生成
        result = subprocess.run(
            ['java', '-jar', str(jar_path), '-tsvg', str(puml_path), '-o', str(puml_path.parent)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0 and svg_path.exists():
            return True
        else:
            if result.stderr:
                print(f"  PlantUMLエラー: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  PlantUML実行がタイムアウトしました")
        return False
    except Exception as e:
        print(f"  ローカルPlantUML実行エラー: {e}")
        return False

def svg_to_pdf(svg_path, pdf_path):
    """SVGをPDFに変換"""
    # macOSのsipsを使用
    if os.path.exists('/usr/bin/sips'):
        try:
            # SVGをPNGに変換してからPDFに変換
            png_path = str(svg_path).replace('.svg', '.png')
            subprocess.run(['/usr/bin/sips', '-s', 'format', 'png', str(svg_path), '--out', png_path], 
                         check=True, capture_output=True)
            subprocess.run(['/usr/bin/sips', '-s', 'format', 'pdf', png_path, '--out', str(pdf_path)], 
                         check=True, capture_output=True)
            if os.path.exists(png_path):
                os.remove(png_path)
            return True
        except subprocess.CalledProcessError as e:
            print(f"sips変換エラー: {e}")
            return False
    
    # cairosvgを使用（フォールバック）
    try:
        import cairosvg
        cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
        return True
    except ImportError:
        print("cairosvgがインストールされていません。pip install cairosvg でインストールしてください。")
    except Exception as e:
        print(f"PDF変換エラー: {e}")
    
    return False

def merge_pdfs(pdf_files, output_path):
    """複数のPDFファイルを1つに統合"""
    try:
        from PyPDF2 import PdfMerger
        merger = PdfMerger()
        for pdf in pdf_files:
            merger.append(pdf)
        merger.write(str(output_path))
        merger.close()
        return True
    except ImportError:
        print("PyPDF2がインストールされていません。pip install PyPDF2 でインストールしてください。")
        return False
    except Exception as e:
        print(f"PDF統合エラー: {e}")
        return False

def main():
    print("図書館管理システム設計モデル PDF生成を開始します...\n")
    
    pdf_files = []
    
    for puml_file in PLANTUML_FILES:
        puml_path = Path(puml_file)
        if not puml_path.exists():
            print(f"警告: {puml_file} が見つかりません")
            continue
        
        print(f"処理中: {puml_file}")
        
        # PlantUMLコードを読み込み
        with open(puml_path, 'r', encoding='utf-8') as f:
            plantuml_code = f.read()
        
        # SVG URLを生成
        svg_url = plantuml_to_svg_url(plantuml_code)
        
        # SVGをダウンロード（オンラインサーバーから）
        svg_path = puml_path.with_suffix('.svg')
        svg_downloaded = download_svg(svg_url, svg_path)
        
        # オンラインサーバーからのダウンロードに失敗した場合、ローカルのPlantUML JARを使用
        if not svg_downloaded:
            print(f"  オンラインサーバーからのダウンロードに失敗。ローカルのPlantUMLを使用します...")
            if generate_svg_local(puml_path, svg_path):
                print(f"  ローカルPlantUMLでSVGを生成: {svg_path}")
                svg_downloaded = True
            else:
                print(f"  ローカルPlantUMLでもSVG生成に失敗しました")
        
        if svg_downloaded and svg_path.exists():
            # PDFに変換
            pdf_path = puml_path.with_suffix('.pdf')
            if svg_to_pdf(svg_path, pdf_path):
                print(f"  PDFを生成: {pdf_path}")
                pdf_files.append(pdf_path)
            else:
                print(f"  PDF変換に失敗: {svg_path}")
        else:
            print(f"  SVG生成に失敗: {puml_file}")
    
    # PDFを統合
    if pdf_files:
        print(f"\n{len(pdf_files)}個のPDFファイルを統合中...")
        output_pdf = Path("2411218-daisuke-narita.pdf")
        
        if merge_pdfs(pdf_files, output_pdf):
            print(f"統合PDFを生成: {output_pdf}")
            print(f"\n完了しました！提出ファイル: {output_pdf}")
        else:
            print("\nPDF統合に失敗しました。個別のPDFファイルが生成されています。")
            print("以下のファイルを手動で統合してください:")
            for pdf in pdf_files:
                print(f"  - {pdf}")
            print("\nmacOSの場合: Previewアプリで開いて、ドラッグ&ドロップで統合できます。")
    else:
        print("\nPDFファイルが生成されませんでした。")

if __name__ == '__main__':
    main()

