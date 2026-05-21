#!/usr/bin/env python3
"""
生成されたTeXファイルにtemplate/before-body.texの内容を追加するスクリプト
"""
import sys
import os

if len(sys.argv) < 2:
    print("Usage: add_before_body.py <tex_file>")
    sys.exit(1)

tex_file = sys.argv[1]

# template/before-body.texのパスを決定
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
before_body_file = os.path.join(project_root, 'template', 'before-body.tex')

# template/before-body.texの内容を読み込む
if not os.path.exists(before_body_file):
    print(f"Error: {before_body_file} not found")
    sys.exit(1)

with open(before_body_file, 'r', encoding='utf-8') as f:
    before_body_content = f.read()

# TeXファイルを読み込む
with open(tex_file, 'r', encoding='utf-8') as f:
    tex_content = f.read()

# \begin{document}の後にbefore-bodyの内容を挿入（まだ含まれていない場合）
if '\\titlepage' not in tex_content and '\\cmemberspage' not in tex_content:
    # \begin{document}の後に挿入
    tex_content = tex_content.replace(
        '\\begin{document}',
        f'\\begin{{document}}\n% NAIST修士論文用LaTeX before-body（手動追加）\n{before_body_content}'
    )
    
    # 変更を保存
    with open(tex_file, 'w', encoding='utf-8') as f:
        f.write(tex_content)
    
    print("✓ Added template/before-body.tex to TeX file")
else:
    print("✓ template/before-body.tex already included")

