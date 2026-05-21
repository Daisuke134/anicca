#!/bin/bash
# PDF生成後のYAML変数展開スクリプト
# quarto render/preview/post-render/UI Knitボタンで使用

# デバッグ用: 実行ログを記録（UIのKnitボタンでも確認できるように）
LOG_FILE="/tmp/quarto-post-render-$$.log"

# 無限ループ防止: 既に実行中かチェック
LOCK_FILE="/tmp/quarto-post-render.lock"
if [ -f "$LOCK_FILE" ]; then
    # ロックファイルが存在する場合、古いプロセスが残っている可能性がある
    # 5分以上経過している場合はロックを解除
    if [ -n "$(find "$LOCK_FILE" -mmin +5 2>/dev/null)" ]; then
        echo "Removing stale lock file..." | tee -a "$LOG_FILE"
        rm -f "$LOCK_FILE"
    else
        echo "post-render.sh is already running. Skipping..." | tee -a "$LOG_FILE"
        exit 0
    fi
fi

# ロックファイルを作成
touch "$LOCK_FILE"
trap "rm -f '$LOCK_FILE'" EXIT

# スクリプトのディレクトリに移動
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# プロジェクトルートに移動（scriptsの親ディレクトリ）
cd "$(dirname "$SCRIPT_DIR")" || exit 1

# Quartoから引数が渡された場合（レンダリングされたファイルのパス）
if [ -n "$1" ]; then
    # 引数からTeXファイルのパスを推測
    RENDERED_FILE="$1"
    # PDFファイルが渡された場合、対応するTeXファイルを探す
    if [[ "$RENDERED_FILE" == *.pdf ]]; then
        # _output/paper.pdfの場合、paper.texまたは_output/paper.texを探す
        if [[ "$RENDERED_FILE" == "_output/"* ]] || [[ "$RENDERED_FILE" == "./_output/"* ]]; then
            # まず_output/paper.texを探す
            if [ -f "_output/paper.tex" ]; then
                TEX_FILE="_output/paper.tex"
            elif [ -f "paper.tex" ]; then
                TEX_FILE="paper.tex"
            else
                TEX_FILE="${RENDERED_FILE%.pdf}.tex"
            fi
        else
        TEX_FILE="${RENDERED_FILE%.pdf}.tex"
        fi
    elif [[ "$RENDERED_FILE" == *.tex ]]; then
        TEX_FILE="$RENDERED_FILE"
    else
        # 引数がファイルパスでない場合、デフォルトの検索を行う
        TEX_FILE=""
    fi
fi

# 生成されたTeXファイルのパスを確認
if [ -z "$TEX_FILE" ] || [ ! -f "$TEX_FILE" ]; then
    # 複数の場所を確認（優先順位順）
    # Quartoは_outputディレクトリにTeXファイルを生成する可能性が高い
    if [ -f "_output/paper.tex" ]; then
        TEX_FILE="_output/paper.tex"
        OUTPUT_DIR="_output"
    elif [ -f "paper.tex" ]; then
        TEX_FILE="paper.tex"
        OUTPUT_DIR="."
    else
        # TeXファイルが見つからない場合は待機して再試行（Quartoのレンダリング完了を待つ）
        echo "Waiting for TeX file to be generated..."
        for i in {1..15}; do
            sleep 1
            if [ -f "_output/paper.tex" ]; then
                TEX_FILE="_output/paper.tex"
                OUTPUT_DIR="_output"
                break
            elif [ -f "paper.tex" ]; then
                TEX_FILE="paper.tex"
                OUTPUT_DIR="."
                break
            fi
        done
        if [ -z "$TEX_FILE" ] || [ ! -f "$TEX_FILE" ]; then
            echo "Warning: TeX file not found. Variables may not be expanded."
            echo "  This is normal if Quarto Preview is still rendering."
            # エラーで終了せず、後で再試行できるようにする
        exit 0
        fi
    fi
else
    # 引数から取得したTeXファイルのパスを使用
    OUTPUT_DIR=$(dirname "$TEX_FILE")
    if [ "$OUTPUT_DIR" = "." ]; then
        OUTPUT_DIR="."
    fi
fi

# 古いtemplate/preamble.texへの参照を削除
if grep -q "template/preamble.tex" "$TEX_FILE" 2>/dev/null; then
    echo "Removing old template/preamble.tex reference..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' '/\\input{template\/preamble\.tex}/d' "$TEX_FILE"
        sed -i '' '/NAIST修士論文用LaTeXプリアンブル（手動追加）/d' "$TEX_FILE"
    else
        sed -i '/\\input{template\/preamble\.tex}/d' "$TEX_FILE"
        sed -i '/NAIST修士論文用LaTeXプリアンブル（手動追加）/d' "$TEX_FILE"
    fi
fi

# template/header.texの手動追加は不要（拡張機能のheader-expanded.texが使用される）
# 古いtemplate/header.texへの参照を削除（もし存在する場合）
if grep -q "template/header.tex" "$TEX_FILE" 2>/dev/null; then
    echo "Removing old template/header.tex reference..." | tee -a "$LOG_FILE"
        if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' '/\\input{template\/header\.tex}/d' "$TEX_FILE"
        sed -i '' '/NAIST修士論文用LaTeXヘッダー（手動追加）/d' "$TEX_FILE"
        else
        sed -i '/\\input{template\/header\.tex}/d' "$TEX_FILE"
        sed -i '/NAIST修士論文用LaTeXヘッダー（手動追加）/d' "$TEX_FILE"
    fi
fi

# template/before-body.texの内容が含まれているか確認
if ! grep -q "\\titlepage\|\\cmemberspage\|\\firstabstract" "$TEX_FILE" 2>/dev/null; then
    echo "Warning: template/before-body.tex not found in $TEX_FILE"
    if [ -f "scripts/add_before_body.py" ]; then
        python3 scripts/add_before_body.py "$TEX_FILE" > /dev/null 2>&1
    fi
fi

