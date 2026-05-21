#!/usr/bin/env python3
"""
Execute NLP2 assignments and generate report
"""

import re
import requests
from bs4 import BeautifulSoup
from transformers import AutoTokenizer

# Student information
STUDENT_ID = "2411218"
STUDENT_NAME = "daisuke narita"

# text0 from the notebook
text0 = """
A large language model (LLM) is a language model trained with self-supervised machine learning on a vast amount of text, designed for natural language processing tasks, especially language generation. The largest and most capable LLMs are generative pre-trained transformers (GPTs) and provide the core capabilities of chatbots such as ChatGPT, Gemini and Claude. LLMs can be fine-tuned for specific tasks or guided by prompt engineering. These models acquire predictive power regarding syntax, semantics, and ontologies inherent in human language corpora, but they also inherit inaccuracies and biases present in the data they are trained on.
They consist of billions to trillions of parameters and operate as general-purpose sequence models, generating, summarizing, translating, and reasoning over text. LLMs represent a significant new technology in their ability to generalize across tasks with minimal task-specific supervision, enabling capabilities like conversational agents, code generation, knowledge retrieval, and automated reasoning that previously required bespoke systems.
LLMs evolved from earlier statistical and recurrent neural network approaches to language modeling. The transformer architecture, introduced in 2017, replaced recurrence with self-attention, allowing efficient parallelization, longer context handling, and scalable training on unprecedented data volumes. This innovation enabled models like GPT, BERT, and their successors, which demonstrated emergent behaviors at scale such as few-shot learning and compositional reasoning.
Reinforcement learning, particularly policy gradient algorithms, has been adapted to fine-tune LLMs for desired behaviors beyond raw next-token prediction. Reinforcement learning from human feedback (RLHF) applies these methods to optimize a policy, the LLM's output distribution, against reward signals derived from human or automated preference judgments. This has been critical for aligning model outputs with user expectations, improving factuality, reducing harmful responses, and enhancing task performance.
Benchmark evaluations for LLMs have evolved from narrow linguistic assessments toward comprehensive, multi-task evaluations measuring reasoning, factual accuracy, alignment, and safety. Hill climbing, iteratively optimizing models against benchmarks, has emerged as a dominant strategy, producing rapid incremental performance gains but raising concerns of overfitting to benchmarks rather than achieving genuine generalization or robust capability improvements.
""".strip("\n").replace("\n", " ")

def search_acl_papers_by_keywords(year, keywords):
    """キーワードでACL論文を検索してカウント"""
    # Use ACL Anthology search
    search_url = "https://aclanthology.org/search/"
    count = 0
    matched_titles = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for keyword in keywords:
        try:
            # Search for papers with keyword in title, filtered by year
            params = {
                'q': keyword,
                'venue': f'ACL {year}',
            }
            response = requests.get(search_url, params=params, headers=headers, timeout=60)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Find paper links in search results
                paper_links = soup.find_all('a', href=re.compile(r'/[PWFD]\d{2}-\d{4}'))
                for link in paper_links:
                    title = link.get_text(strip=True)
                    if title:
                        matched_titles.add(title)
            time.sleep(1)  # Be polite
        except Exception as e:
            print(f"Error searching for '{keyword}': {e}")
    
    return len(matched_titles)

def get_acl_papers(year):
    """ACL論文のタイトルを取得"""
    url = f"https://aclanthology.org/events/acl-{year}/"
    titles = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        print(f"Fetching ACL {year} papers from {url}...")
        response = requests.get(url, headers=headers, timeout=120)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Method 1: Find all links with ACL paper ID pattern (e.g., /P15-1001, /W15-1234)
        paper_links = soup.find_all('a', href=re.compile(r'/[PWFD]\d{2}-\d{4}'))
        for link in paper_links:
            title_text = link.get_text(strip=True)
            if title_text and len(title_text) > 5 and title_text not in titles:
                titles.append(title_text)
        
        # Method 2: Find span.entry-title
        for span in soup.find_all('span', class_='entry-title'):
            title_text = span.get_text(strip=True)
            if title_text and len(title_text) > 5 and title_text not in titles:
                titles.append(title_text)
        
        # Method 3: Find headings with paper links
        for heading in soup.find_all(['h2', 'h3', 'h4', 'h5']):
            link = heading.find('a', href=re.compile(r'/[PWFD]\d{2}-\d{4}'))
            if link:
                title_text = link.get_text(strip=True)
                if title_text and len(title_text) > 5 and title_text not in titles:
                    titles.append(title_text)
        
        # Method 4: Try to find papers in list items or paragraphs
        for elem in soup.find_all(['li', 'p', 'div']):
            link = elem.find('a', href=re.compile(r'/[PWFD]\d{2}-\d{4}'))
            if link:
                title_text = link.get_text(strip=True)
                if title_text and len(title_text) > 5 and title_text not in titles:
                    titles.append(title_text)
        
        # Remove duplicates while preserving order
        titles = list(dict.fromkeys(titles))
        print(f"Found {len(titles)} titles for ACL {year}")
        
    except Exception as e:
        print(f"Error fetching ACL {year} papers: {e}")
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
                # "POS" を独立した単語として検索
                # "POS " (スペースが後続) または "POS" が文末、または "POS" の後に句読点
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

