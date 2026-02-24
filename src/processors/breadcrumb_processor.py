from bs4 import BeautifulSoup

from src.processors.base import SlideProcessor


class BreadcrumbProcessor(SlideProcessor):
    """
    Tracks heading hierarchy across slides and writes a breadcrumb trail
    (e.g. "Chapter 1 › Section A") into the shared context dict under the
    key 'breadcrumb_text'.

    State is intentionally held per-instance so a fresh instance gives a
    clean run, while the same instance accumulates context across slides.

    SRP: sole responsibility is breadcrumb context tracking.
    """

    def __init__(self) -> None:
        self._header_context: dict[int, str] = {}

    def process(self, soup: BeautifulSoup, context: dict) -> None:
        first_heading = soup.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        if first_heading:
            level = int(first_heading.name[1])
            self._header_context[level] = first_heading.get_text()
            # Remove all deeper headings — they belong to the previous subtree
            for k in list(self._header_context.keys()):
                if k > level:
                    del self._header_context[k]

        context["breadcrumb_text"] = (
            " › ".join(
                self._header_context[i]
                for i in sorted(self._header_context.keys())
            )
            if self._header_context
            else ""
        )
