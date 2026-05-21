#!/usr/bin/env python3
"""
Quartoが生成したTeXファイル内のtemplate/preamble.texのYAML変数を展開するスクリプト
"""
import sys
import re
import os
import time

if len(sys.argv) < 2:
    print("Usage: expand_preamble.py <tex_file>")
    sys.exit(1)

tex_file = sys.argv[1]

# ファイルが存在しない場合は、別のパスを試す
if not os.path.exists(tex_file):
    # _output/paper.texまたはpaper.texを試す
    if os.path.exists('_output/paper.tex'):
        tex_file = '_output/paper.tex'
    elif os.path.exists('paper.tex'):
        tex_file = 'paper.tex'
    else:
        print(f"Error: TeX file not found: {sys.argv[1]}")
        sys.exit(1)

# paper.qmdからYAML変数を読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
qmd_file = os.path.join(project_root, 'paper.qmd')

# paper.qmdの更新時刻を確認し、TeXファイルより新しい場合は待機
if os.path.exists(qmd_file) and os.path.exists(tex_file):
    qmd_mtime = os.path.getmtime(qmd_file)
    tex_mtime = os.path.getmtime(tex_file)
    # paper.qmdがTeXファイルより新しい場合、少し待つ（Quartoのレンダリングが完了するまで）
    if qmd_mtime > tex_mtime:
        print(f"  paper.qmd is newer than {tex_file}. Waiting for Quarto to finish rendering...", file=sys.stderr)
        # TeXファイルが更新されるまで待つ（最大5秒）
        for i in range(10):
            time.sleep(0.5)
            if os.path.exists(tex_file):
                new_tex_mtime = os.path.getmtime(tex_file)
                if new_tex_mtime >= qmd_mtime:
                    print(f"  TeX file has been updated by Quarto", file=sys.stderr)
                    break

yaml_vars = {}
# paper.qmdを再度読み込む（最新の値を取得）
with open(qmd_file, 'r', encoding='utf-8') as f:
    content = f.read()
    # YAMLフロントマターを抽出
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if match:
        yaml_content = match.group(1)
        # 各行を処理
        current_key = None
        current_value = []
        indent_level = 0
        in_format_section = False
        
        for line in yaml_content.split('\n'):
            line_stripped = line.strip()
            line_indent = len(line) - len(line.lstrip())
            
            # format:セクションの開始/終了を検出
            if line_stripped.startswith('format:'):
                in_format_section = True
                # format: naist-pdf: のような形式を処理
                if ':' in line_stripped:
                    parts = line_stripped.split(':', 1)
                    if len(parts) > 1:
                        format_name = parts[1].strip()
                        # format: naist-pdf: の場合は、次の行から開始
                        continue
                continue
            elif in_format_section and line_indent == 0 and line_stripped and not line_stripped.startswith(' '):
                # formatセクションの終了（新しいトップレベルのキー）
                in_format_section = False
            
            # formatセクション内でも、number-depthは読み取る
            if in_format_section:
                # number-depth: 3 のような形式を処理（インデントされた行）
                if line_indent > 0 and ':' in line_stripped and not line_stripped.startswith('-') and not line_stripped.startswith('|'):
                    key, value = line_stripped.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key == 'number-depth':
                        yaml_vars['number-depth'] = value
                        print(f"  Found number-depth in format section: {value}", file=sys.stderr)
                continue
            
            # bibliography:もスキップ
            if line_stripped.startswith('bibliography:'):
                continue
            
            # キー:値の形式
            if ':' in line and not line_stripped.startswith('-') and not line_stripped.startswith('|'):
                # 前のキーの値を保存
                if current_key:
                    yaml_vars[current_key] = '\n'.join(current_value).strip()
                # 新しいキーを取得
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value == '|':
                    # 複数行の値
                    current_key = key
                    current_value = []
                else:
                    yaml_vars[key] = value
                    current_key = None
                    current_value = []
            elif current_key and (line.startswith('  ') or line.startswith('\t')):
                # 複数行の値の続き
                current_value.append(line.lstrip())
            elif line_stripped == '':
                # 空行は無視
                continue
        # 最後のキーの値を保存
        if current_key:
            yaml_vars[current_key] = '\n'.join(current_value).strip()
        
        # デバッグ: 読み込んだ変数を表示
        print(f"✓ Loaded {len(yaml_vars)} YAML variables")
        for key in ['supervisor', 'lab-name-japanese', 'japanese-year', 'submission-month', 'submission-day', 'number-depth']:
            if key in yaml_vars:
                print(f"  {key}: {yaml_vars[key][:50]}")

