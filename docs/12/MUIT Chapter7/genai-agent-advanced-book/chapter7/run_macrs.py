#!/usr/bin/env python3
"""
MACRS実行スクリプト
事前に定義した入力内容を使用してMACRSを実行し、結果を保存します。
"""
import asyncio
import sys
import json
import io
from datetime import datetime
from macrs.agent import MACRS, UserInputAgent
from macrs.custom_logger import setup_logger

logger = setup_logger(__name__)

# 実行時の入力内容（最低4回以上）
USER_INPUTS = [
    "こんにちは、AIエージェントについて学びたいと思っています。",
    "ビジネス活用事例が知りたいです。",
    "ありがとうございます。講座についての情報がありますか。",
    "具体的には、どのようなスキルが身につきますか？",
    "exit"  # 終了
]


class MockUserInputAgent(UserInputAgent):
    """UserInputAgentをモックして、事前定義した入力を使用"""
    def __init__(self, inputs):
        self.inputs = inputs
        self.index = 0
        super().__init__()
    
    async def run(self, state: dict, prompt="あなた: ") -> dict:
        if self.index < len(self.inputs):
            user_input = self.inputs[self.index]
            self.index += 1
            print(f"{prompt}{user_input}")
            logger.info("ユーザー : %s", user_input)
            
            if user_input.lower() == "exit":
                print("対話を終了します。ありがとうございました！")
                state["exit"] = True
                return state
            else:
                state["conversation_history"] += f"\nユーザー: {user_input}"
                state["user_input"] = user_input
                state["exit"] = False
        else:
            state["exit"] = True
        return state


async def run_macrs_with_inputs():
    """事前定義した入力でMACRSを実行"""
    macrs = MACRS()
    
    # UserInputAgentをモック版に置き換え
    macrs.user_input_agent = MockUserInputAgent(USER_INPUTS)
    
    # グラフを再作成（新しいエージェントを使用）
    app = macrs.create_graph()
    
    state = {
        "user_input": "",
        "conversation_history": "",
        "exit": False,
        "selected_agent": "",
    }
    print(
        "タスク管理エージェントへようこそ！操作を開始してください（終了するには 'exit' と入力してください）。"
    )
    # 初回実行
    result = await app.ainvoke(state)
    # exitフラグがセットされていれば処理を中断
    if result.get("exit"):
        return result
    state.update(result)
    # 対話のループ
    while not state.get("exit"):
        result = await app.ainvoke(state)
        if result.get("exit"):
            state.update(result)  # exitがTrueの場合も状態を更新
            break
        state.update(result)
    
    # 最終的な状態を返す
    return state


def parse_conversation_history(history: str):
    """会話履歴を解析して、各対話の詳細を抽出"""
    dialogues = []
    lines = history.strip().split("\n")
    
    current_dialogue = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith("ユーザー:"):
            if current_dialogue:
                dialogues.append(current_dialogue)
            current_dialogue = {
                "user_input": line.replace("ユーザー:", "").strip(),
                "selected_agent": None,
                "agent_response": None,
                "agent_type": None
            }
        elif line.startswith("選択されたエージェント:"):
            if current_dialogue:
                current_dialogue["selected_agent"] = line.replace("選択されたエージェント:", "").strip()
        elif line.startswith("AIエージェント (質問):"):
            if current_dialogue:
                current_dialogue["agent_response"] = line.replace("AIエージェント (質問):", "").strip()
                current_dialogue["agent_type"] = "QuestionAgent"
        elif line.startswith("AIエージェント (レコメンド):"):
            if current_dialogue:
                current_dialogue["agent_response"] = line.replace("AIエージェント (レコメンド):", "").strip()
                current_dialogue["agent_type"] = "RecommendationAgent"
        elif line.startswith("AIエージェント (雑談):"):
            if current_dialogue:
                current_dialogue["agent_response"] = line.replace("AIエージェント (雑談):", "").strip()
                current_dialogue["agent_type"] = "ChitChatAgent"
        elif line.startswith("質問:"):
            if current_dialogue:
                current_dialogue["agent_response"] = line.replace("質問:", "").strip()
                current_dialogue["agent_type"] = "QuestionAgent"
        elif line.startswith("レコメンド:"):
            if current_dialogue:
                current_dialogue["agent_response"] = line.replace("レコメンド:", "").strip()
                current_dialogue["agent_type"] = "RecommendationAgent"
        elif line.startswith("おしゃべり:"):
            if current_dialogue:
                current_dialogue["agent_response"] = line.replace("おしゃべり:", "").strip()
                current_dialogue["agent_type"] = "ChitChatAgent"
    
    if current_dialogue:
        dialogues.append(current_dialogue)
    
    return dialogues


