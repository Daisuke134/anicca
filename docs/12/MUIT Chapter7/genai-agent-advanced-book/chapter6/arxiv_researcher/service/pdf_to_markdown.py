import os
from typing import Optional
from urllib.parse import quote

import requests

from arxiv_researcher.service.markdown_storage import MarkdownStorage
from arxiv_researcher.settings import settings


class JinaApiClient:
    def __init__(self):
        self.headers = {"Authorization": f"Bearer {settings.JINA_API_KEY}"}
        self.base_url = "https://r.jina.ai"

    def convert_pdf_to_markdown(self, pdf_url: str) -> str:
        encoded_url = quote(pdf_url, safe="")
        jina_url = f"{self.base_url}/{encoded_url}"

        response = requests.get(jina_url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"JINA API error: {response.status_code} - {response.text}")

        return response.text


class PdfToMarkdown:
    def __init__(self, pdf_path_or_url: str):
        self.pdf_path_or_url = pdf_path_or_url
        self.jina_client = JinaApiClient()
        self.storage = MarkdownStorage()

    def convert(self, file_name: Optional[str] = None) -> str:
        _file_name = file_name if file_name else self.pdf_path_or_url.split("/")[-1]
        _file_name = f"{_file_name}.md"

        # 既存のmarkdownファイルがあれば、それを読み込んで返す
        try:
            return self.storage.read(_file_name)
        except FileNotFoundError:
            # 新規変換の場合、JINA Reader APIを使用
            markdown = self.jina_client.convert_pdf_to_markdown(self.pdf_path_or_url)
            # markdownを保存
            self.storage.write(_file_name, markdown)
            return markdown