# 変数マッピング（ハイフンをアンダースコアに変換）
var_map = {}
for key, value in yaml_vars.items():
    # $key$形式で使用できるようにする
    var_map[key] = value
    # ハイフンをアンダースコアに変換したキーも追加
    var_map[key.replace('-', '-')] = value

# 生成されたTeXファイルを読み込んで変数を展開
with open(tex_file, 'r', encoding='utf-8') as f:
    tex_content = f.read()

# Quartoはinclude-in-headerで指定されたファイルの内容を直接挿入するため、
# \input{template/header.tex}というコマンドは生成されない
# そのため、生成されたTeXファイル内の$variable-name$を直接展開する

# number-depthを取得（デフォルトは3）
number_depth = yaml_vars.get('number-depth', '3')
# format: naist-pdf: number-depth: 3 のような形式もチェック
if 'number-depth' not in yaml_vars:
    # format: naist-pdf: セクションを確認
    for key in yaml_vars.keys():
        if 'format' in key.lower() or 'naist' in key.lower():
            # ネストされた構造を確認する必要があるが、簡易的にデフォルト値を使用
            pass

# YAML変数を展開（$var-name$形式）
for var_name, var_value in yaml_vars.items():
    # $var-name$形式を置換
    placeholder = '$' + var_name + '$'
    # YAML変数の値で、数式モード内の\piを正しく処理
    # YAMLでは$\\pi$と書くと、現在のパース処理では$\\\\pi$（4つのバックスラッシュ）として読み込まれる
    # これを$\pi$（LaTeXの数式モード、バックスラッシュ1つ）に変換する
    var_value_escaped = var_value
    # パターン1: $\\\\pi$（YAMLでパースされた2つのバックスラッシュ）→ $\pi$（LaTeXの数式モード）
    # YAMLでは$\\pi$と書くと、パース後は$\\\\pi$（2つのバックスラッシュ）として読み込まれる
    # これを$\pi$（LaTeXの数式モード、バックスラッシュ1つ）に変換する
    # 正規表現で$\\\\pi$をマッチし、lambda関数で置換（エスケープ問題を回避）
    var_value_escaped = re.sub(r'\$\\\\pi\$', lambda m: '$\\pi$', var_value_escaped)
    # パターン2: $\\pi$（既に1つのバックスラッシュの場合）→ $\pi$（そのまま）
    # これは通常発生しないが、念のため
    var_value_escaped = re.sub(r'\$\\pi\$', lambda m: '$\\pi$', var_value_escaped)
    # パターン3: \\pi（数式モード外の2つのバックスラッシュ）→ \pi
    # ただし、$...$で囲まれていない場合のみ
    # $...$で囲まれていない\\piを\piに変換（置換文字列はraw stringを使用）
    # ただし、このパターンは通常発生しないので、コメントアウト
    # var_value_escaped = re.sub(r'(?<!\$)\\\\pi(?!\$)', lambda m: '\\pi', var_value_escaped)
    tex_content = tex_content.replace(placeholder, var_value_escaped)

# number-depthを展開（$number-depth$形式）
if '$number-depth$' in tex_content:
    tex_content = tex_content.replace('$number-depth$', number_depth)
    print(f"  Expanded $number-depth$ to {number_depth}", file=sys.stderr)

