import re

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from src.processors.base import SlideProcessor


class GridProcessor(SlideProcessor):
    """
    Converts a <!-- $grid(N) --> ... <!-- $grid/ --> block into a CSS grid.
    Items are delimited by <hr> tags (produced by ----- in Markdown).

    Per-cell spanning (optional):
        After an <hr> separator, place <!-- $grid-cell(cols, rows) --> as the
        first line of the new cell to make it span multiple columns and/or rows.
        Omitting the comment defaults to colspan=1, rowspan=1 (current behaviour).

    SRP: sole responsibility is grid layout transformation.
    OCP: extended by changing only CSS or the regex pattern.
    """

    _OPEN = re.compile(r"^\s*\$grid\((\d+)\)\s*$")
    _CLOSE = re.compile(r"^\s*\$grid/\s*$")
    _CELL = re.compile(r"^\s*\$grid-cell\((\d+),\s*(\d+)\)\s*$")

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

        # Split the now-detached nodes by <hr> into groups with span info
        groups = self._split_by_hr(items_raw)

        # Build grid container
        grid = soup.new_tag("div", attrs={"class": "slide-grid"})
        grid["style"] = f"--grid-cols: {cols}"
        for group_nodes, colspan, rowspan in groups:
            item = soup.new_tag("div", attrs={"class": "grid-item"})
            spans = []
            if colspan > 1:
                spans.append(f"grid-column: span {colspan}")
            if rowspan > 1:
                spans.append(f"grid-row: span {rowspan}")
            if spans:
                item["style"] = "; ".join(spans)
            for n in group_nodes:
                item.append(n)  # already detached — no .extract() needed
            grid.append(item)

        # Replace open comment with grid; remove close comment
        open_node.replace_with(grid)
        close_node.extract()

    @classmethod
    def _split_by_hr(cls, nodes):
        """
        Split nodes by <hr> into groups.

        Returns a list of (nodes, colspan, rowspan) tuples.
        If the first node of a group is a <!-- $grid-cell(C,R) --> comment it is
        consumed and its values become the span; otherwise defaults are (1, 1).
        """
        raw_groups = []
        current = []
        for node in nodes:
            if isinstance(node, Tag) and node.name == "hr":
                if current:
                    raw_groups.append(current)
                current = []
            elif isinstance(node, NavigableString) and not str(node).strip():
                continue  # skip whitespace-only text nodes between blocks
            else:
                current.append(node)
        if current:
            raw_groups.append(current)

        result = []
        for group in raw_groups:
            colspan, rowspan = 1, 1
            remaining = group
            if remaining and isinstance(remaining[0], Comment):
                m = cls._CELL.match(str(remaining[0]).strip())
                if m:
                    colspan = int(m.group(1))
                    rowspan = int(m.group(2))
                    remaining = remaining[1:]
                    # Drop any whitespace-only text nodes immediately after the comment
                    while (
                        remaining
                        and isinstance(remaining[0], NavigableString)
                        and not str(remaining[0]).strip()
                    ):
                        remaining = remaining[1:]
            result.append((remaining, colspan, rowspan))
        return result