def main():
    """メイン実行関数"""
    print("=" * 80)
    print("MACRS実行開始")
    print("=" * 80)
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"入力内容: {len(USER_INPUTS) - 1}回の対話を予定")
    print("=" * 80)
    print()
    
    # MACRSを実行
    result = asyncio.run(run_macrs_with_inputs())
    
    # 会話履歴を解析
    conversation_history = result.get("conversation_history", "")
    dialogues = parse_conversation_history(conversation_history)
    
    # 結果を保存
    output_dir = "/Users/cbns03/Downloads/anicca-project/docs/12/Chapter7/genai-agent-advanced-book/chapter7"
    
    # テキスト形式で保存
    txt_file = f"{output_dir}/macrs_result.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("MACRS実行結果\n")
        f.write("=" * 80 + "\n")
        f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n")
        f.write("入力内容:\n")
        f.write("-" * 80 + "\n")
        for i, inp in enumerate(USER_INPUTS[:-1], 1):  # exitを除く
            f.write(f"{i}. {inp}\n")
        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("実行結果（会話履歴）:\n")
        f.write("=" * 80 + "\n")
        f.write(conversation_history)
        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("対話の詳細:\n")
        f.write("=" * 80 + "\n")
        for i, dialogue in enumerate(dialogues, 1):
            f.write(f"\n対話{i}回目:\n")
            f.write(f"  ユーザー: {dialogue.get('user_input', 'N/A')}\n")
            f.write(f"  選択されたエージェント: {dialogue.get('agent_type', 'N/A')}\n")
            f.write(f"  AIエージェント応答: {dialogue.get('agent_response', 'N/A')}\n")
        f.write("\n")
        f.write("=" * 80 + "\n")
        f.write("最終状態:\n")
        f.write("-" * 80 + "\n")
        f.write(f"選択されたエージェント: {result.get('selected_agent', 'N/A')}\n")
        f.write(f"推奨内容: {result.get('recommendation', 'N/A')}\n")
    
    # JSON形式でも保存
    json_file = f"{output_dir}/macrs_result.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({
            "execution_time": datetime.now().isoformat(),
            "user_inputs": USER_INPUTS[:-1],  # exitを除く
            "conversation_history": conversation_history,
            "dialogues": dialogues,
            "final_state": {
                "selected_agent": result.get("selected_agent", ""),
                "recommendation": result.get("recommendation", ""),
            }
        }, f, ensure_ascii=False, indent=2)
    
    print()
    print("=" * 80)
    print("実行完了")
    print("=" * 80)
    print(f"結果を保存しました:")
    print(f"  - {txt_file}")
    print(f"  - {json_file}")
    print()
    print("対話の詳細:")
    print("-" * 80)
    for i, dialogue in enumerate(dialogues, 1):
        print(f"\n対話{i}回目:")
        print(f"  ユーザー: {dialogue.get('user_input', 'N/A')}")
        print(f"  選択されたエージェント: {dialogue.get('agent_type', 'N/A')}")
        print(f"  AIエージェント応答: {dialogue.get('agent_response', 'N/A')[:100]}...")


if __name__ == "__main__":
    main()

