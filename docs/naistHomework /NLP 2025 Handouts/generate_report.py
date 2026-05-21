#!/usr/bin/env python3
"""
NLP2 Assignments Report Generator
レポートフォーマットに従って回答を生成
"""

import re
from collections import Counter
from transformers import AutoTokenizer
import requests
from bs4 import BeautifulSoup
import json

# text0の定義
text0 = """
A large language model (LLM) is a language model trained with self-supervised machine learning on a vast amount of text, designed for natural language processing tasks, especially language generation. The largest and most capable LLMs are generative pre-trained transformers (GPTs) and provide the core capabilities of chatbots such as ChatGPT, Gemini and Claude. LLMs can be fine-tuned for specific tasks or guided by prompt engineering. These models acquire predictive power regarding syntax, semantics, and ontologies inherent in human language corpora, but they also inherit inaccuracies and biases present in the data they are trained on.
They consist of billions to trillions of parameters and operate as general-purpose sequence models, generating, summarizing, translating, and reasoning over text. LLMs represent a significant new technology in their ability to generalize across tasks with minimal task-specific supervision, enabling capabilities like conversational agents, code generation, knowledge retrieval, and automated reasoning that previously required bespoke systems.
LLMs evolved from earlier statistical and recurrent neural network approaches to language modeling. The transformer architecture, introduced in 2017, replaced recurrence with self-attention, allowing efficient parallelization, longer context handling, and scalable training on unprecedented data volumes. This innovation enabled models like GPT, BERT, and their successors, which demonstrated emergent behaviors at scale such as few-shot learning and compositional reasoning.
Reinforcement learning, particularly policy gradient algorithms, has been adapted to fine-tune LLMs for desired behaviors beyond raw next-token prediction. Reinforcement learning from human feedback (RLHF) applies these methods to optimize a policy, the LLM's output distribution, against reward signals derived from human or automated preference judgments. This has been critical for aligning model outputs with user expectations, improving factuality, reducing harmful responses, and enhancing task performance.
Benchmark evaluations for LLMs have evolved from narrow linguistic assessments toward comprehensive, multi-task evaluations measuring reasoning, factual accuracy, alignment, and safety. Hill climbing, iteratively optimizing models against benchmarks, has emerged as a dominant strategy, producing rapid incremental performance gains but raising concerns of overfitting to benchmarks rather than achieving genuine generalization or robust capability improvements.
""".strip("\n").replace("\n", " ")

def solve_questions_1_2():
    """質問1-2を解く"""
    text1 = text0.replace(",", " ,").replace(".", " .").replace("(", "( ").replace(")", " )")
    text1_lower = text1.lower()
    tokens = text1_lower.split()
    
    q1_answer = len(tokens)
    q2_answer = len(set(tokens))
    
    return q1_answer, q2_answer

def solve_questions_3_5():
    """質問3-5を解く（llm-jp-3.1-1.8b）"""
    tokenizer = AutoTokenizer.from_pretrained("llm-jp/llm-jp-3.1-1.8b")
    
    vocab_size = len(tokenizer.get_vocab())
    tokens = tokenizer.tokenize(text0)
    num_tokens = len(tokens)
    num_unique_tokens = len(set(tokens))
    
    return vocab_size, num_tokens, num_unique_tokens

def solve_questions_6_8():
    """質問6-8を解く（Qwen/Qwen3-1.7B）"""
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B")
    
    vocab_size = len(tokenizer.get_vocab())
    tokens = tokenizer.tokenize(text0)
    num_tokens = len(tokens)
    num_unique_tokens = len(set(tokens))
    
    return vocab_size, num_tokens, num_unique_tokens

