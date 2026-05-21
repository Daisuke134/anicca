#!/bin/bash

# 図書館管理システム設計モデル PDF生成スクリプト（ローカルPlantUML使用）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PLANTUML_JAR="plantuml.jar"
PLANTUML_URL="https://github.com/plantuml/plantuml/releases/download/v1.2024.5/plantuml-1.2024.5.jar"

# PlantUML JARファイルのダウンロード
if [ ! -f "$PLANTUML_JAR" ]; then
    echo "PlantUML JARファイルをダウンロード中..."
    curl -L -o "$PLANTUML_JAR" "$PLANTUML_URL"
fi

PLANTUML_FILES=(
    "library-management-usecase.puml"
    "library-management-class.puml"
    "library-management-sequence-borrow.puml"
    "library-management-sequence-return.puml"
    "library-management-statemachine-user.puml"
    "library-management-statemachine-book.puml"
)

echo "図書館管理システム設計モデル PDF生成を開始します..."
echo ""

# PNGを生成
echo "PNGファイルを生成中..."
java -jar "$PLANTUML_JAR" -tpng -o . "${PLANTUML_FILES[@]}"

# PNGをPDFに変換
echo ""
echo "PNGをPDFに変換中..."
PDF_FILES=()
for puml_file in "${PLANTUML_FILES[@]}"; do
    png_file="${puml_file%.puml}.png"
    pdf_file="${puml_file%.puml}.pdf"
    
    if [ -f "$png_file" ]; then
        if command -v sips &> /dev/null; then
            sips -s format pdf "$png_file" --out "$pdf_file" > /dev/null 2>&1
            if [ -f "$pdf_file" ]; then
                echo "  PDFを生成: $pdf_file"
                PDF_FILES+=("$pdf_file")
            fi
        fi
    fi
done

# PDFを統合
if [ ${#PDF_FILES[@]} -gt 0 ]; then
    echo ""
    echo "PDFファイルを統合中..."
    OUTPUT_PDF="2411218-daisuke-narita.pdf"
    
    # Ghostscriptを使用して統合
    if command -v gs &> /dev/null; then
        gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile="$OUTPUT_PDF" "${PDF_FILES[@]}"
        if [ -f "$OUTPUT_PDF" ]; then
            echo "統合PDFを生成: $OUTPUT_PDF"
            echo ""
            echo "完了しました！提出ファイル: $OUTPUT_PDF"
        else
            echo "PDF統合に失敗しました。"
        fi
    else
        echo "Ghostscriptが見つかりません。個別のPDFファイルが生成されています。"
    fi
else
    echo "PDFファイルが生成されませんでした。"
fi