# デフォルト値（header-expanded.texに埋め込まれている値）を置換
# 研究室名
if 'lab-name-japanese' in yaml_vars:
    # \jlabname{xxx 研究室} を \jlabname{実際の値} に置換
    # 正規表現のエスケープ問題を回避するため、文字列置換を使用
    old_value = '\\jlabname{xxx 研究室}'
    new_value = f'\\jlabname{{{yaml_vars["lab-name-japanese"]}}}'
    if old_value in tex_content:
        print(f"  Replacing lab-name-japanese: {yaml_vars['lab-name-japanese']}")
        tex_content = tex_content.replace(old_value, new_value)
    else:
        print(f"  Warning: lab-name-japanese pattern not found in TeX file")
if 'lab-name-english' in yaml_vars:
    # \elabname{xxx Lab.} を \elabname{実際の値} に置換
    old_value = '\\elabname{xxx Lab.}'
    new_value = f'\\elabname{{{yaml_vars["lab-name-english"]}}}'
    if old_value in tex_content:
        tex_content = tex_content.replace(old_value, new_value)

# 審査委員
if 'supervisor' in yaml_vars:
    # \cmembers{○○ ○○ 教授}{（主指導教員，情報科学領域）} の最初の引数を置換
    # 文字列置換を使用（正規表現のエスケープ問題を回避）
    old_value = '\\cmembers{○○ ○○ 教授}{（主指導教員，情報科学領域）}'
    new_value = f'\\cmembers{{{yaml_vars["supervisor"]}}}{{（主指導教員，情報科学領域）}}'
    if old_value in tex_content:
        print(f"  Replacing supervisor: {yaml_vars['supervisor']}")
        tex_content = tex_content.replace(old_value, new_value)
    else:
        print(f"  Warning: supervisor pattern not found in TeX file")
    # \ecmembers内のProfessor ○○ ○○ 教授も置換
    old_prof_value = 'Professor ○○ ○○ 教授'
    new_prof_value = f'Professor {yaml_vars["supervisor"]}'
    if old_prof_value in tex_content:
        tex_content = tex_content.replace(old_prof_value, new_prof_value)

if 'co-supervisor' in yaml_vars:
    # \cmembersの3番目の引数（副指導教員）を置換
    # パターン: \cmembers{...}{...}\n         {○○ ○○ 教授}{（副指導教員，情報科学領域）}
    # 複数行に対応（改行や空白を考慮）
    # まず、\cmembersの後に続く行で、{○○ ○○ 教授}{（副指導教員，情報科学領域）}を探す
    # 正規表現を使用（複数行対応が必要なため）
    pattern = r'(\s+)\{○○ ○○ 教授\}\s*\{（副指導教員，情報科学領域）\}'
    if re.search(pattern, tex_content, flags=re.MULTILINE):
        tex_content = re.sub(
            pattern,
            lambda m: f'{m.group(1)}{{{yaml_vars["co-supervisor"]}}}{{（副指導教員，情報科学領域）}}',
            tex_content,
            flags=re.MULTILINE
        )
    # \ecmembers内のProfessor ○○ ○○ 教授（co-supervisor）も置換
    # supervisorが既に置換されている場合、co-supervisorのパターンを探す
    # ただし、supervisorの置換後に実行されるため、既に置換されている可能性がある
    old_co_prof_value = 'Professor ○○ ○○ 教授'
    if old_co_prof_value in tex_content and 'supervisor' in yaml_vars:
        # supervisorが既に置換されている場合、co-supervisorのパターンを探す
        # より具体的なパターンで置換（Co-supervisorの行を探す）
        co_pattern = r'Professor \{yaml_vars\["supervisor"\]\}'
        # 実際には、co-supervisorの行は別の行にあるので、直接置換
        pass  # 上記の置換で対応

