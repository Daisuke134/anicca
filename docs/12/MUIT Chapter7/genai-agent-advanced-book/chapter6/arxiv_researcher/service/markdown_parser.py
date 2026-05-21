import re
from typing import List

from arxiv_researcher.models.markdown import Section


class MarkdownParser:
    """
    Markdownテキストの構造解析を担当
    セクションの抽出とフォーマット変換を提供
    """

    def parse_sections(self, text: str) -> List[Section]:
        """
        Markdownテキストからセクションを抽出する

        Args:
            text: Markdownテキスト

        Returns:
            List[Section]: 抽出されたセクションのリスト
        """
        sections = []
        lines = text.split("\n")
        current_header = None
        section_content = []

        for line in lines:
            if not line.strip():
                continue

            header_match = re.match(r"^(#+)\s+(.+)$", line.strip())

            if header_match:
                # 前のセクションがある場合は保存
                if current_header:
                    section_text = "\n".join(section_content)
                    sections.append(
                        Section(
                            header=current_header,
                            content=section_text,
                            char_count=len(section_text),
                        )
                    )
                    section_content = []

                current_header = header_match.group(2)
            else:
                if current_header:
                    section_content.append(line)

        # 最後のセクションを追加
        if current_header:
            section_text = "\n".join(section_content)
            sections.append(
                Section(
                    header=current_header,
                    content=section_text,
                    char_count=len(section_text),
                )
            )

        return sections

    def format_as_xml(self, sections: List[Section]) -> str:
        """
        セクションをXML形式にフォーマットする

        Args:
            sections: セクションのリスト

        Returns:
            str: XML形式の文字列
        """
        output = []
        output.append("<items>")
        for i, section in enumerate(sections, 1):
            first_line = section.content.split("\n")[0].strip()[:200]
            output.append("  <item>")
            output.append(f"    <index>{i}</index>")
            output.append(f"    <header>{section.header}</header>")
            output.append(f"    <first_line>{first_line}</first_line>")
            output.append(f"    <char_count>{section.char_count}</char_count>")
            output.append("  </item>")
        output.append("</items>")
        return "\n".join(output)

    def get_sections_overview(self, text: str) -> str:
        """
        Markdownテキストからセクションの概要をXML形式で取得する

        Args:
            text: Markdownテキスト

        Returns:
            str: セクション概要のXML形式文字列
        """
        sections = self.parse_sections(text)
        return self.format_as_xml(sections)

    def get_selected_sections(self, text: str, section_indices: list[int]) -> str:
        """
        指定されたインデックスのセクションを取得し、XML形式で返す

        Args:
            text: Markdownテキスト
            section_indices: 取得するセクションのインデックスリスト（1-indexed）

        Returns:
            str: 選択されたセクションのXML形式文字列
        """
        sections = self.parse_sections(text)
        selected_sections = []
        for section_index in section_indices:
            if 1 <= section_index <= len(sections):
                section = sections[section_index - 1]
                header_and_content = f"<section>\n<header>{section.header}</header>\n<content>{section.content}</content>\n</section>"
                selected_sections.append(header_and_content)
        return "\n".join(selected_sections)
