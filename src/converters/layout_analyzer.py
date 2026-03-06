from dataclasses import dataclass, field
from typing import List


@dataclass
class ShapeRegion:
    """
    Represents one content region on a slide with normalised coordinates (0-1).

    All coordinate values are relative to slide width and height so that the
    analyzer is independent of unit systems (EMU, points, pixels, etc.).
    """
    content_md: str   # pre-rendered Markdown for this shape
    x: float          # left edge, 0-1
    y: float          # top edge, 0-1
    w: float          # width, 0-1
    h: float          # height, 0-1


@dataclass
class SlideLayout:
    """Result returned by LayoutAnalyzer.analyze()."""
    title: str
    bands: List[List[ShapeRegion]]  # each band is a row; sorted left-to-right
    n_cols: int                     # max columns across all bands


class LayoutAnalyzer:
    """
    Detects multi-column layout from a list of ShapeRegions.

    Algorithm:
    1. Separate title shape (topmost with y < 0.25, or the first shape by y).
    2. Cluster remaining shapes into horizontal bands by overlapping y-ranges.
    3. Within each band sort shapes by x; split into columns where the gap
       between adjacent shapes exceeds COLUMN_GAP_THRESHOLD of slide width.
    4. n_cols = max(len(band) for band in bands).
    5. If n_cols >= 2 → grid mode with <!-- $grid(n_cols) -->.

    SRP: sole responsibility is spatial layout classification.
    """

    TITLE_Y_THRESHOLD: float = 0.25    # shapes above this are title candidates
    COLUMN_GAP_THRESHOLD: float = 0.15 # x-gap > 15 % of slide width = new column
    BAND_OVERLAP_THRESHOLD: float = 0.5  # 50 % vertical overlap → same band

    def analyze(self, shapes: List[ShapeRegion]) -> SlideLayout:
        if not shapes:
            return SlideLayout(title="", bands=[], n_cols=1)

        title_shape, body_shapes = self._extract_title(shapes)
        title_md = title_shape.content_md if title_shape else ""

        if not body_shapes:
            return SlideLayout(title=title_md, bands=[], n_cols=1)

        bands = self._cluster_into_bands(body_shapes)
        # Sort each band left-to-right
        bands = [sorted(band, key=lambda s: s.x) for band in bands]
        # Sort bands top-to-bottom by the minimum y in the band
        bands.sort(key=lambda band: min(s.y for s in band))

        n_cols = max(len(band) for band in bands) if bands else 1
        return SlideLayout(title=title_md, bands=bands, n_cols=n_cols)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_title(self, shapes: List[ShapeRegion]):
        """
        Identify the title shape.

        A shape qualifies as the title only when its top edge is above
        TITLE_Y_THRESHOLD (i.e. y < 0.25 in normalised coordinates).
        If no shape meets that criterion, no title is extracted and all
        shapes flow into the body bands.
        """
        candidates = [s for s in shapes if s.y < self.TITLE_Y_THRESHOLD]
        if not candidates:
            return None, shapes
        title = min(candidates, key=lambda s: s.y)
        body = [s for s in shapes if s is not title]
        return title, body

    def _cluster_into_bands(self, shapes: List[ShapeRegion]) -> List[List[ShapeRegion]]:
        """
        Group shapes into horizontal bands using vertical overlap detection.

        Two shapes belong to the same band when their y-intervals overlap by
        at least BAND_OVERLAP_THRESHOLD of the smaller shape's height.
        """
        sorted_shapes = sorted(shapes, key=lambda s: s.y)
        if not sorted_shapes:
            return []

        bands: List[List[ShapeRegion]] = [[sorted_shapes[0]]]

        for shape in sorted_shapes[1:]:
            placed = False
            for band in bands:
                if self._overlaps_band(shape, band):
                    band.append(shape)
                    placed = True
                    break
            if not placed:
                bands.append([shape])

        return bands

    def _overlaps_band(self, shape: ShapeRegion, band: List[ShapeRegion]) -> bool:
        """Return True when shape vertically overlaps the band's y-extent."""
        band_y_min = min(s.y for s in band)
        band_y_max = max(s.y + s.h for s in band)
        shape_y_min = shape.y
        shape_y_max = shape.y + shape.h

        overlap_top = max(band_y_min, shape_y_min)
        overlap_bot = min(band_y_max, shape_y_max)
        overlap = max(0.0, overlap_bot - overlap_top)

        shape_height = shape.h or 0.01  # avoid division by zero
        return (overlap / shape_height) >= self.BAND_OVERLAP_THRESHOLD

    # ------------------------------------------------------------------
    # Markdown emission
    # ------------------------------------------------------------------

    def to_markdown(self, layout: SlideLayout) -> str:
        """
        Render a SlideLayout as md-reveal-wrapper Markdown.

        Single-column layouts emit content directly.
        Multi-column layouts wrap content in <!-- $grid(N) --> blocks.
        """
        lines: List[str] = []

        if layout.title:
            lines.append(f"# {layout.title}")
            lines.append("")

        if layout.n_cols < 2:
            # Flat layout — just concatenate band contents
            for band in layout.bands:
                for shape in band:
                    lines.append(shape.content_md.strip())
                    lines.append("")
        else:
            lines.append(f"<!-- $grid({layout.n_cols}) -->")
            lines.append("")
            first_cell = True
            for band in layout.bands:
                for shape in band:
                    if not first_cell:
                        lines.append("-----")
                        lines.append("")
                    # Check if this shape spans multiple columns
                    span = self._compute_span(shape, layout.n_cols)
                    if span > 1:
                        lines.append(f"<!-- $grid-cell({span}, 1) -->")
                        lines.append("")
                    lines.append(shape.content_md.strip())
                    lines.append("")
                    first_cell = False
            lines.append("<!-- $grid/ -->")
            lines.append("")

        return "\n".join(lines)

    def _compute_span(self, shape: ShapeRegion, n_cols: int) -> int:
        """Return the column span for a shape based on its width."""
        # A shape occupying more than (n_cols-1)/n_cols of slide width spans all cols
        col_width = 1.0 / n_cols
        return max(1, round(shape.w / col_width))
