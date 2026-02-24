from bs4 import BeautifulSoup

from src.processors.base import SlideProcessor


class FragmentProcessor(SlideProcessor):
    """
    Adds the Reveal.js 'fragment' class to every list item so that items
    appear one at a time during the presentation.
    SRP: sole responsibility is fragment animation class injection.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    def process(self, soup: BeautifulSoup, context: dict) -> None:
        if not self._enabled:
            return
        for li in soup.find_all("li"):
            existing = li.get("class", [])
            if "fragment" not in existing:
                li["class"] = existing + ["fragment"]
