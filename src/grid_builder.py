"""
grid_builder.py — low-level grid Markdown assembly for md-reveal-wrapper.

Grid syntax produced by this module:

    <!-- $grid(N) -->       open an N-column grid
    cell content 1
    -----                   cell separator
    cell content 2
    <!-- $grid/ -->         close the grid

    <!-- $grid-cell(span, row) -->   optional per-cell span directive

SRP: sole responsibility is generating correct grid-syntax Markdown strings.
OCP: positioning rules and grid variants can be extended by subclassing.
"""

from typing import List


class GridBuilder:
    """
    Assembles grid-syntax Markdown blocks for md-reveal-wrapper slides.

    Usage::

        gb = GridBuilder()

        # Standalone image, auto-positioned into a 2-column grid when
        # the image is clearly on the left or right side of the slide:
        md = gb.image_block("images/slide_1_img_1.png", x_frac=0.65, w_frac=0.30)

        # Explicit N-column block from pre-formatted cell strings:
        md = gb.n_col(["Left text", "Right text"], n=2)
    """

    CELL_SEP = "-----"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def image_block(self, img_rel_path: str, x_frac: float, w_frac: float) -> str:
        """
        Return Markdown for an image, wrapping it in a 2-column grid when
        the image is clearly positioned on one side of the slide.

        Positioning rules (per spec):
            w_frac >= 0.60               → full-width image, plain tag, no grid
            x_frac < 0.40               → image in left column of a 2-col grid
            x_frac > 0.60               → image in right column of a 2-col grid
            0.40 <= x_frac <= 0.60      → centred image, plain tag, no grid

        Args:
            img_rel_path: Relative path from the .md file to the image file.
            x_frac:       Left edge of the image normalised to slide width (0–1).
            w_frac:       Width of the image normalised to slide width (0–1).
        """
        img_md = f"![]({img_rel_path})"

        if w_frac >= 0.60 or 0.40 <= x_frac <= 0.60:
            return img_md

        if x_frac < 0.40:
            return self.n_col([img_md, ""], n=2)

        return self.n_col(["", img_md], n=2)

    def n_col(self, cells: List[str], n: int) -> str:
        """
        Build an N-column grid block from a list of cell content strings.

        Args:
            cells: Content string for each cell, ordered left to right.
            n:     Column count declared in the opening grid comment.
        """
        lines: List[str] = [f"<!-- $grid({n}) -->", ""]
        for i, cell in enumerate(cells):
            if i > 0:
                lines += [self.CELL_SEP, ""]
            lines.append(cell.strip())
            lines.append("")
        lines.append("<!-- $grid/ -->")
        return "\n".join(lines)

    def cell_span(self, content: str, col_span: int, row_span: int = 1) -> str:
        """
        Prefix *content* with a grid-cell span directive.

        Args:
            content:  Markdown content for the cell.
            col_span: Number of columns the cell spans.
            row_span: Number of rows the cell spans (default 1).
        """
        directive = f"<!-- $grid-cell({col_span}, {row_span}) -->"
        return f"{directive}\n\n{content.strip()}"