# TeXLive 2018互換性のため、\PassOptionsToPackageを削除
# Quartoが生成する\PassOptionsToPackageがLaTeX3コマンドと衝突する場合があるため
if [ -f "$TEX_FILE" ]; then
    echo "Fixing \PassOptionsToPackage for TeXLive 2018 compatibility..." | tee -a "$LOG_FILE"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS用のsedコマンド
        sed -i '' '/^\\PassOptionsToPackage{unicode}{hyperref}$/d' "$TEX_FILE"
        sed -i '' '/^\\PassOptionsToPackage{hyphens}{url}$/d' "$TEX_FILE"
        sed -i '' '/^\\PassOptionsToPackage{dvipsnames,svgnames,x11names}{xcolor}$/d' "$TEX_FILE"
    else
        sed -i '/^\\PassOptionsToPackage{unicode}{hyperref}$/d' "$TEX_FILE"
        sed -i '/^\\PassOptionsToPackage{hyphens}{url}$/d' "$TEX_FILE"
        sed -i '/^\\PassOptionsToPackage{dvipsnames,svgnames,x11names}{xcolor}$/d' "$TEX_FILE"
    fi
    echo "✓ Removed \PassOptionsToPackage commands" | tee -a "$LOG_FILE"
    
    # Quartoのnumber-depth: 3が正しく機能しない場合のフォールバック
    # Quartoが生成する\setcounter{secnumdepth}{-\maxdimen}を上書きして、
    # subsubsectionまで表示されるようにする（\ref{}が正しく動作するため）
    echo "Fixing secnumdepth to show subsubsection (fallback)..." | tee -a "$LOG_FILE"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS用のsedコマンド - より柔軟なパターンマッチング
        sed -i '' 's/\\setcounter{secnumdepth}{-\\maxdimen}[^%]*/\\setcounter{secnumdepth}{3} % show subsubsection/' "$TEX_FILE"
    else
        sed -i 's/\\setcounter{secnumdepth}{-\\maxdimen}[^%]*/\\setcounter{secnumdepth}{3} % show subsubsection/' "$TEX_FILE"
    fi
    echo "✓ Fixed secnumdepth to show subsubsection (fallback)" | tee -a "$LOG_FILE"
    
    # Remove \PassOptionsToPackage lines (they cause issues with ltjsarticle)
    # Remove \maketitle first (NAIST format uses \titlepage, and \maketitle causes "No \title given" error)
    echo "Removing \\maketitle (NAIST format uses \\titlepage)..." | tee -a "$LOG_FILE"
    python3 << 'PYTHON_SCRIPT'
import sys
import re

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()

# \maketitleを確実に削除（複数回実行される可能性があるため）
if '\\maketitle' in content:
    content = re.sub(r'\\maketitle\s*\n?', '% \\maketitle removed (NAIST format uses \\titlepage)\n', content)
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        f.write(content)
    print("  ✓ Removed \\maketitle", file=sys.stderr)
else:
    print("  ✓ \\maketitle already removed", file=sys.stderr)
PYTHON_SCRIPT
        "$TEX_FILE"
    echo "✓ Removed \\maketitle" | tee -a "$LOG_FILE"
    
    # This must be done FIRST, before any other processing
    echo "Removing \PassOptionsToPackage lines..." | tee -a "$LOG_FILE"
    # Use Python for more reliable pattern matching
    python3 << 'PYTHON_SCRIPT'
import sys
import re

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
removed_count = 0
for line in lines:
    if '\\PassOptionsToPackage' in line and not line.strip().startswith('%'):
        removed_count += 1
        continue
    new_lines.append(line)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

if removed_count > 0:
    print(f"Removed {removed_count} \\PassOptionsToPackage line(s)", file=sys.stderr)
PYTHON_SCRIPT
    "$TEX_FILE"
    echo "✓ Removed \PassOptionsToPackage lines" | tee -a "$LOG_FILE"
    
    # Quartoが自動生成した\AtBeginDocumentブロックを削除（etoolbox読み込み前に使用されるとエラーになる）
    echo "Removing \\AtBeginDocument blocks..." | tee -a "$LOG_FILE"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS用のsedコマンド - \AtBeginDocument{から対応する}までを削除
        python3 << 'PYTHON_SCRIPT'
import re
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()

# \AtBeginDocument{...}ブロックを削除（コメント内のものは除く）
lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # コメント行でない場合のみチェック
    if '\\AtBeginDocument{' in line and not line.strip().startswith('%'):
        # ブロックの開始を検出
        brace_count = line.count('{') - line.count('}')
        start_line = i
        i += 1
        # 対応する閉じ括弧を探す
        while i < len(lines) and brace_count > 0:
            brace_count += lines[i].count('{') - lines[i].count('}')
            i += 1
        # ブロック全体をスキップ
        print(f"Removed \\AtBeginDocument block (lines {start_line+1} to {i})", file=sys.stderr)
        continue
    new_lines.append(line)
    i += 1

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))
PYTHON_SCRIPT
        "$TEX_FILE"
        echo "✓ Removed \\AtBeginDocument blocks" | tee -a "$LOG_FILE"
    else
        # Linux用の処理（同様のPythonスクリプト）
        python3 << 'PYTHON_SCRIPT'
import re
import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if '\\AtBeginDocument{' in line and not line.strip().startswith('%'):
        brace_count = line.count('{') - line.count('}')
        start_line = i
        i += 1
        while i < len(lines) and brace_count > 0:
            brace_count += lines[i].count('{') - lines[i].count('}')
            i += 1
        print(f"Removed \\AtBeginDocument block (lines {start_line+1} to {i})", file=sys.stderr)
        continue
    new_lines.append(line)
    i += 1

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))
PYTHON_SCRIPT
        "$TEX_FILE"
        echo "✓ Removed \\AtBeginDocument blocks" | tee -a "$LOG_FILE"
    fi
    
    # \begin{document}が確実に存在するようにする
    echo "Ensuring \begin{document} exists..." | tee -a "$LOG_FILE"
    if ! grep -q "^\\\\begin{document}" "$TEX_FILE" 2>/dev/null; then
        # \begin{document}が存在しない場合、\date{...}の後に挿入
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS用のsedコマンド
            sed -i '' '/^\\date{/a\
\\begin{document}
' "$TEX_FILE"
        else
            sed -i '/^\\date{/a\\begin{document}' "$TEX_FILE"
        fi
        echo "✓ Inserted \begin{document}" | tee -a "$LOG_FILE"
    else
        echo "✓ \begin{document} already exists" | tee -a "$LOG_FILE"
    fi
    
    # \maketitleを削除またはコメントアウト（NAISTフォーマットでは\titlepageを使用）
    echo "Removing \\maketitle (NAIST format uses \\titlepage)..." | tee -a "$LOG_FILE"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' 's/\\maketitle/% \\maketitle removed (NAIST format uses \\titlepage)/g' "$TEX_FILE"
    else
        sed -i 's/\\maketitle/% \\maketitle removed (NAIST format uses \\titlepage)/g' "$TEX_FILE"
    fi
    echo "✓ Removed \\maketitle" | tee -a "$LOG_FILE"
    
    # \titleと\authorが\begin{document}の前に存在することを確認
    echo "Ensuring \\title and \\author are before \\begin{document}..." | tee -a "$LOG_FILE"
    python3 << 'PYTHON_SCRIPT'
import sys
import re

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    lines = f.readlines()

# \begin{document}の位置を探す
doc_start_idx = None
for i, line in enumerate(lines):
    if '\\begin{document}' in line:
        doc_start_idx = i
        break

if doc_start_idx is None:
    print("  ✗ \\begin{document} not found", file=sys.stderr)
    sys.exit(1)