if 'third-member' in yaml_vars:
    # \def\tempthird{○○ ○○ 准教授} を置換
    old_value = '\\def\\tempthird{○○ ○○ 准教授}'
    new_value = f'\\def\\tempthird{{{yaml_vars["third-member"]}}}'
    if old_value in tex_content:
        tex_content = tex_content.replace(old_value, new_value)
    # \cmembers内の条件分岐も直接値に置換
    if yaml_vars["third-member"].strip():
        old_cond = '{\\ifx\\tempthird\\empty\\else\\tempthird\\fi}'
        new_cond = f'{{{yaml_vars["third-member"]}}}'
        if old_cond in tex_content:
            tex_content = tex_content.replace(old_cond, new_cond)
            print(f"  Replaced third-member condition with direct value")
        # 念のため、\tempthirdの値を取得して置換（既に\def\tempthirdが設定されている場合）
        tempthird_match = re.search(r'\\def\\tempthird\{([^}]+)\}', tex_content)
        if tempthird_match:
            tempthird_value = tempthird_match.group(1)
            if old_cond in tex_content:
                tex_content = tex_content.replace(old_cond, f'{{{tempthird_value}}}')
                print(f"  Replaced third-member condition using \\tempthird value: {tempthird_value}")
    # $third-member$形式のプレースホルダーも直接値に置換（template/header.texの新しい形式に対応）
    if '$third-member$' in tex_content:
        tex_content = tex_content.replace('$third-member$', yaml_vars["third-member"])
        print(f"  Replaced $third-member$ placeholder with: {yaml_vars['third-member']}")

if 'third-position' in yaml_vars:
    # \def\tempthirdpos{（副指導教員，情報科学領域）} を置換
    old_value = '\\def\\tempthirdpos{（副指導教員，情報科学領域）}'
    new_value = f'\\def\\tempthirdpos{{{yaml_vars["third-position"]}}}'
    if old_value in tex_content:
        tex_content = tex_content.replace(old_value, new_value)
    # \cmembers内の条件分岐も直接値に置換
    if yaml_vars["third-position"].strip():
        old_cond = '{\\ifx\\tempthirdpos\\empty\\else\\tempthirdpos\\fi}'
        new_cond = f'{{{yaml_vars["third-position"]}}}'
        if old_cond in tex_content:
            tex_content = tex_content.replace(old_cond, new_cond)
            print(f"  Replaced third-position condition with direct value")
        # 念のため、\tempthirdposの値を取得して置換（既に\def\tempthirdposが設定されている場合）
        tempthirdpos_match = re.search(r'\\def\\tempthirdpos\{([^}]+)\}', tex_content)
        if tempthirdpos_match:
            tempthirdpos_value = tempthirdpos_match.group(1)
            if old_cond in tex_content:
                tex_content = tex_content.replace(old_cond, f'{{{tempthirdpos_value}}}')
                print(f"  Replaced third-position condition using \\tempthirdpos value: {tempthirdpos_value}")
    # $third-position$形式のプレースホルダーも直接値に置換（template/header.texの新しい形式に対応）
    if '$third-position$' in tex_content:
        tex_content = tex_content.replace('$third-position$', yaml_vars["third-position"])
        print(f"  Replaced $third-position$ placeholder with: {yaml_vars['third-position']}")

# fourth-memberの処理（コメントアウトされている場合は空文字列を設定）
fourth_member_value = yaml_vars.get("fourth-member", "").strip()
if 'fourth-member' in yaml_vars:
    # \def\tempfourth{○○ ○○ 准教授} を置換
    old_value = '\\def\\tempfourth{○○ ○○ 准教授}'
    new_value = f'\\def\\tempfourth{{{yaml_vars["fourth-member"]}}}'
    if old_value in tex_content:
        tex_content = tex_content.replace(old_value, new_value)
    # \cmembers内の条件分岐も直接値に置換
    # {\ifx\tempfourth\empty\else\tempfourth\fi} を {あああああ　准教授} に置換
    if fourth_member_value:
        old_cond = '{\\ifx\\tempfourth\\empty\\else\\tempfourth\\fi}'
        new_cond = f'{{{yaml_vars["fourth-member"]}}}'
        if old_cond in tex_content:
            tex_content = tex_content.replace(old_cond, new_cond)
            print(f"  Replaced fourth-member condition with direct value")
        # 念のため、\tempfourthの値を取得して置換（既に\def\tempfourthが設定されている場合）
        tempfourth_match = re.search(r'\\def\\tempfourth\{([^}]+)\}', tex_content)
        if tempfourth_match:
            tempfourth_value = tempfourth_match.group(1)
            if old_cond in tex_content:
                tex_content = tex_content.replace(old_cond, f'{{{tempfourth_value}}}')
                print(f"  Replaced fourth-member condition using \\tempfourth value: {tempfourth_value}")
