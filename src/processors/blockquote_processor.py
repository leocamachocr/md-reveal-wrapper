import re

from bs4 import BeautifulSoup

from src.processors.base import SlideProcessor


class BlockquoteProcessor(SlideProcessor):
    """
    Transforms blockquotes that start with [info], [warning], or [tip]
    into styled callout boxes by:
      - adding a CSS class matching the tag type
      - replacing the blockquote contents with just the message text
    SRP: sole responsibility is blockquote-to-callout transformation.
    OCP: new callout types can be added by changing only the regex pattern.
    """

    _PATTERN = re.compile(r"\[(info|warning|tip)\]\s*(.*)", re.IGNORECASE | re.DOTALL)

    def process(self, soup: BeautifulSoup, context: dict) -> None:
        for blockquote in soup.find_all("blockquote"):
            text = blockquote.get_text(strip=True)
            match = self._PATTERN.match(text)
            if not match:
                continue

            callout_type = match.group(1).lower()
            message = match.group(2)

            blockquote["class"] = blockquote.get("class", []) + [callout_type]
            blockquote.clear()
            new_p = soup.new_tag("p")
            new_p.string = message
            blockquote.append(new_p)
