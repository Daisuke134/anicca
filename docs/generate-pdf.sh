#!/bin/bash

# PlantUML JARファイルのダウンロード
PLANTUML_JAR="plantuml.jar"
PLANTUML_URL="https://github.com/plantuml/plantuml/releases/download/v1.2024.5/plantuml-1.2024.5.jar"

if [ ! -f "$PLANTUML_JAR" ]; then
    echo "PlantUML JARファイルをダウンロード中..."
    curl -L -o "$PLANTUML_JAR" "$PLANTUML_URL"
fi

# PDFを生成
echo "PDFを生成中..."
java -jar "$PLANTUML_JAR" -tpng -o . library-management-*.puml

# PNGをPDFに変換（ImageMagickまたはsipsを使用）
if command -v sips &> /dev/null; then
    echo "PNGをPDFに変換中..."
    for png in library-management-*.png; do
        if [ -f "$png" ]; then
            sips -s format pdf "$png" --out "${png%.png}.pdf"
        fi
    done
    
    # PDFを統合
    echo "PDFを統合中..."
    /System/Library/Automator/Combine\ PDF\ Pages.action/Contents/Resources/join.py \
        -o library-management-diagrams.pdf \
        library-management-usecase.pdf \
        library-management-class.pdf \
        library-management-sequence-borrow.pdf \
        library-management-sequence-return.pdf \
        library-management-statemachine-user.pdf \
        library-management-statemachine-book.pdf 2>/dev/null || \
    echo "PDF統合には手動で行ってください。個別のPDFファイルが生成されています。"
else
    echo "sipsコマンドが見つかりません。PNGファイルが生成されています。"
fi

echo "完了しました！"










