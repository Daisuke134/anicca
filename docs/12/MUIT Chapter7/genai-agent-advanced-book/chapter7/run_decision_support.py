#!/usr/bin/env python
"""意思決定支援エージェントの実行スクリプト"""
import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv(Path(__file__).parent / ".env")

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from decision_support_agent.agent import DecisionSupportAgent

def main():
    print("=" * 80)
    print("意思決定支援エージェントを実行します")
    print("=" * 80)
    
    # エージェントのインスタンス化
    agent = DecisionSupportAgent()
    
    # ユーザーリクエストの定義
    user_request = (
        "生成AIエージェントを活用して業務効率化を目指すビジネスパーソンに"
        "興味をもってもらえるようにコンテンツのテーマを改善して"
    )
    
    print(f"\nユーザーリクエスト: {user_request}\n")
    print("エージェントを実行中...\n")
    
    # エージェントの実行
    result = agent.run_agent(user_request)
    
    print("\n" + "=" * 80)
    print("実行結果")
    print("=" * 80)
    
    # 結果の表示
    print("\n【生成されたペルソナ】")
    for i, persona in enumerate(result.get("personas", []), 1):
        print(f"\nペルソナ {i}:")
        print(persona)
    
    print("\n【評価結果】")
    for i, evaluation in enumerate(result.get("evaluations", []), 1):
        print(f"\n評価 {i}:")
        print(f"ペルソナ: {evaluation.get('persona', 'N/A')}")
        print(f"フィードバック: {evaluation.get('feedback', 'N/A')}")
    
    print("\n【分析レポート】")
    print(result.get("report", "N/A"))
    
    print("\n【改善後のコンテンツ】")
    improved_contents = result.get("improved_contents")
    if improved_contents:
        print(improved_contents)
    else:
        print("改善後のコンテンツは生成されませんでした。")
    
    # 結果をJSONファイルに保存
    output_file = Path(__file__).parent / "decision_support_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n結果を {output_file} に保存しました。")
    
    # テキスト形式でも保存（スライド用）
    text_output_file = Path(__file__).parent / "decision_support_result.txt"
    with open(text_output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("意思決定支援エージェント 実行結果\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("【生成されたペルソナ】\n")
        for i, persona in enumerate(result.get("personas", []), 1):
            f.write(f"\nペルソナ {i}:\n")
            f.write(f"{persona}\n")
            f.write("-" * 80 + "\n")
        
        f.write("\n【評価結果】\n")
        for i, evaluation in enumerate(result.get("evaluations", []), 1):
            f.write(f"\n評価 {i}:\n")
            f.write(f"ペルソナ: {evaluation.get('persona', 'N/A')}\n")
            f.write(f"フィードバック:\n{evaluation.get('feedback', 'N/A')}\n")
            f.write("-" * 80 + "\n")
        
        f.write("\n【分析レポート】\n")
        f.write(result.get("report", "N/A"))
        f.write("\n\n")
        
        f.write("【改善後のコンテンツ】\n")
        improved_contents = result.get("improved_contents")
        if improved_contents:
            f.write(str(improved_contents))
        else:
            f.write("改善後のコンテンツは生成されませんでした。")
    print(f"テキスト形式の結果を {text_output_file} に保存しました。")

if __name__ == "__main__":
    main()