def get_acl_papers(year):
    """ACL論文のタイトルを取得"""
    url = f"https://aclanthology.org/events/acl-{year}/"
    titles = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 方法1: span.entry-title を探す（ACL Anthologyの標準的な構造）
        for span in soup.find_all('span', class_='entry-title'):
            title_text = span.get_text(strip=True)
            if title_text and len(title_text) > 5:
                titles.append(title_text)
        
        # 方法2: リンクからタイトルを取得（ACL論文IDパターンにマッチ）
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            # ACL論文IDパターン: /P15-1001/, /W15-1001/, /F15-1001/, /D15-1001/ など
            if re.search(r'/[PWFD]\d{2}-\d{4}', href):
                title_text = link.get_text(strip=True)
                if title_text and len(title_text) > 5 and title_text not in titles:
                    titles.append(title_text)
        
        # 方法3: h4やh3タグからタイトルを取得
        for heading in soup.find_all(['h4', 'h3', 'h2']):
            title_text = heading.get_text(strip=True)
            if title_text and len(title_text) > 10 and len(title_text) < 500:
                # リンク内のテキストを優先（重複を避ける）
                link = heading.find('a')
                if link:
                    title_text = link.get_text(strip=True)
                if title_text and title_text not in titles:
                    titles.append(title_text)
        
        # 重複を除去（順序を保持）
        titles = list(dict.fromkeys(titles))
        
        print(f"  Found {len(titles)} unique titles for ACL {year}")
        
    except Exception as e:
        print(f"Warning: Error fetching ACL {year} papers: {e}")
        import traceback
        traceback.print_exc()
    
    return titles

def count_papers_with_keywords(titles, keywords):
    """キーワードを含む論文数をカウント"""
    matched_titles = set()
    
    for title in titles:
        title_lower = title.lower()
        for keyword in keywords:
            matched = False
            
            if keyword.lower() == "pos":
                # "POS" を独立した単語として検索（"POS "のようにスペースが後続、または文末）
                # "XPOS"や"Decompositional"を除外するため、単語境界を使用
                # "POS " (スペース後)、"POS." (ピリオド後)、"POS," (カンマ後)、"POS)" (閉じ括弧後)、"POS" (文末)
                pattern = r'\bpos\s+|\bpos[.,;:)!?\]\}\-]|\bpos$'
                if re.search(pattern, title_lower, re.IGNORECASE):
                    matched = True
            elif keyword.lower() == "pos tagging":
                if "pos tagging" in title_lower:
                    matched = True
            else:
                if keyword.lower() in title_lower:
                    matched = True
            
            if matched:
                matched_titles.add(title)
                break
    
    return len(matched_titles)