else:
    # fourth-memberがコメントアウトされている場合、空文字列を設定
    old_value = '\\def\\tempfourth{○○ ○○ 准教授}'
    if old_value in tex_content:
        tex_content = tex_content.replace(old_value, '\\def\\tempfourth{}')
    # 条件分岐を空文字列に置換
    old_cond = '{\\ifx\\tempfourth\\empty\\else\\tempfourth\\fi}'
    if old_cond in tex_content:
        tex_content = tex_content.replace(old_cond, '{}')
        print(f"  Replaced fourth-member condition with empty (commented out)")

# $fourth-member$形式のプレースホルダーも直接値に置換（template/header.texの新しい形式に対応）
if '$fourth-member$' in tex_content:
    tex_content = tex_content.replace('$fourth-member$', fourth_member_value)
    print(f"  Replaced $fourth-member$ placeholder with: '{fourth_member_value}'")

# fourth-positionの処理（コメントアウトされている場合は空文字列を設定）
fourth_position_value = yaml_vars.get("fourth-position", "").strip()
if 'fourth-position' in yaml_vars:
    # \def\tempfourthpos{（△△大学）} を置換
    old_value = '\\def\\tempfourthpos{（△△大学）}'
    new_value = f'\\def\\tempfourthpos{{{yaml_vars["fourth-position"]}}}'
    if old_value in tex_content:
        tex_content = tex_content.replace(old_value, new_value)
    # \cmembers内の条件分岐も直接値に置換
    if fourth_position_value:
        old_cond = '{\\ifx\\tempfourthpos\\empty\\else\\tempfourthpos\\fi}'
        new_cond = f'{{{yaml_vars["fourth-position"]}}}'
        if old_cond in tex_content:
            tex_content = tex_content.replace(old_cond, new_cond)
            print(f"  Replaced fourth-position condition with direct value")
        # 念のため、\tempfourthposの値を取得して置換（既に\def\tempfourthposが設定されている場合）
        tempfourthpos_match = re.search(r'\\def\\tempfourthpos\{([^}]+)\}', tex_content)
        if tempfourthpos_match:
            tempfourthpos_value = tempfourthpos_match.group(1)
            if old_cond in tex_content:
                tex_content = tex_content.replace(old_cond, f'{{{tempfourthpos_value}}}')
                print(f"  Replaced fourth-position condition using \\tempfourthpos value: {tempfourthpos_value}")
else:
    # fourth-positionがコメントアウトされている場合、空文字列を設定
    old_value = '\\def\\tempfourthpos{（△△大学）}'
    if old_value in tex_content:
        tex_content = tex_content.replace(old_value, '\\def\\tempfourthpos{}')
    # 条件分岐を空文字列に置換
    old_cond = '{\\ifx\\tempfourthpos\\empty\\else\\tempfourthpos\\fi}'
    if old_cond in tex_content:
        tex_content = tex_content.replace(old_cond, '{}')
        print(f"  Replaced fourth-position condition with empty (commented out)")

# $fourth-position$形式のプレースホルダーも直接値に置換（template/header.texの新しい形式に対応）
if '$fourth-position$' in tex_content:
    tex_content = tex_content.replace('$fourth-position$', fourth_position_value)
    print(f"  Replaced $fourth-position$ placeholder with: '{fourth_position_value}'")

# 5人目と6人目の処理
fifth_member_value = yaml_vars.get("fifth-member", "").strip()
fifth_position_value = yaml_vars.get("fifth-position", "").strip()
sixth_member_value = yaml_vars.get("sixth-member", "").strip()
sixth_position_value = yaml_vars.get("sixth-position", "").strip()

# $fifth-member$と$fifth-position$のプレースホルダーを置換
if '$fifth-member$' in tex_content:
    tex_content = tex_content.replace('$fifth-member$', fifth_member_value)
    print(f"  Replaced $fifth-member$ placeholder with: '{fifth_member_value}'")

