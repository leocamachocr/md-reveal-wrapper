import re

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from src.processors.base import SlideProcessor


class GridProcessor(SlideProcessor):
    """
    Converts a <!-- $grid(N) --> ... <!-- $grid/ --> block into a CSS grid.
    Items are delimited by <hr> tags (produced by ----- in Markdown).

    SRP: sole responsibility is grid layout transformation.
    OCP: extended by changing only CSS or the regex pattern.
    """

    _OPEN = re.compile(r"^\s*\$grid\((\d+)\)\s*$")
    _CLOSE = re.compile(r"^\s*\$grid/\s*$")

    def process(self, soup: BeautifulSoup, context: dict) -> None:
        # Snapshot children list to avoid live-iterator issues
        children = list(soup.children)

        open_node = None
        cols = None
        for child in children:
            if isinstance(child, Comment):
                m = self._OPEN.match(str(child).strip())
                if m:
                    open_node = child
                    cols = int(m.group(1))
                    break

        if open_node is None:
            return  # no grid in this slide

        # Collect siblings until closing comment
        items_raw = []
        close_node = None
        node = open_node.next_sibling
        while node is not None:
            if isinstance(node, Comment) and self._CLOSE.match(str(node).strip()):
                close_node = node
                break
            items_raw.append(node)
            node = node.next_sibling

        if close_node is None:
            return  # malformed — leave slide untouched

        # Detach ALL nodes between the comments from the DOM upfront so that
        # <hr> separators (not included in any group) don't linger in the tree.
        for node in items_raw:
            node.extract()

        # Split the now-detached nodes by <hr> into groups
        groups = self._split_by_hr(items_raw)

        # Build grid container
        grid = soup.new_tag("div", attrs={"class": "slide-grid"})
        grid["style"] = f"--grid-cols: {cols}"
        for group in groups:
            item = soup.new_tag("div", attrs={"class": "grid-item"})
            for n in group:
                item.append(n)  # already detached — no .extract() needed
            grid.append(item)

        # Replace open comment with grid; remove close comment
        open_node.replace_with(grid)
        close_node.extract()

    @staticmethod
    def _split_by_hr(nodes):
        groups = []
        current = []
        for node in nodes:
            if isinstance(node, Tag) and node.name == "hr":
                if current:
                    groups.append(current)
                current = []
            elif isinstance(node, NavigableString) and not str(node).strip():
                continue  # skip whitespace-only text nodes between blocks
            else:
                current.append(node)
        if current:
            groups.append(current)
        return groups
