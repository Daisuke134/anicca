#!/usr/bin/env bash
# arXiv API search — phrase search with proper encoding
# Usage: search_arxiv.sh "mind wandering" [count] [field]
# field: ti (title), abs (abstract), all (default)
set -euo pipefail

QUERY="$1"
COUNT="${2:-5}"
FIELD="${3:-ti}"

# URL-encode the query (spaces → +, wrap in quotes for phrase match)
ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('\"$QUERY\"'))")

curl -sL "https://export.arxiv.org/api/query?search_query=${FIELD}:${ENCODED}&start=0&max_results=${COUNT}&sortBy=submittedDate&sortOrder=descending"
