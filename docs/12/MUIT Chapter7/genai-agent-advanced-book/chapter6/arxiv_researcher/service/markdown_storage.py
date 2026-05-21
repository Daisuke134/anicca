import os
from pathlib import Path


class MarkdownStorage:
    """
    Markdownファイルの永続化を担当する
    シンプルなread/writeのみを提供
    """

    def __init__(self, base_dir: str = "storage/markdown"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def write(self, filename: str, content: str) -> str:
        """
        ファイルを保存し、相対パスを返す

        Args:
            filename: 保存するファイル名
            content: 保存する内容

        Returns:
            str: 保存したファイルへの相対パス
        """
        filepath = os.path.join(self.base_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return os.path.join(self.base_dir, filename)

    def read(self, path: str) -> str:
        """
        パスからファイルを読み込む

        Args:
            path: ファイルへの相対パス

        Returns:
            str: ファイルの内容
        """
        filepath = Path(path)
        if not filepath.is_absolute():
            filepath = Path(os.getcwd()) / filepath

        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
