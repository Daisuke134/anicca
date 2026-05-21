#!/bin/bash

# 図書館管理システム設計モデル PDF生成スクリプト
# PlantUMLオンラインサーバーを使用してSVGを取得し、PDFに変換

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PLANTUML_FILES=(
    "library-management-usecase.puml"
    "library-management-class.puml"
    "library-management-sequence-borrow.puml"
    "library-management-sequence-return.puml"
    "library-management-statemachine-user.puml"
    "library-management-statemachine-book.puml"
)

PDF_FILES=()

echo "図書館管理システム設計モデル PDF生成を開始します..."

for puml_file in "${PLANTUML_FILES[@]}"; do
    if [ ! -f "$puml_file" ]; then
        echo "警告: $puml_file が見つかりません"
        continue
    fi
    
    echo "処理中: $puml_file"
    
    # PlantUMLコードを読み込み
    plantuml_code=$(cat "$puml_file")
    
    # PlantUMLコードを圧縮してエンコード（オンラインサーバー用）
    encoded=$(echo "$plantuml_code" | python3 -c "
import sys
import base64
import zlib
code = sys.stdin.read()
compressed = zlib.compress(code.encode('utf-8'))
encoded = base64.urlsafe_b64encode(compressed).decode('ascii').rstrip('=')
print(encoded)
")
    
    # SVG URLを生成（DEFLATEエンコーディング、プレフィックスなし）
    svg_url="http://www.plantuml.com/plantuml/svg/$encoded"
    
    # SVGをダウンロード
    svg_file="${puml_file%.puml}.svg"
    curl -s -o "$svg_file" "$svg_url"
    
    if [ -f "$svg_file" ]; then
        echo "  SVGをダウンロード: $svg_file"
        
        # PDFに変換（macOSのsipsを使用）
        pdf_file="${puml_file%.puml}.pdf"
        if command -v sips &> /dev/null; then
            # SVGをPNGに変換してからPDFに変換
            png_file="${puml_file%.puml}.png"
            sips -s format png "$svg_file" --out "$png_file" > /dev/null 2>&1
            sips -s format pdf "$png_file" --out "$pdf_file" > /dev/null 2>&1
            rm -f "$png_file"
            
            if [ -f "$pdf_file" ]; then
                echo "  PDFを生成: $pdf_file"
                PDF_FILES+=("$pdf_file")
            else
                echo "  PDF変換に失敗: $svg_file"
            fi
        else
            echo "  sipsコマンドが見つかりません。SVGファイルが生成されています。"
        fi
    else
        echo "  SVGダウンロードに失敗: $svg_url"
    fi
done

# PDFを統合
if [ ${#PDF_FILES[@]} -gt 0 ]; then
    echo ""
    echo "PDFファイルを統合中..."
    OUTPUT_PDF="2411218-daisuke-narita.pdf"
    
    # macOSの/System/Library/Automator/Combine PDF Pages.action/Contents/Resources/join.pyを使用
    if [ -f "/System/Library/Automator/Combine PDF Pages.action/Contents/Resources/join.py" ]; then
        python3 /System/Library/Automator/Combine\ PDF\ Pages.action/Contents/Resources/join.py \
            -o "$OUTPUT_PDF" \
            "${PDF_FILES[@]}" 2>/dev/null
        
        if [ -f "$OUTPUT_PDF" ]; then
            echo "統合PDFを生成: $OUTPUT_PDF"
        else
            echo "PDF統合に失敗しました。個別のPDFファイルが生成されています。"
            echo "以下のファイルを手動で統合してください:"
            for pdf in "${PDF_FILES[@]}"; do
                echo "  - $pdf"
            done
        fi
    else
        # join.pyが見つからない場合は、Pythonスクリプトで統合
        python3 << EOF
import sys
from PyPDF2 import PdfMerger

merger = PdfMerger()
pdf_files = ${PDF_FILES[@]@Q}

for pdf in pdf_files:
    try:
        merger.append(pdf)
    except Exception as e:
        print(f"エラー: {pdf} を追加できませんでした: {e}")
        sys.exit(1)

output_file = "2411218-daisuke-narita.pdf"
try:
    merger.write(output_file)
    merger.close()
    print(f"統合PDFを生成: {output_file}")
except Exception as e:
    print(f"PDF統合に失敗しました: {e}")
    print("個別のPDFファイルが生成されています。")
    sys.exit(1)
EOF
    fi
else
    echo "PDFファイルが生成されませんでした。"
fi

echo ""
echo "完了しました！"