# \begin{document}の前に\titleと\authorがあるか確認
has_title_before = False
has_author_before = False
for i in range(doc_start_idx):
    if '\\title{' in lines[i] and not lines[i].strip().startswith('%'):
        has_title_before = True
    if '\\author{' in lines[i] and not lines[i].strip().startswith('%'):
        has_author_before = True

if not has_title_before or not has_author_before:
    # \begin{document}の後に\titleと\authorを探す
    title_line = None
    author_line = None
    for i in range(doc_start_idx + 1, len(lines)):
        if title_line is None and '\\title{' in lines[i] and not lines[i].strip().startswith('%'):
            title_line = lines[i].strip()
        if author_line is None and '\\author{' in lines[i] and not lines[i].strip().startswith('%'):
            author_line = lines[i].strip()
        if title_line and author_line:
            break
    
    if title_line and author_line:
        # \begin{document}の後に見つかった\titleと\authorを削除
        new_lines = []
        for i, line in enumerate(lines):
            if i > doc_start_idx and (title_line in line or author_line in line):
                continue
            new_lines.append(line)
        
        # \begin{document}の直前に挿入
        new_lines.insert(doc_start_idx, title_line + '\n')
        new_lines.insert(doc_start_idx + 1, author_line + '\n')
        
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            f.write(''.join(new_lines))
        print(f"  ✓ Moved \\title and \\author before \\begin{{document}}", file=sys.stderr)
    else:
        print("  ✗ \\title or \\author not found", file=sys.stderr)
else:
    print("  ✓ \\title and \\author are already before \\begin{{document}}", file=sys.stderr)
PYTHON_SCRIPT
        "$TEX_FILE"
        echo "✓ Ensured \\title and \\author are before \\begin{document}" | tee -a "$LOG_FILE"
    
    # \begin{document}の直後に目次のタイトルとハイパーリンクの設定を追加
    # secnumdepthを確実に設定（NAISTスタイルファイルの読み込み後に上書きされる可能性があるため）
    echo "Adding document settings after \begin{document}..." | tee -a "$LOG_FILE"
    # Pythonで確実に処理（sedのエスケープ問題を回避）
    python3 << 'PYTHON_SCRIPT'
import sys
import re

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 既に追加されている場合はスキップ
    if 'secnumdepthを確実に設定（NAISTスタイルファイルの読み込み後に上書きされる可能性があるため）' in content:
        print("  ✓ Document settings already added", file=sys.stderr)
    else:
        # \begin{document}の直後に設定を追加
        # パターン1: \begin{document}\n\maketitle
        pattern1 = r'(\\begin\{document\}[ \t]*\n\\maketitle)'
        replacement1 = '''\\1
% secnumdepthを確実に設定（NAISTスタイルファイルの読み込み後に上書きされる可能性があるため）
% \\AtBeginDocumentを使用して、\\begin{document}の後に確実に設定する
% これにより、\\titlepageや\\cmemberspageなどのコマンドが実行された後でも、secnumdepthが3に設定される
% expand_preamble.pyで$number-depth$が展開される（デフォルトは3）
\\makeatletter
\\AtBeginDocument{%
  \\setcounter{secnumdepth}{$number-depth$}%
  \\setcounter{tocdepth}{$number-depth$}%
}
\\makeatother
% 目次のタイトルとハイパーリンクの設定（post-render.shで追加）
\\makeatletter
\\renewcommand*\\contentsname{目次}
\\renewcommand*\\listfigurename{図目次}
\\renewcommand*\\listtablename{表目次}
\\hypersetup{
  colorlinks=true,
  linkcolor=black,
  filecolor=black,
  urlcolor=black,
  citecolor=black
}
\\makeatother'''
        
        # パターン2: \begin{document}のみ
        pattern2 = r'(\\begin\{document\})'
        replacement2 = '''\\1
% secnumdepthを確実に設定（NAISTスタイルファイルの読み込み後に上書きされる可能性があるため）
% \\AtBeginDocumentを使用して、\\begin{document}の後に確実に設定する
% これにより、\\titlepageや\\cmemberspageなどのコマンドが実行された後でも、secnumdepthが3に設定される
% expand_preamble.pyで$number-depth$が展開される（デフォルトは3）
\\makeatletter
\\AtBeginDocument{%
  \\setcounter{secnumdepth}{$number-depth$}%
  \\setcounter{tocdepth}{$number-depth$}%
}
\\makeatother
% 目次のタイトルとハイパーリンクの設定（post-render.shで追加）
\\makeatletter
\\renewcommand*\\contentsname{目次}
\\renewcommand*\\listfigurename{図目次}
\\renewcommand*\\listtablename{表目次}
\\hypersetup{
  colorlinks=true,
  linkcolor=black,
  filecolor=black,
  urlcolor=black,
  citecolor=black
}
\\makeatother'''
        
        modified = False
        if re.search(pattern1, content):
            # \maketitleの後に追加
            content = re.sub(pattern1, replacement1, content, count=1)
            modified = True
            print("  ✓ Added document settings after \\begin{document} and \\maketitle", file=sys.stderr)
        elif re.search(pattern2, content):
            # \begin{document}の直後に追加
            content = re.sub(pattern2, replacement2, content, count=1)
            modified = True
            print("  ✓ Added document settings after \\begin{document}", file=sys.stderr)
        else:
            print("  ✗ \\begin{document} not found", file=sys.stderr)
            sys.exit(1)
        
        if modified:
            with open(sys.argv[1], 'w', encoding='utf-8') as f:
                f.write(content)
