#!/usr/bin/env python3
"""
NLP2 Assignments Solution Script
Questions 1-10を解くためのスクリプト
"""

import re
from collections import Counter
from transformers import AutoTokenizer
import requests
from bs4 import BeautifulSoup

# text0の定義
text0 = """
A large language model (LLM) is a language model trained with self-supervised machine learning on a vast amount of text, designed for natural language processing tasks, especially language generation. The largest and most capable LLMs are generative pre-trained transformers (GPTs) and provide the core capabilities of chatbots such as ChatGPT, Gemini and Claude. LLMs can be fine-tuned for specific tasks or guided by prompt engineering. These models acquire predictive power regarding syntax, semantics, and ontologies inherent in human language corpora, but they also inherit inaccuracies and biases present in the data they are trained on.
They consist of billions to trillions of parameters and operate as general-purpose sequence models, generating, summarizing, translating, and reasoning over text. LLMs represent a significant new technology in their ability to generalize across tasks with minimal task-specific supervision, enabling capabilities like conversational agents, code generation, knowledge retrieval, and automated reasoning that previously required bespoke systems.
LLMs evolved from earlier statistical and recurrent neural network approaches to language modeling. The transformer architecture, introduced in 2017, replaced recurrence with self-attention, allowing efficient parallelization, longer context handling, and scalable training on unprecedented data volumes. This innovation enabled models like GPT, BERT, and their successors, which demonstrated emergent behaviors at scale such as few-shot learning and compositional reasoning.
Reinforcement learning, particularly policy gradient algorithms, has been adapted to fine-tune LLMs for desired behaviors beyond raw next-token prediction. Reinforcement learning from human feedback (RLHF) applies these methods to optimize a policy, the LLM's output distribution, against reward signals derived from human or automated preference judgments. This has been critical for aligning model outputs with user expectations, improving factuality, reducing harmful responses, and enhancing task performance.
Benchmark evaluations for LLMs have evolved from narrow linguistic assessments toward comprehensive, multi-task evaluations measuring reasoning, factual accuracy, alignment, and safety. Hill climbing, iteratively optimizing models against benchmarks, has emerged as a dominant strategy, producing rapid incremental performance gains but raising concerns of overfitting to benchmarks rather than achieving genuine generalization or robust capability improvements.
""".strip("\n").replace("\n", " ")

print("=" * 80)
print("NLP2 Assignments Solutions")
print("=" * 80)

# Question 1: Count the total number of word tokens
print("\n[Question 1]")
text1 = text0.replace(",", " ,").replace(".", " .").replace("(", "( ").replace(")", " )")
# 大文字小文字を区別しない（小文字に統一）
text1_lower = text1.lower()
# 空白で分割してトークンを取得
tokens = text1_lower.split()
total_tokens = len(tokens)
print(f"Total number of word tokens: {total_tokens}")

# Question 2: Count the number of word types (unique word tokens)
print("\n[Question 2]")
unique_tokens = set(tokens)
num_types = len(unique_tokens)
print(f"Number of word types (unique tokens): {num_types}")

# Question 3-5: llm-jp-3.1-1.8b tokenizer
print("\n[Questions 3-5]")
print("Loading llm-jp-3.1-1.8b tokenizer...")
tokenizer_jp = AutoTokenizer.from_pretrained("llm-jp/llm-jp-3.1-1.8b")

# Question 3: Vocabulary size
vocab_size_jp = len(tokenizer_jp.get_vocab())
print(f"Question 3 - Vocabulary size: {vocab_size_jp}")

# Question 4: Total number of tokens
tokens_jp = tokenizer_jp.tokenize(text0)
num_tokens_jp = len(tokens_jp)
print(f"Question 4 - Total number of tokens: {num_tokens_jp}")

# Question 5: Total number of unique tokens
unique_tokens_jp = set(tokens_jp)
num_unique_tokens_jp = len(unique_tokens_jp)
print(f"Question 5 - Total number of unique tokens: {num_unique_tokens_jp}")

# Question 6-8: Qwen/Qwen3-1.7B tokenizer
print("\n[Questions 6-8]")
print("Loading Qwen/Qwen3-1.7B tokenizer...")
tokenizer_qwen = AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B")

# Question 6: Vocabulary size
vocab_size_qwen = len(tokenizer_qwen.get_vocab())
print(f"Question 6 - Vocabulary size: {vocab_size_qwen}")

# Question 7: Total number of tokens
tokens_qwen = tokenizer_qwen.tokenize(text0)
num_tokens_qwen = len(tokens_qwen)
print(f"Question 7 - Total number of tokens: {num_tokens_qwen}")

# Question 8: Total number of unique tokens
unique_tokens_qwen = set(tokens_qwen)
num_unique_tokens_qwen = len(unique_tokens_qwen)
print(f"Question 8 - Total number of unique tokens: {num_unique_tokens_qwen}")

# Question 9-10: ACL papers analysis
print("\n[Questions 9-10]")
print("Analyzing ACL 2015 and 2025 papers...")