def solve_questions_9_10():
    """質問9-10を解く"""
    # 実際の論文数（問題文より）
    total_2015 = 363
    total_2025 = 4547  # 訂正後の値
    
    # ACL論文を取得（時間がかかる可能性があるため、キャッシュを検討）
    print("Fetching ACL 2015 papers...")
    acl_2015_titles = get_acl_papers(2015)
    print(f"Found {len(acl_2015_titles)} titles for ACL 2015")
    
    print("Fetching ACL 2025 papers...")
    acl_2025_titles = get_acl_papers(2025)
    print(f"Found {len(acl_2025_titles)} titles for ACL 2025")
    
    # Question 9: tokenization
    keywords_tokenization = ["tokenization", "tokenisation"]
    count_2015_tokenization = count_papers_with_keywords(acl_2015_titles, keywords_tokenization)
    count_2025_tokenization = count_papers_with_keywords(acl_2025_titles, keywords_tokenization)
    
    ratio_2015_tokenization = count_2015_tokenization / total_2015 if total_2015 > 0 else 0
    ratio_2025_tokenization = count_2025_tokenization / total_2025 if total_2025 > 0 else 0
    
    # Question 10: lexical analysis
    keywords_lexical = ["morpheme", "morphology", "morphological", "word segmentation", "POS", "POS tagging"]
    count_2015_lexical = count_papers_with_keywords(acl_2015_titles, keywords_lexical)
    count_2025_lexical = count_papers_with_keywords(acl_2025_titles, keywords_lexical)
    
    ratio_2015_lexical = count_2015_lexical / total_2015 if total_2015 > 0 else 0
    ratio_2025_lexical = count_2025_lexical / total_2025 if total_2025 > 0 else 0
    
    # Question 9の選択肢を決定
    if count_2025_tokenization > count_2015_tokenization and ratio_2025_tokenization > ratio_2015_tokenization * 1.1:
        q9_choice = "c"
    elif count_2025_tokenization > count_2015_tokenization and abs(ratio_2025_tokenization - ratio_2015_tokenization) < 0.001:
        q9_choice = "b"
    else:
        q9_choice = "a"
    
    # Question 10の選択肢を決定
    if count_2015_lexical > count_2025_lexical and ratio_2015_lexical > ratio_2025_lexical * 1.1:
        q10_choice = "a"
    elif count_2025_lexical > count_2015_lexical and abs(ratio_2025_lexical - ratio_2015_lexical) < 0.001:
        q10_choice = "b"
    else:
        q10_choice = "c"
    
    return {
        'q9': {
            'count_2015': count_2015_tokenization,
            'count_2025': count_2025_tokenization,
            'ratio_2015': ratio_2015_tokenization,
            'ratio_2025': ratio_2025_tokenization,
            'choice': q9_choice
        },
        'q10': {
            'count_2015': count_2015_lexical,
            'count_2025': count_2025_lexical,
            'ratio_2015': ratio_2015_lexical,
            'ratio_2025': ratio_2025_lexical,
            'choice': q10_choice
        }
    }

def main():
    """メイン処理"""
    print("Solving Questions 1-2...")
    q1_answer, q2_answer = solve_questions_1_2()
    
    print("Solving Questions 3-5...")
    q3_answer, q4_answer, q5_answer = solve_questions_3_5()
    
    print("Solving Questions 6-8...")
    q6_answer, q7_answer, q8_answer = solve_questions_6_8()
    
    print("Solving Questions 9-10...")
    q9_10_answers = solve_questions_9_10()
    
    # レポートフォーマットに従って出力
    report_path = "/Users/cbns03/Downloads/anicca-project/docs/naist/NLP 2025 Handouts/NLP2_report_format.txt"
    
    answers = [
        str(q1_answer),
        str(q2_answer),
        str(q3_answer),
        str(q4_answer),
        str(q5_answer),
        str(q6_answer),
        str(q7_answer),
        str(q8_answer),
        q9_10_answers['q9']['choice'],
        q9_10_answers['q10']['choice']
    ]
    
    # レポートファイルに書き込み
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("Student ID: 2411218\n")
        f.write("Name: daisuke narita\n")
        f.write("\n")
        for i, answer in enumerate(answers, 1):
            f.write(f"{i},{answer}\n")
    
    print("\n" + "=" * 80)
    print("Answers Summary:")
    print("=" * 80)
    for i, answer in enumerate(answers, 1):
        print(f"{i}. {answer}")
    
    print("\nDetailed Results for Questions 9-10:")
    print(f"Question 9: ACL 2015={q9_10_answers['q9']['count_2015']} ({q9_10_answers['q9']['ratio_2015']:.4f}), "
          f"ACL 2025={q9_10_answers['q9']['count_2025']} ({q9_10_answers['q9']['ratio_2025']:.4f}), "
          f"Choice: {q9_10_answers['q9']['choice']}")
    print(f"Question 10: ACL 2015={q9_10_answers['q10']['count_2015']} ({q9_10_answers['q10']['ratio_2015']:.4f}), "
          f"ACL 2025={q9_10_answers['q10']['count_2025']} ({q9_10_answers['q10']['ratio_2025']:.4f}), "
          f"Choice: {q9_10_answers['q10']['choice']}")
    
    print(f"\nReport saved to: {report_path}")

if __name__ == "__main__":
    main()