except Exception as e:
    print(f"  ✗ Error: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
    "$TEX_FILE" || echo "Warning: Failed to add document settings" | tee -a "$LOG_FILE"
    echo "✓ Added document settings after \begin{document}" | tee -a "$LOG_FILE"
fi

# YAML変数を展開
# スクリプトのディレクトリに移動（既に移動済みだが、念のため）
cd "$SCRIPT_DIR" || exit 1

if [ -f "scripts/expand_preamble.py" ]; then
    # TeXファイルが見つからない場合、少し待ってから再試行（UIのKnitボタンでレンダリングが完了するまで待つ）
    if [ ! -f "$TEX_FILE" ]; then
        echo "Waiting for TeX file to be generated..." | tee -a "$LOG_FILE"
        for i in {1..30}; do
            sleep 0.5
            if [ -f "_output/paper.tex" ]; then
                TEX_FILE="_output/paper.tex"
                OUTPUT_DIR="_output"
                echo "Found _output/paper.tex" | tee -a "$LOG_FILE"
                break
            elif [ -f "paper.tex" ]; then
                TEX_FILE="paper.tex"
                OUTPUT_DIR="."
                echo "Found paper.tex" | tee -a "$LOG_FILE"
                break
            fi
        done
    fi
    
    # TeXファイルが存在する場合のみ変数を展開
    if [ -f "$TEX_FILE" ]; then
        echo "Processing TeX file: $TEX_FILE" | tee -a "$LOG_FILE"
        
        # \maketitleを先に削除（expand_preamble.pyが実行される前に）
        # 確実に削除するため、grepで確認してからPythonで処理
        if grep -q "\\\\maketitle" "$TEX_FILE" 2>/dev/null; then
            echo "Removing \\maketitle before expand_preamble.py..." | tee -a "$LOG_FILE"
            python3 << 'PYTHON_SCRIPT'
import sys

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    removed = False
    for line in lines:
        if '\\maketitle' in line and not line.strip().startswith('%'):
            new_lines.append('% \\maketitle removed (NAIST format uses \\titlepage)\n')
            removed = True
        else:
            new_lines.append(line)
    
    if removed:
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("  ✓ Removed \\maketitle", file=sys.stderr)
    else:
        print("  ✓ \\maketitle already removed or not found", file=sys.stderr)
except Exception as e:
    print(f"  ✗ Error removing \\maketitle: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
                "$TEX_FILE" || echo "Warning: Failed to remove \\maketitle" | tee -a "$LOG_FILE"
        fi
        
        # 変数が既に展開されているか確認
        # biber 2.21がHomebrewでインストールされているため、backend=biberを使用
        # 古いTeX Liveのbiberとの互換性チェックは不要
        
        # 図のデフォルト配置を独立ページ（[p]）に設定
        if grep -q "\\\\def\\\\fps@figure{htbp}" "$TEX_FILE" 2>/dev/null; then
            echo "Setting default figure placement to [p] (independent page)..." | tee -a "$LOG_FILE"
            sed -i.bak 's/\\def\\fps@figure{htbp}/\\def\\fps@figure{p}/g' "$TEX_FILE" 2>/dev/null || \
            sed -i '' 's/\\def\\fps@figure{htbp}/\\def\\fps@figure{p}/g' "$TEX_FILE" 2>/dev/null || true
            rm -f "$TEX_FILE.bak" 2>/dev/null || true
        fi
        
        if ! grep -q "\$japanese-title\|\$supervisor\|\$lab-name" "$TEX_FILE" 2>/dev/null; then
            echo "Variables already expanded in $TEX_FILE" | tee -a "$LOG_FILE"
            # exit 0  # コメントアウト: bibtex処理のために再コンパイルが必要
        fi
        
        # TeXファイルが完全に生成されるまで待つ（ファイルサイズが安定するまで）
        echo "Waiting for TeX file to be fully generated..." | tee -a "$LOG_FILE"
        PREV_SIZE=0
        STABLE_COUNT=0
        for i in {1..20}; do
            sleep 0.3
            if [ -f "$TEX_FILE" ]; then
                CURRENT_SIZE=$(stat -f "%z" "$TEX_FILE" 2>/dev/null || stat -c "%s" "$TEX_FILE" 2>/dev/null || echo "0")
                if [ "$CURRENT_SIZE" -eq "$PREV_SIZE" ] && [ "$CURRENT_SIZE" -gt 0 ]; then
                    STABLE_COUNT=$((STABLE_COUNT + 1))
                    if [ "$STABLE_COUNT" -ge 3 ]; then
                        echo "TeX file is stable (size: $CURRENT_SIZE bytes)" | tee -a "$LOG_FILE"
                        break
                    fi
                else
                    STABLE_COUNT=0
                    PREV_SIZE="$CURRENT_SIZE"
                fi
            fi
        done
        
        # paper.qmdの更新時刻を確認（YAML変数が最新であることを確認）
        QMD_FILE="paper.qmd"
        QMD_MTIME=0
        if [ -f "$QMD_FILE" ]; then
            QMD_MTIME=$(stat -f "%m" "$QMD_FILE" 2>/dev/null || stat -c "%Y" "$QMD_FILE" 2>/dev/null || echo "0")
            TEX_MTIME=$(stat -f "%m" "$TEX_FILE" 2>/dev/null || stat -c "%Y" "$TEX_FILE" 2>/dev/null || echo "0")
            # paper.qmdがTeXファイルより新しい場合、Quartoのレンダリングが完了するまで待つ
            if [ "$QMD_MTIME" -gt "$TEX_MTIME" ]; then
                echo "paper.qmd is newer than $TEX_FILE. Waiting for Quarto to finish rendering..." | tee -a "$LOG_FILE"
                # TeXファイルが更新されるまで待つ（最大10秒）
                for i in {1..20}; do
                    sleep 0.5
                    TEX_MTIME_NEW=$(stat -f "%m" "$TEX_FILE" 2>/dev/null || stat -c "%Y" "$TEX_FILE" 2>/dev/null || echo "0")
                    if [ "$TEX_MTIME_NEW" -ge "$QMD_MTIME" ]; then
                        echo "TeX file has been updated by Quarto" | tee -a "$LOG_FILE"
                        break
                    fi
                done
            fi
        fi
        
        # TeXファイルが完全に生成されるまで待つ（ファイルサイズが安定するまで）
        echo "Waiting for TeX file to be fully generated..." | tee -a "$LOG_FILE"
        PREV_SIZE=0
        STABLE_COUNT=0
        for i in {1..30}; do
            sleep 0.3
            if [ -f "$TEX_FILE" ]; then
                CURRENT_SIZE=$(stat -f "%z" "$TEX_FILE" 2>/dev/null || stat -c "%s" "$TEX_FILE" 2>/dev/null || echo "0")
                if [ "$CURRENT_SIZE" -eq "$PREV_SIZE" ] && [ "$CURRENT_SIZE" -gt 0 ]; then
                    STABLE_COUNT=$((STABLE_COUNT + 1))
                    if [ "$STABLE_COUNT" -ge 5 ]; then
                        echo "TeX file is stable (size: $CURRENT_SIZE bytes)" | tee -a "$LOG_FILE"
                        break
                    fi
                else
                    STABLE_COUNT=0
                    PREV_SIZE="$CURRENT_SIZE"
                fi
            fi
        done
        
        # expand_preamble.pyを実行（最大2回まで再試行）
        MAX_RETRIES=2
        RETRY_COUNT=0
        while [ "$RETRY_COUNT" -le "$MAX_RETRIES" ]; do
            # TeXファイルの更新時刻を記録
            TEX_MTIME_BEFORE=$(stat -f "%m" "$TEX_FILE" 2>/dev/null || stat -c "%Y" "$TEX_FILE" 2>/dev/null || echo "0")
            
            if [ "$RETRY_COUNT" -eq 0 ]; then
                echo "Expanding YAML variables in $TEX_FILE..." | tee -a "$LOG_FILE"
            else
                echo "Retrying expand_preamble.py (attempt $RETRY_COUNT/$MAX_RETRIES)..." | tee -a "$LOG_FILE"
                sleep 1
            fi
            
            timeout 30 python3 scripts/expand_preamble.py "$TEX_FILE" 2>&1 | head -10 | tee -a "$LOG_FILE" || echo "Warning: expand_preamble.py timed out or failed" | tee -a "$LOG_FILE"
            
            # TeXファイルが更新されたか確認
            sleep 0.5  # ファイルシステムの同期を待つ
            TEX_MTIME_AFTER=$(stat -f "%m" "$TEX_FILE" 2>/dev/null || stat -c "%Y" "$TEX_FILE" 2>/dev/null || echo "0")
            
            # paper.qmdが更新されていないか確認
            if [ -f "$QMD_FILE" ]; then
                QMD_MTIME_NEW=$(stat -f "%m" "$QMD_FILE" 2>/dev/null || stat -c "%Y" "$QMD_FILE" 2>/dev/null || echo "0")
                if [ "$QMD_MTIME_NEW" -gt "$QMD_MTIME" ]; then
                    echo "paper.qmd was updated during processing. Retrying..." | tee -a "$LOG_FILE"
                    QMD_MTIME="$QMD_MTIME_NEW"
                    RETRY_COUNT=$((RETRY_COUNT + 1))
                    continue
                fi
            fi
            
            # 変数が正しく展開されたか確認（$variable-name$形式のプレースホルダーが残っていないか）
            if grep -q "\$fifth-member\$\|\$sixth-member\$\|\$fourth-member\$" "$TEX_FILE" 2>/dev/null; then
                if [ "$RETRY_COUNT" -lt "$MAX_RETRIES" ]; then
                    echo "Some variables were not expanded. Retrying..." | tee -a "$LOG_FILE"
                    RETRY_COUNT=$((RETRY_COUNT + 1))
                    continue
                else
                    echo "Warning: Some variables may not have been expanded after $MAX_RETRIES retries" | tee -a "$LOG_FILE"
                fi
            else
                if [ "$TEX_MTIME_AFTER" -gt "$TEX_MTIME_BEFORE" ]; then
                    echo "TeX file was updated by expand_preamble.py" | tee -a "$LOG_FILE"
                fi
                break
            fi
        done
        
        # Section~\refを\refに置換（数字だけを表示するため）
        # paper.texと_output/paper.texの両方を処理
        for TEX_FILE_TO_PROCESS in "$TEX_FILE" "paper.tex" "_output/paper.tex"; do
            if [ -f "$TEX_FILE_TO_PROCESS" ]; then
                echo "Removing 'Section' prefix from cross-references in $TEX_FILE_TO_PROCESS..." | tee -a "$LOG_FILE"
                # Pythonで確実に置換（sedのエスケープ問題を回避）
                python3 << 'PYTHON_SCRIPT'
import sys
import re

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    # Section~\ref{...}を\ref{...}に置換
    pattern = r'Section~\\ref\{([^}]+)\}'
    if re.search(pattern, content):
        content = re.sub(pattern, r'\\ref{\1}', content)
        modified = True
        print(f"  ✓ Replaced Section~\\ref with \\ref in {sys.argv[1]}", file=sys.stderr)
    
    if modified:
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        print(f"  No Section~\\ref found in {sys.argv[1]}", file=sys.stderr)
except Exception as e:
    print(f"  ✗ Error processing {sys.argv[1]}: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
                "$TEX_FILE_TO_PROCESS" || echo "Warning: Failed to remove Section prefix from $TEX_FILE_TO_PROCESS" | tee -a "$LOG_FILE"
            fi
        done
        echo "✓ Processed Section prefix removal" | tee -a "$LOG_FILE"
        
        # \edatestrを設定（\smonth, \sday, \esyearから）
        if grep -q "\\\\smonth{" "$TEX_FILE" 2>/dev/null && ! grep -q "\\\\def\\\\edatestr" "$TEX_FILE" 2>/dev/null; then
            echo "Adding \\def\\edatestr (fallback)..." | tee -a "$LOG_FILE"
            python3 << 'PYTHON_SCRIPT'
import sys
import re

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    # \smonth, \sday, \esyearから値を取得
    month_match = re.search(r'\\smonth\{([^}]+)\}', content)
    day_match = re.search(r'\\sday\{([^}]+)\}', content)
    year_match = re.search(r'\\esyear\{([^}]+)\}', content)
    
    if month_match and day_match and year_match:
        month = month_match.group(1)
        day = day_match.group(1)
        year = year_match.group(1)
        
        # 月名を取得
        try:
            month_num = int(month)
            month_names = {
                1: 'January', 2: 'February', 3: 'March', 4: 'April',
                5: 'May', 6: 'June', 7: 'July', 8: 'August',
                9: 'September', 10: 'October', 11: 'November', 12: 'December'
            }
            month_name = month_names.get(month_num, 'February')
        except ValueError:
            month_name = 'February'
        
        edatestr_value = f'{month_name} {day}, {year}'
        
        # \begin{document}の前に追加
        if '\\begin{document}' in content:
            edatestr_line = f'\\def\\edatestr{{{edatestr_value}}}\n'
            content = content.replace('\\begin{document}', edatestr_line + '\\begin{document}')
            with open(sys.argv[1], 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Added \\def\\edatestr{{{edatestr_value}}}", file=sys.stderr)
        else:
            print("  ✗ \\begin{document} not found", file=sys.stderr)
    else:
        print("  ✗ \\smonth, \\sday, or \\esyear not found", file=sys.stderr)
except Exception as e:
    print(f"  ✗ Error: {e}", file=sys.stderr)
PYTHON_SCRIPT
                "$TEX_FILE" || echo "Warning: Failed to add \\def\\edatestr" | tee -a "$LOG_FILE"
        fi
        
        # \DeclareCaptionLabelSeparatorを削除（エラーの原因となる可能性があるため）
        if grep -q "DeclareCaptionLabelSeparator{space}" "$TEX_FILE" 2>/dev/null; then
            echo "Removing DeclareCaptionLabelSeparator to fix spacefactor error..." | tee -a "$LOG_FILE"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' '/DeclareCaptionLabelSeparator{space}/d' "$TEX_FILE"
            else
                sed -i '/DeclareCaptionLabelSeparator{space}/d' "$TEX_FILE"
            fi
            echo "✓ Removed DeclareCaptionLabelSeparator" | tee -a "$LOG_FILE"
        fi
    fi  # expand_preamble.pyの実行ブロックの終了
    
    # \section{はじめに}の直後に\setcounter{secnumdepth}{3}を追加
    # \sectionコマンドが実行された後でも確実にsecnumdepthが3に設定されるように
    echo "Adding \\setcounter{secnumdepth}{3} after \\section{はじめに}..." | tee -a "$LOG_FILE"
    python3 << 'PYTHON_SCRIPT'
import re
import sys

tex_file = sys.argv[1]

with open(tex_file, 'r', encoding='utf-8') as f:
    content = f.read()

# \section{はじめに}の直後に\setcounter{secnumdepth}{3}を追加
# ただし、既に存在する場合は追加しない
pattern = r'(\\section\{はじめに\}[^\n]*\n)'
if re.search(pattern, content):
    # 既に\setcounter{secnumdepth}{3}が直後にあるか確認
    if not re.search(r'\\section\{はじめに\}[^\n]*\n[^\n]*\\setcounter\{secnumdepth\}', content):
        replacement = r'\1\\setcounter{secnumdepth}{3}\n'
        content = re.sub(pattern, replacement, content, count=1)
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✓ Added \\setcounter{secnumdepth}{3} after \\section{はじめに}", file=sys.stderr)
    else:
        print("  ✓ \\setcounter{secnumdepth}{3} already exists after \\section{はじめに}", file=sys.stderr)
else:
    print("  ⚠ \\section{はじめに} not found", file=sys.stderr)
PYTHON_SCRIPT
    "$TEX_FILE"
    echo "✓ Added \\setcounter{secnumdepth}{3} after \\section{はじめに}" | tee -a "$LOG_FILE"
    
fi  # if [ -f "scripts/expand_preamble.py" ]の終了

# \figurenameと\tablenameはQuartoのlanguageオプション（crossref-fig-title, crossref-tbl-title）で制御するため、ここでは処理しない

# Quartoが自動的に追加した\printbibliography（headingオプションなし）を削除
# 「参考文献」セクションで既に\printbibliography[heading=none]を使用しているため
# 常に実行して、\printbibliography（headingオプションなし）を確実に削除
if [ -f "$TEX_FILE" ]; then
    echo "Removing auto-added \\printbibliography (without heading=none)..." | tee -a "$LOG_FILE"
    python3 << 'PYTHON_SCRIPT'
import sys
import re

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    removed = False
    
    for i, line in enumerate(lines):
        # \printbibliography[heading=none]は保持
        if '\\printbibliography[heading=none]' in line:
            new_lines.append(line)
        # \printbibliography（headingオプションなし）を削除
        elif line.strip() == '\\printbibliography':
            removed = True
            # 前後の空行も削除（ただし、連続する空行は1つだけ残す）
            if new_lines and new_lines[-1].strip() == '':
                new_lines.pop()
            continue
        else:
            new_lines.append(line)
    
    if removed:
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("  ✓ Removed auto-added \\printbibliography", file=sys.stderr)
    else:
        print("  No auto-added \\printbibliography found", file=sys.stderr)
except Exception as e:
    print(f"  ✗ Error: {e}", file=sys.stderr)
PYTHON_SCRIPT
    "$TEX_FILE" || echo "Warning: Failed to remove \\printbibliography" | tee -a "$LOG_FILE"
    echo "✓ Processed \\printbibliography removal" | tee -a "$LOG_FILE"
fi

# テーブルの配置はQuartoのtbl-posオプションで制御するため、ここでは処理しない
# ユーザーはpaper.qmdでtbl-pos="p"などを指定して制御する

# 図の配置はQuartoのfig-posオプションで制御するため、ここでは処理しない
# ユーザーはpaper.qmdでfig-pos="p"などを指定して制御する

# 最後に再度\printbibliography（headingオプションなし）を削除（Quartoが再レンダリング時に追加する可能性があるため）
if [ -f "$TEX_FILE" ]; then
    python3 << 'PYTHON_SCRIPT'
import sys
import re

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    removed = False
    
    for i, line in enumerate(lines):
        # \printbibliography[heading=none]は保持
        if '\\printbibliography[heading=none]' in line:
            new_lines.append(line)
        # \printbibliography（headingオプションなし）を削除
        elif line.strip() == '\\printbibliography':
            removed = True
            # 前の行が空行なら削除
            if new_lines and new_lines[-1].strip() == '':
                new_lines.pop()
            continue
        else:
            new_lines.append(line)
    
    if removed:
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("  ✓ Removed auto-added \\printbibliography (final check)", file=sys.stderr)
except Exception as e:
    print(f"  ✗ Error: {e}", file=sys.stderr)
PYTHON_SCRIPT
    "$TEX_FILE" || true
fi

# \eabstract{...}の後に\def\eabstracttext{...}を追加（naist-mcommon.styが読み込まれていない場合のフォールバック）
if [ -f "$TEX_FILE" ]; then
    if grep -q "\\\\eabstract{" "$TEX_FILE" 2>/dev/null && ! grep -q "\\\\def\\\\eabstracttext" "$TEX_FILE" 2>/dev/null; then
            echo "Adding \\def\\eabstracttext (fallback)..." | tee -a "$LOG_FILE"
            python3 << 'PYTHON_SCRIPT'
import sys
import re

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    eabstract_found = False
    
    for i, line in enumerate(lines):
        if '\\eabstract{' in line and not eabstract_found:
            eabstract_found = True
            new_lines.append(line)
            # \eabstract{...}の内容を抽出
            match = re.search(r'\\eabstract\{([^}]+)\}', line)
            if match:
                value = match.group(1)
                # \def\eabstracttext{...}を追加
                new_lines.append(f'\\def\\eabstracttext{{{value}}}\n')
                print("  ✓ Added \\def\\eabstracttext", file=sys.stderr)
        else:
            new_lines.append(line)
    
    if eabstract_found:
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
except Exception as e:
    print(f"  ✗ Error: {e}", file=sys.stderr)
PYTHON_SCRIPT
                "$TEX_FILE" || echo "Warning: Failed to add \\def\\eabstracttext" | tee -a "$LOG_FILE"
        fi
        
        # NAIST要素が設定されているか確認（expand_preamble.pyが失敗した場合のフォールバック）
        echo "Checking NAIST elements..." | tee -a "$LOG_FILE"
        if ! grep -q "\\\\studentnumber{" "$TEX_FILE" 2>/dev/null; then
            echo "Adding NAIST elements (fallback)..." | tee -a "$LOG_FILE"
            python3 << 'PYTHON_SCRIPT'
import sys

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    doc_start_idx = None
    for i, line in enumerate(lines):
        if '\\begin{document}' in line:
            doc_start_idx = i
            break
    
    if doc_start_idx is None:
        print("  ✗ \\begin{document} not found", file=sys.stderr)
        sys.exit(1)
    
    # 既にNAIST要素があるか確認
    preamble = ''.join(lines[:doc_start_idx])
    if '\\studentnumber{' in preamble:
        print("  ✓ NAIST elements already present", file=sys.stderr)
        sys.exit(0)
    
    # NAIST要素を追加
    naist_elements = [
        '% NAISTフォーマットの必須要素\n',
        '\\studentnumber{123456}\n',
        '\\doctitle{\\mastersthesis}\n',
        '\\major{\\engineering}\n',
        '\\program{\\ise}\n'
    ]
    new_lines = lines[:doc_start_idx] + naist_elements + lines[doc_start_idx:]
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("  ✓ Added NAIST elements", file=sys.stderr)
except Exception as e:
    print(f"  ✗ Error: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_SCRIPT
                "$TEX_FILE" || echo "Warning: Failed to add NAIST elements" | tee -a "$LOG_FILE"
        else
            echo "✓ NAIST elements already present" | tee -a "$LOG_FILE"
        fi
        
        # 変数が展開されたか確認（上記の再試行処理で既に処理されているため、ここでは警告のみ）
        if grep -q "\$japanese-title\|\$supervisor\|\$lab-name\|\$fifth-member\$\|\$sixth-member\$\|\$fourth-member\$" "$TEX_FILE" 2>/dev/null; then
            echo "Warning: Some variables may not have been expanded. Check the log above." | tee -a "$LOG_FILE"
        fi

        # \maketitleを再度確認して削除（expand_preamble.py実行後）
        if grep -q "\\\\maketitle" "$TEX_FILE" 2>/dev/null; then
            echo "Removing \\maketitle after expand_preamble.py..." | tee -a "$LOG_FILE"
            python3 << 'PYTHON_SCRIPT'
import sys

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    removed = False
    for line in lines:
        if '\\maketitle' in line and not line.strip().startswith('%'):
            new_lines.append('% \\maketitle removed (NAIST format uses \\titlepage)\n')
            removed = True
        else:
            new_lines.append(line)
    
    if removed:
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("  ✓ Removed \\maketitle", file=sys.stderr)
except Exception as e:
    print(f"  ✗ Error: {e}", file=sys.stderr)
PYTHON_SCRIPT
                "$TEX_FILE" || true
        fi

    # Quartoが生成したPDFを削除（post-render.shで再生成するため）
    # これにより、Quartoの自動実行とpost-render.shの実行が重複することを防ぐ
    if [ -f "$OUTPUT_DIR/paper.pdf" ]; then
        PDF_MTIME=$(stat -f "%m" "$OUTPUT_DIR/paper.pdf" 2>/dev/null || stat -c "%Y" "$OUTPUT_DIR/paper.pdf" 2>/dev/null || echo "0")
        TEX_MTIME=$(stat -f "%m" "$TEX_FILE" 2>/dev/null || stat -c "%Y" "$TEX_FILE" 2>/dev/null || echo "0")
        # PDFがTeXファイルより新しい場合（Quartoが生成したもの）、削除
        if [ "$PDF_MTIME" -gt "$TEX_MTIME" ]; then
            echo "Removing Quarto-generated PDF (will regenerate with post-render.sh)..." | tee -a "$LOG_FILE"
            rm -f "$OUTPUT_DIR/paper.pdf"
        fi
    fi
    
    # 修正したTeXファイルをOUTPUT_DIRにコピー（_output/paper.texが存在しない場合）
    # Quarto Previewは_outputディレクトリに.texファイルを生成しないため、
    # 修正したpaper.texを_output/paper.texにコピーする必要がある
    if [ "$OUTPUT_DIR" != "." ] && [ ! -f "$OUTPUT_DIR/paper.tex" ]; then
        echo "Copying modified paper.tex to $OUTPUT_DIR/paper.tex..." | tee -a "$LOG_FILE"
        cp "$TEX_FILE" "$OUTPUT_DIR/paper.tex" || {
            echo "Warning: Failed to copy $TEX_FILE to $OUTPUT_DIR/paper.tex" | tee -a "$LOG_FILE"
        }
        # 依存ファイルもコピー（template/ディレクトリへの参照が相対パスで解決されるように）
        # ただし、既に存在する場合はスキップ
    fi
    
    # 展開されたTeXファイルからPDFを再生成（xelatexとbibtex/biberを使用）
    # 既に再生成済みかチェック（無限ループ防止）
    REGEN_FLAG_FILE="$OUTPUT_DIR/.post-render-regenerated"
    if [ -f "$REGEN_FLAG_FILE" ] && [ -f "$OUTPUT_DIR/paper.pdf" ] && [ "$REGEN_FLAG_FILE" -nt "$TEX_FILE" ]; then
        echo "PDF already regenerated. Skipping..." | tee -a "$LOG_FILE"
    else
        cd "$OUTPUT_DIR" || exit 1
        echo "Regenerating PDF with expanded variables and bibliography..." | tee -a "$LOG_FILE"
        echo "  (This will run xelatex 3 times + bibtex/biber 1 time)" | tee -a "$LOG_FILE"
        
        # TEXINPUTSを設定して、template/ディレクトリへの参照を解決できるようにする
        # _outputディレクトリから見ると、template/は../template/になる
        if [ "$OUTPUT_DIR" != "." ]; then
            export TEXINPUTS=".:$SCRIPT_DIR:$SCRIPT_DIR/template:"
        fi
        
        # 第1回: xelatexを実行して.auxと.bcfファイルを生成
        echo "  [1/4] Running xelatex (generating .aux and .bcf)..." | tee -a "$LOG_FILE"
        xelatex -interaction=nonstopmode -halt-on-error paper.tex > paper-xelatex-1.log 2>&1 || {
            echo "  ✗ xelatex (1st pass) failed. Check paper-xelatex-1.log" | tee -a "$LOG_FILE"
            tail -20 paper-xelatex-1.log | tee -a "$LOG_FILE"
        }
        
        # biblatexのbackendを確認（.bcfファイルの有無で判定）
        # .bcfファイルが存在する場合はbiber、存在しない場合はbibtexを使用
        if [ -f "paper.bcf" ]; then
            echo "  [2/4] Running biber (processing bibliography)..." | tee -a "$LOG_FILE"
            biber paper > paper-biber.log 2>&1 || {
                echo "  ⚠ biber failed (version mismatch). Continuing anyway..." | tee -a "$LOG_FILE"
                tail -5 paper-biber.log | tee -a "$LOG_FILE"
                echo "  Note: Bibliography may not be generated. Please upgrade biber to 2.15+ for biblatex 3.21." | tee -a "$LOG_FILE"
                # biberが失敗しても続行（空の.bblファイルが生成される可能性がある）
            }
        else
            echo "  [2/4] Running bibtex (processing bibliography)..." | tee -a "$LOG_FILE"
            bibtex paper > paper-bibtex.log 2>&1 || {
                echo "  ✗ bibtex failed. Check paper-bibtex.log" | tee -a "$LOG_FILE"
                tail -10 paper-bibtex.log | tee -a "$LOG_FILE"
            }
        fi
        
        # 第2回: xelatexを実行して引用を埋め込む
        echo "  [3/4] Running xelatex (embedding citations)..." | tee -a "$LOG_FILE"
        xelatex -interaction=nonstopmode -halt-on-error paper.tex > paper-xelatex-2.log 2>&1 || {
            echo "  ✗ xelatex (2nd pass) failed. Check paper-xelatex-2.log" | tee -a "$LOG_FILE"
            tail -20 paper-xelatex-2.log | tee -a "$LOG_FILE"
        }
        
        # 第3回: xelatexを実行して相互参照を解決
        echo "  [4/4] Running xelatex (resolving cross-references)..." | tee -a "$LOG_FILE"
        xelatex -interaction=nonstopmode -halt-on-error paper.tex > paper-xelatex-3.log 2>&1 || {
            echo "  ✗ xelatex (3rd pass) failed. Check paper-xelatex-3.log" | tee -a "$LOG_FILE"
            tail -20 paper-xelatex-3.log | tee -a "$LOG_FILE"
        }
        
        # 再生成フラグを設定
        touch "$REGEN_FLAG_FILE"
        echo "✓ PDF regeneration complete" | tee -a "$LOG_FILE"
        cd "$SCRIPT_DIR" || exit 1
    fi

        # .texファイル内の?contents?などを置き換える
        echo "Replacing ?contents?, ?listfigure?, ?listtable?, ?figure?, ?table? in $TEX_FILE..." | tee -a "$LOG_FILE"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's/?contents?/Contents/g' "$TEX_FILE"
            sed -i '' 's/?listfigure?/List of Figures/g' "$TEX_FILE"
            sed -i '' 's/?listtable?/List of Tables/g' "$TEX_FILE"
            sed -i '' 's/?figure?/Figure/g' "$TEX_FILE"
            sed -i '' 's/?table?/Table/g' "$TEX_FILE"
        else
            sed -i 's/?contents?/Contents/g' "$TEX_FILE"
            sed -i 's/?listfigure?/List of Figures/g' "$TEX_FILE"
            sed -i 's/?listtable?/List of Tables/g' "$TEX_FILE"
            sed -i 's/?figure?/Figure/g' "$TEX_FILE"
            sed -i 's/?table?/Table/g' "$TEX_FILE"
        fi
        
        # .toc、.lof、.lotファイルも処理（?contents?を置き換える）
        for toc_file in "$OUTPUT_DIR/paper.toc" "$OUTPUT_DIR/paper.lof" "$OUTPUT_DIR/paper.lot"; do
            if [ -f "$toc_file" ]; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' 's/?contents?/Contents/g' "$toc_file"
                    sed -i '' 's/?listfigure?/List of Figures/g' "$toc_file"
                    sed -i '' 's/?listtable?/List of Tables/g' "$toc_file"
                    sed -i '' 's/?figure?/Figure/g' "$toc_file"
                    sed -i '' 's/?table?/Table/g' "$toc_file"
                else
                    sed -i 's/?contents?/Contents/g' "$toc_file"
                    sed -i 's/?listfigure?/List of Figures/g' "$toc_file"
                    sed -i 's/?listtable?/List of Tables/g' "$toc_file"
                    sed -i 's/?figure?/Figure/g' "$toc_file"
                    sed -i 's/?table?/Table/g' "$toc_file"
                fi
            fi
        done

    # PDFをルートディレクトリと_outputディレクトリにコピー
    if [ -f "$OUTPUT_DIR/paper.pdf" ]; then
        cp "$OUTPUT_DIR/paper.pdf" paper.pdf 2>/dev/null || true
        if [ "$OUTPUT_DIR" != "_output" ] && [ -d "_output" ]; then
            cp "$OUTPUT_DIR/paper.pdf" _output/paper.pdf 2>/dev/null || true
        fi
        echo "✓ YAML variables expanded and PDF regenerated" | tee -a "$LOG_FILE"
    fi
else
    echo "Warning: TeX file not found. Variables will not be expanded." | tee -a "$LOG_FILE"
    echo "  This may be normal if Quarto is still rendering." | tee -a "$LOG_FILE"
    exit 0
fi

# 最終確認: \printbibliography（headingオプションなし）を削除（Quartoが再レンダリング時に追加する可能性があるため）
# また、Section~\refを\refに置換（最終確認）
for TEX_FILE_FINAL in "$TEX_FILE" "paper.tex" "_output/paper.tex"; do
    if [ -f "$TEX_FILE_FINAL" ]; then
        # \printbibliographyの削除
        python3 << 'PYTHON_SCRIPT'
import sys
import re

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    removed = False
    
    for i, line in enumerate(lines):
        # \printbibliography[heading=none]は保持
        if '\\printbibliography[heading=none]' in line:
            new_lines.append(line)
        # \printbibliography（headingオプションなし）を削除
        elif line.strip() == '\\printbibliography':
            removed = True
            # 前の行が空行なら削除
            if new_lines and new_lines[-1].strip() == '':
                new_lines.pop()
            continue
        else:
            new_lines.append(line)
    
    if removed:
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"  ✓ Removed auto-added \\printbibliography from {sys.argv[1]} (final check)", file=sys.stderr)
except Exception as e:
    print(f"  ✗ Error: {e}", file=sys.stderr)
PYTHON_SCRIPT
        "$TEX_FILE_FINAL" || true
        
        # Section~\refを\refに置換（最終確認）
        python3 << 'PYTHON_SCRIPT'
import sys
import re

try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    # Section~\ref{...}を\ref{...}に置換
    pattern = r'Section~\\ref\{([^}]+)\}'
    if re.search(pattern, content):
        content = re.sub(pattern, r'\\ref{\1}', content)
        modified = True
        print(f"  ✓ Replaced Section~\\ref with \\ref in {sys.argv[1]} (final check)", file=sys.stderr)
    
    if modified:
        with open(sys.argv[1], 'w', encoding='utf-8') as f:
            f.write(content)
except Exception as e:
    print(f"  ✗ Error: {e}", file=sys.stderr)
PYTHON_SCRIPT
        "$TEX_FILE_FINAL" || true
    fi
done

# Quartoのformat-resourcesがルートにコピーしたファイルを削除（template/に存在するため不要）
echo "Removing files copied by Quarto format-resources from root directory..." | tee -a "$LOG_FILE"
cd "$(dirname "$SCRIPT_DIR")" || exit 1
for file in naist-jmthesis.sty naist-mcommon.sty naist-mthesis.sty jpa.bbx jpa.cbx jpa.dbx biblatex-dm.cfg; do
    if [ -f "$file" ] && [ -f "template/$file" ]; then
        # template/に存在する場合のみ削除（元のファイルがtemplate/にあることを確認）
        rm -f "$file"
        echo "  ✓ Removed $file (exists in template/)" | tee -a "$LOG_FILE"
    fi
done
echo "✓ Cleaned up format-resources files from root directory" | tee -a "$LOG_FILE"