def get_acl_papers(year):
    """ACL論文のタイトルを取得"""
    url = f"https://aclanthology.org/events/acl-{year}/"
    titles = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # ACL Anthologyのページ構造に基づいてタイトルを取得
        # 論文タイトルは通常、リンクや特定のクラスに含まれている
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            # ACL論文のIDパターンにマッチするリンクを探す
            if '/P' in href or '/W' in href or '/F' in href or '/D' in href:
                title_text = link.get_text(strip=True)
                if title_text and len(title_text) > 5:
                    titles.append(title_text)
        
        # 重複を除去
        titles = list(dict.fromkeys(titles))  # 順序を保ちながら重複除去
        
        # より確実な方法: span.entry-title や h4 などのタイトル要素を探す
        if len(titles) < 50:  # 十分なタイトルが取得できていない場合
            for elem in soup.find_all(['span', 'h4', 'h3', 'p'], class_=lambda x: x and ('title' in x.lower() or 'entry' in x.lower())):
                text = elem.get_text(strip=True)
                if text and len(text) > 10 and len(text) < 500:
                    titles.append(text)
        
        # 再度重複除去
        titles = list(dict.fromkeys(titles))
        
    except Exception as e:
        print(f"Error fetching ACL {year} papers: {e}")
        import traceback
        traceback.print_exc()
    
    return titles

def count_papers_with_keywords(titles, keywords):
    """キーワードを含む論文数をカウント（重複カウントを避ける）"""
    matched_titles = set()
    
    for title in titles:
        title_lower = title.lower()
        for keyword in keywords:
            matched = False
            
            if keyword.lower() == "pos":
                # "POS" を単語として検索（"XPOS"や"Decompositional"を除外）
                # "POS " (スペース後) または "POS." または "POS," など
                pattern = r'\bpos\s+[^a-z]|\bpos\b[^a-z]|\bpos$'
                if re.search(pattern, title_lower, re.IGNORECASE):
                    matched = True
            elif keyword.lower() == "pos tagging":
                if "pos tagging" in title_lower:
                    matched = True
            else:
                # その他のキーワードは通常の部分文字列マッチ
                if keyword.lower() in title_lower:
                    matched = True
            
            if matched:
                matched_titles.add(title)
                break  # 1つのキーワードにマッチしたら次のタイトルへ
    
    return len(matched_titles)

# ACL 2015と2025の論文を取得
print("Fetching ACL 2015 papers...")
acl_2015_titles = get_acl_papers(2015)
print(f"Found {len(acl_2015_titles)} papers for ACL 2015")

print("Fetching ACL 2025 papers...")
acl_2025_titles = get_acl_papers(2025)
print(f"Found {len(acl_2025_titles)} papers for ACL 2025")

# 実際の論文数（問題文より）
total_2015 = 363
total_2025 = 4547  # 訂正後の値

# Question 9: tokenization papers
print("\n[Question 9]")
keywords_tokenization = ["tokenization", "tokenisation"]
count_2015_tokenization = count_papers_with_keywords(acl_2015_titles, keywords_tokenization)
count_2025_tokenization = count_papers_with_keywords(acl_2025_titles, keywords_tokenization)

ratio_2015_tokenization = count_2015_tokenization / total_2015 if total_2015 > 0 else 0
ratio_2025_tokenization = count_2025_tokenization / total_2025 if total_2025 > 0 else 0

print(f"ACL 2015 papers with 'tokenization' or 'tokenisation': {count_2015_tokenization}")
print(f"ACL 2015 ratio: {ratio_2015_tokenization:.4f} ({count_2015_tokenization}/{total_2015})")
print(f"ACL 2025 papers with 'tokenization' or 'tokenisation': {count_2025_tokenization}")
print(f"ACL 2025 ratio: {ratio_2025_tokenization:.4f} ({count_2025_tokenization}/{total_2025})")

# Question 10: lexical analysis papers
print("\n[Question 10]")
keywords_lexical = ["morpheme", "morphology", "morphological", "word segmentation", "POS", "POS tagging"]
count_2015_lexical = count_papers_with_keywords(acl_2015_titles, keywords_lexical)
count_2025_lexical = count_papers_with_keywords(acl_2025_titles, keywords_lexical)

ratio_2015_lexical = count_2015_lexical / total_2015 if total_2015 > 0 else 0
ratio_2025_lexical = count_2025_lexical / total_2025 if total_2025 > 0 else 0

print(f"ACL 2015 papers with lexical analysis keywords: {count_2015_lexical}")
print(f"ACL 2015 ratio: {ratio_2015_lexical:.4f} ({count_2015_lexical}/{total_2015})")
print(f"ACL 2025 papers with lexical analysis keywords: {count_2025_lexical}")
print(f"ACL 2025 ratio: {ratio_2025_lexical:.4f} ({count_2025_lexical}/{total_2025})")

print("\n" + "=" * 80)
print("Summary of Answers:")
print("=" * 80)
print(f"1. Total word tokens: {total_tokens}")
print(f"2. Number of word types: {num_types}")
print(f"3. llm-jp vocabulary size: {vocab_size_jp}")
print(f"4. llm-jp total tokens: {num_tokens_jp}")
print(f"5. llm-jp unique tokens: {num_unique_tokens_jp}")
print(f"6. Qwen vocabulary size: {vocab_size_qwen}")
print(f"7. Qwen total tokens: {num_tokens_qwen}")
print(f"8. Qwen unique tokens: {num_unique_tokens_qwen}")
print(f"9. ACL 2015 tokenization: {count_2015_tokenization} ({ratio_2015_tokenization:.4f}), ACL 2025: {count_2025_tokenization} ({ratio_2025_tokenization:.4f})")
print(f"10. ACL 2015 lexical: {count_2015_lexical} ({ratio_2015_lexical:.4f}), ACL 2025: {count_2025_lexical} ({ratio_2025_lexical:.4f})")