# Questions 1-2: Word tokens and types
print("=" * 60)
print("Questions 1-2: Word tokens and types")
print("=" * 60)

text1 = text0.replace(",", " ,").replace(".", " .").replace("(", "( ").replace(")", " )")
text1_lower = text1.lower()
tokens = text1_lower.split()
total_tokens = len(tokens)
unique_tokens = set(tokens)
num_types = len(unique_tokens)

print(f"Question 1 - Total number of word tokens: {total_tokens}")
print(f"Question 2 - Number of word types (unique tokens): {num_types}")

q1_answer = total_tokens
q2_answer = num_types

# Questions 3-5: llm-jp-3.1-1.8b tokenizer
print("\n" + "=" * 60)
print("Questions 3-5: llm-jp-3.1-1.8b tokenizer")
print("=" * 60)

tokenizer_llmjp = AutoTokenizer.from_pretrained("llm-jp/llm-jp-3.1-1.8b")
vocab_size_llmjp = len(tokenizer_llmjp.get_vocab())
tokens_llmjp = tokenizer_llmjp.tokenize(text0)
num_tokens_llmjp = len(tokens_llmjp)
unique_tokens_llmjp = set(tokens_llmjp)
num_unique_tokens_llmjp = len(unique_tokens_llmjp)

print(f"Question 3 - Vocabulary size: {vocab_size_llmjp}")
print(f"Question 4 - Total number of tokens: {num_tokens_llmjp}")
print(f"Question 5 - Total number of unique tokens: {num_unique_tokens_llmjp}")

q3_answer = vocab_size_llmjp
q4_answer = num_tokens_llmjp
q5_answer = num_unique_tokens_llmjp

# Questions 6-8: Qwen/Qwen3-1.7B tokenizer
print("\n" + "=" * 60)
print("Questions 6-8: Qwen/Qwen3-1.7B tokenizer")
print("=" * 60)

tokenizer_qwen = AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B")
vocab_size_qwen = len(tokenizer_qwen.get_vocab())
tokens_qwen = tokenizer_qwen.tokenize(text0)
num_tokens_qwen = len(tokens_qwen)
unique_tokens_qwen = set(tokens_qwen)
num_unique_tokens_qwen = len(unique_tokens_qwen)

print(f"Question 6 - Vocabulary size: {vocab_size_qwen}")
print(f"Question 7 - Total number of tokens: {num_tokens_qwen}")
print(f"Question 8 - Total number of unique tokens: {num_unique_tokens_qwen}")

q6_answer = vocab_size_qwen
q7_answer = num_tokens_qwen
q8_answer = num_unique_tokens_qwen

# Questions 9-10: ACL papers
print("\n" + "=" * 60)
print("Questions 9-10: ACL papers")
print("=" * 60)

acl_2015_titles = get_acl_papers(2015)
acl_2025_titles = get_acl_papers(2025)

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

# 選択肢を決定
print("\n[Answers]")
# Question 9の選択肢
if count_2025_tokenization > count_2015_tokenization and ratio_2025_tokenization > ratio_2015_tokenization * 1.1:
    q9_choice = "c"
elif count_2025_tokenization > count_2015_tokenization and abs(ratio_2025_tokenization - ratio_2015_tokenization) < 0.001:
    q9_choice = "b"
else:
    q9_choice = "a"

# Question 10の選択肢
if count_2015_lexical > count_2025_lexical and ratio_2015_lexical > ratio_2025_lexical * 1.1:
    q10_choice = "a"
elif count_2025_lexical > count_2015_lexical and abs(ratio_2025_lexical - ratio_2015_lexical) < 0.001:
    q10_choice = "b"
else:
    q10_choice = "c"

print(f"Question 9 answer: {q9_choice}")
print(f"Question 10 answer: {q10_choice}")

# Write results to TXT file
output_file = "/Users/cbns03/Downloads/anicca-project/docs/naist/NLP 2025 Handouts/NLP2_report.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(f"Student ID: {STUDENT_ID}\n")
    f.write(f"Name: {STUDENT_NAME}\n")
    f.write("\n")
    f.write(f"1,{q1_answer}\n")
    f.write(f"2,{q2_answer}\n")
    f.write(f"3,{q3_answer}\n")
    f.write(f"4,{q4_answer}\n")
    f.write(f"5,{q5_answer}\n")
    f.write(f"6,{q6_answer}\n")
    f.write(f"7,{q7_answer}\n")
    f.write(f"8,{q8_answer}\n")
    f.write(f"9,{q9_choice}\n")
    f.write(f"10,{q10_choice}\n")

print(f"\n" + "=" * 60)
print(f"Results written to: {output_file}")
print("=" * 60)