if '$fifth-position$' in tex_content:
    tex_content = tex_content.replace('$fifth-position$', fifth_position_value)
    print(f"  Replaced $fifth-position$ placeholder with: '{fifth_position_value}'")

if '$sixth-member$' in tex_content:
    tex_content = tex_content.replace('$sixth-member$', sixth_member_value)
    print(f"  Replaced $sixth-member$ placeholder with: '{sixth_member_value}'")

if '$sixth-position$' in tex_content:
    tex_content = tex_content.replace('$sixth-position$', sixth_position_value)
    print(f"  Replaced $sixth-position$ placeholder with: '{sixth_position_value}'")

# \cmembersコマンドの4番目の引数（4人目）が空の場合に処理
# fourth-memberまたはfourth-positionがコメントアウトされている場合、\cmembersの4番目の引数を空にする
if not fourth_member_value or not fourth_position_value:
    # \cmembersコマンドの4番目の引数を空にする
    # パターン: \cmembers{...}{...}\n         {...}{...}\n         {...}{...}\n         {...}{...}
    pattern_cmembers = r'(\\cmembers\{[^}]+\}\{[^}]+\}\s*\n\s+\{[^}]+\}\{[^}]+\}\s*\n\s+\{[^}]+\}\{[^}]+\}\s*\n\s+)\{[^}]+\}\{[^}]+\}'
    if re.search(pattern_cmembers, tex_content):
        tex_content = re.sub(pattern_cmembers, r'\1{}{}', tex_content)
        print(f"  Replaced fourth member arguments in \\cmembers with empty strings")
    else:
        # 別のパターンを試す（改行がない場合）
        pattern_cmembers2 = r'(\\cmembers\{[^}]+\}\{[^}]+\}\s+\{[^}]+\}\{[^}]+\}\s+\{[^}]+\}\{[^}]+\}\s+)\{[^}]+\}\{[^}]+\}'
        if re.search(pattern_cmembers2, tex_content):
            tex_content = re.sub(pattern_cmembers2, r'\1{}{}', tex_content)
            print(f"  Replaced fourth member arguments in \\cmembers with empty strings (pattern2)")

# \addcmembersコマンドの1番目と2番目の引数（5人目と6人目）が空の場合に処理
# $fifth-member$と$sixth-member$のプレースホルダーは既に上で置換されているので、
# ここでは追加の処理は不要（naist-jmthesis.styの条件分岐で自動的に非表示になる）

# 存在しない変数のプレースホルダーを空文字列に置換
# $variable-name$形式のプレースホルダーが残っている場合は、空文字列に置換
pattern = r'\$([a-zA-Z0-9_-]+)\$'
def replace_missing_var(match):
    var_name = match.group(1)
    # YAML変数に存在しない場合は空文字列に置換
    if var_name not in yaml_vars:
        return ''
    return match.group(0)  # 既に置換済みの場合はそのまま
tex_content = re.sub(pattern, replace_missing_var, tex_content)

# \edatestrを設定する処理
# YAML変数から直接値を取得（日本語の日付と同じロジック）
# submission-month, submission-day, english-yearから値を取得
month_value = yaml_vars.get('submission-month', '')
day_value = yaml_vars.get('submission-day', '')
year_value = yaml_vars.get('english-year', '')

# YAML変数から取得できない場合は、\smonth{}, \sday{}, \esyear{}から値を読み取る（フォールバック）
if not month_value or not day_value or not year_value:
    month_match = re.search(r'\\smonth\{([^}]+)\}', tex_content)
    day_match = re.search(r'\\sday\{([^}]+)\}', tex_content)
    year_match = re.search(r'\\esyear\{([^}]+)\}', tex_content)
    
    if month_match:
        month_value = month_match.group(1)
    if day_match:
        day_value = day_match.group(1)
    if year_match:
        year_value = year_match.group(1)

