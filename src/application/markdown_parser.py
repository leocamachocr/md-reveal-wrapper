import re

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt


class MarkdownParser:
    """
    Converts a Markdown string to a BeautifulSoup DOM tree.

    Also extends the fenced-code renderer to support Reveal.js line-number
    annotations in the form:  ```lang [x|y-z]

    SRP: sole responsibility is Markdown-to-HTML parsing.
    OCP: new Markdown extensions can be added without touching processors
         or the generator.
    """

    def __init__(self) -> None:
        self._md = MarkdownIt("commonmark").enable("table")
        self._patch_fence_renderer()

    def parse(self, md_content: str) -> BeautifulSoup:
        html = self._md.render(md_content)
        return BeautifulSoup(html, "html.parser")

    def _patch_fence_renderer(self) -> None:
        default_fence = self._md.renderer.rules.get("fence")

        def fence_with_line_numbers(tokens, idx, options, env):
            token = tokens[idx]
            info = token.info.strip()
            match = re.match(r"(\w+)\s*(?:\[(.+)\])?", info)
            if match:
                lang = match.group(1)
                lines = match.group(2)
                token.attrSet("class", f"language-{lang}")
                if lines:
                    token.attrSet("data-line-numbers", lines)
            return default_fence(tokens, idx, options, env)

        self._md.renderer.rules["fence"] = fence_with_line_numbers