if month_value and day_value and year_value:
    
    # 数値に変換できるか確認
    try:
        month_num = int(month_value)
        # 月名のマッピング
        month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        month_name = month_names.get(month_num, '')
        
        # \edatestrを設定
        edatestr_value = f'{month_name} {day_value}, {year_value}'
        
        # \def\edatestr{}を置換（文字列置換を使用）
        old_edatestr = '\\def\\edatestr{}'
        new_edatestr = f'\\def\\edatestr{{{edatestr_value}}}'
        if old_edatestr in tex_content:
            tex_content = tex_content.replace(old_edatestr, new_edatestr)
            print(f"  Set \\edatestr to: {edatestr_value}")
        
        # $edatestr-placeholder$も置換（念のため）
        if '$edatestr-placeholder$' in tex_content:
            tex_content = tex_content.replace('$edatestr-placeholder$', edatestr_value)
        
        # naist-mcommon.styの\edatestr定義を上書きするため、\defで再定義
        # naist-mcommon.styは\def\edatestr{...}で定義されているため、\renewcommandではなく\defで上書きする必要がある
        # naist-jmthesis.styの読み込み後に\def\edatestr{...}を追加（naist-mcommon.styの定義を上書き）
        # まず、\input{template/naist-jmthesis.sty}の後に追加を試みる
        if '\\input{template/naist-jmthesis.sty}' in tex_content:
            # \input{template/naist-jmthesis.sty}の後に\def\edatestr{...}を追加
            edatestr_redef = f'\n% naist-mcommon.styの\\edatestr定義を上書き\n\\makeatletter\n\\def\\edatestr{{{edatestr_value}}}\n\\makeatother\n'
            # \input{template/naist-jmthesis.sty}の後に\makeatotherがある場合、その後に追加
            old_pattern = '\\input{template/naist-jmthesis.sty}\n\\makeatother'
            if old_pattern in tex_content:
                tex_content = tex_content.replace(old_pattern, old_pattern + edatestr_redef)
            else:
                # \input{template/naist-jmthesis.sty}の直後に追加
                tex_content = tex_content.replace('\\input{template/naist-jmthesis.sty}', 
                                                   '\\input{template/naist-jmthesis.sty}' + edatestr_redef)
            print(f"  Added \\def\\edatestr after naist-jmthesis.sty to: {edatestr_value}")
        
        # \begin{document}の直前にも追加（念のため）
        # naist-mcommon.styの\edatestr定義を確実に上書きするため、\begin{document}の直前に追加
        if '\\begin{document}' in tex_content:
            edatestr_redef_doc = f'% \\edatestrを再定義（naist-mcommon.styの定義を上書き）\n\\makeatletter\n\\def\\edatestr{{{edatestr_value}}}\n\\makeatother\n'
            # \begin{document}の直前に追加（常に追加して、naist-mcommon.styの定義を確実に上書き）
            tex_content = tex_content.replace('\\begin{document}', edatestr_redef_doc + '\\begin{document}')
            print(f"  Added \\def\\edatestr before \\begin{{document}} to: {edatestr_value}")
    except ValueError:
        # 数値に変換できない場合は、そのまま使用
        pass

# Quartoが設定した\contentsnameを英語に変更
# Quartoは\AtBeginDocument内で\contentsnameを設定するため、それを上書き
import re

# ?contents?、?listfigure?、?listtable?を日本語に変更（Mtex形式）
# これらの文字列は、LaTeXのコンパイル時に\contentsname、\listfigurename、\listtablenameとして展開される
# しかし、PDFに直接表示される場合は、文字列置換で対応
tex_content = tex_content.replace('?contents?', '目次')
tex_content = tex_content.replace('?listfigure?', '図目次')
tex_content = tex_content.replace('?listtable?', '表目次')
# 大文字バージョンも対応
tex_content = tex_content.replace('?Contents?', '目次')
tex_content = tex_content.replace('?Listfigure?', '図目次')
tex_content = tex_content.replace('?Listtable?', '表目次')
# 生成された.tocファイルや.lofファイル、.lotファイルにも含まれる可能性があるため、
# これらのファイルも処理する必要があるかもしれないが、現時点ではTeXファイルのみ処理

# \contentsnameの設定を探して置換（Mtexに合わせて日本語に統一）
tex_content = re.sub(
    r'\\renewcommand\*\\contentsname\{Table of contents\}',
    r'\\renewcommand*\\contentsname{目次}',
    tex_content
)
tex_content = re.sub(
    r'\\newcommand\\contentsname\{Table of contents\}',
    r'\\newcommand\\contentsname{目次}',
    tex_content
)
# 既に設定されている\contentsnameも確実に「目次」に変更（Mtex形式）
tex_content = re.sub(
    r'\\renewcommand\*\\contentsname\{[^}]+\}',
    r'\\renewcommand*\\contentsname{目次}',
    tex_content
)
tex_content = re.sub(
    r'\\newcommand\\contentsname\{[^}]+\}',
    r'\\newcommand\\contentsname{目次}',
    tex_content
)
tex_content = re.sub(
    r'\\renewcommand\*\\listfigurename\{[^}]+\}',
    r'\\renewcommand*\\listfigurename{図目次}',
    tex_content
)
tex_content = re.sub(
    r'\\newcommand\\listfigurename\{[^}]+\}',
    r'\\newcommand\\listfigurename{List of Figures}',
    tex_content
)
tex_content = re.sub(
    r'\\renewcommand\*\\listtablename\{[^}]+\}',
    r'\\renewcommand*\\listtablename{表目次}',
    tex_content
)
tex_content = re.sub(
    r'\\newcommand\\listtablename\{[^}]+\}',
    r'\\newcommand\\listtablename{List of Tables}',
    tex_content
)

# \listoffiguresの前の\newpageは保持（図目次は改ページ）
# \listoftablesの前の\newpageを削除（表目次は改ページしない）
# \newpage\listoftables を \listoftables に変更
tex_content = re.sub(r'\\newpage\s*\\listoftables', r'\\listoftables', tex_content)

# Quartoが生成した\hypersetupを削除（本文に表示されないようにする）
# pdftitle、pdfauthor、pdflang、pdfcreatorが含まれる\hypersetupをすべて削除
# 手動削除のロジックを使用（確実に動作する方法）
removed_count = 0
pattern = r'\\hypersetup\s*\{'
matches = list(re.finditer(pattern, tex_content))
for match in matches:
    start = match.start()
    depth = 1
    i = match.end()
    while i < len(tex_content):
        if tex_content[i] == '{':
            depth += 1
        elif tex_content[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                snippet = tex_content[start:end]
                if any(keyword in snippet for keyword in ['pdftitle', 'pdfauthor', 'pdflang', 'pdfcreator']):
                    # 前後の空白行も削除
                    before_start = start
                    after_end = end
                    # 前の行が空行の場合は削除
                    if before_start > 0 and tex_content[before_start-1] == '\n':
                        j = before_start - 2
                        while j >= 0 and tex_content[j] in [' ', '\t']:
                            j -= 1
                        if j >= 0 and tex_content[j] == '\n':
                            before_start = j + 1
                    # 後の行が空行の場合は削除
                    if after_end < len(tex_content) and tex_content[after_end] == '\n':
                        after_end += 1
                    tex_content = tex_content[:before_start] + tex_content[after_end:]
                    removed_count += 1
                    break
                break
        i += 1
if removed_count > 0:
    print(f"  Removed {removed_count} \\hypersetup command(s) with pdfauthor/pdftitle")

# 展開された内容を保存
with open(tex_file, 'w', encoding='utf-8') as f:
    f.write(tex_content)

# .toc、.lof、.lotファイルも処理（?contents?を置き換える）
output_dir = os.path.dirname(tex_file) if os.path.dirname(tex_file) else '.'
for toc_file_name in ['paper.toc', 'paper.lof', 'paper.lot']:
    toc_file = os.path.join(output_dir, toc_file_name)
    if os.path.exists(toc_file):
        with open(toc_file, 'r', encoding='utf-8') as f:
            toc_content = f.read()
        toc_content = toc_content.replace('?contents?', 'Contents')
        toc_content = toc_content.replace('?listfigure?', 'List of Figures')
        toc_content = toc_content.replace('?listtable?', 'List of Tables')
        with open(toc_file, 'w', encoding='utf-8') as f:
            f.write(toc_content)

print("✓ Expanded YAML variables in template/preamble.tex")
