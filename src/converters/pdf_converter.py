import re
import statistics
from pathlib import Path
from typing import List, Optional, Tuple

from src.converters.base import PresentationConverter
from src.converters.layout_analyzer import LayoutAnalyzer, ShapeRegion


class PDFConverter(PresentationConverter):
    """
    Converts a .pdf file to md-reveal-wrapper Markdown.

    Requires: pdfplumber, Pillow

    SRP: sole responsibility is PDF → Markdown translation.
    """

    LINE_GAP_THRESHOLD: float = 3.0   # points: words closer → same line
    BLOCK_GAP_THRESHOLD: float = 12.0 # points: lines further apart → new block
    HEADING_SIZE_MARGIN: float = 2.0  # points above median → heading candidate

    def convert(self, input_path: Path) -> str:
        try:
            import pdfplumber
        except ImportError as exc:
            raise ImportError(
                "pdfplumber is required: pip install pdfplumber"
            ) from exc

        assets_dir = input_path.parent / f"{input_path.stem}_assets"
        analyzer = LayoutAnalyzer()
        slide_mds: List[str] = []
        img_counter = [0]

        with pdfplumber.open(str(input_path)) as pdf:
            for page in pdf.pages:
                slide_md = self._convert_page(page, assets_dir, img_counter, analyzer)
                slide_mds.append(slide_md)

        return "\n\n---\n\n".join(slide_mds)

    # ------------------------------------------------------------------
    # Per-page conversion
    # ------------------------------------------------------------------

    def _convert_page(self, page, assets_dir: Path, img_counter: List[int], analyzer: LayoutAnalyzer) -> str:
        pw = page.width or 1
        ph = page.height or 1

        # --- Text blocks ---
        words = page.extract_words(extra_attrs=["size", "fontname"])
        lines = self._group_words_into_lines(words)
        text_blocks = self._group_lines_into_blocks(lines)

        # Compute median font size for heading detection
        all_sizes = [w.get("size", 12) for w in words if w.get("size")]
        median_size = statistics.median(all_sizes) if all_sizes else 12.0

        regions: List[ShapeRegion] = []
        for block in text_blocks:
            content_md, bx, by, bw, bh = self._block_to_markdown(
                block, median_size, pw, ph
            )
            if content_md.strip():
                regions.append(ShapeRegion(content_md=content_md, x=bx, y=by, w=bw, h=bh))

        # --- Images ---
        for img_info in (page.images or []):
            img_md = self._extract_image(page, img_info, assets_dir, img_counter, pw, ph)
            if img_md:
                x0, top, x1, bottom = (
                    img_info.get("x0", 0),
                    img_info.get("top", 0),
                    img_info.get("x1", pw),
                    img_info.get("bottom", ph),
                )
                regions.append(ShapeRegion(
                    content_md=img_md,
                    x=x0 / pw, y=top / ph,
                    w=(x1 - x0) / pw, h=(bottom - top) / ph,
                ))

        layout = analyzer.analyze(regions)
        return analyzer.to_markdown(layout)

    # ------------------------------------------------------------------
    # Word / line / block grouping
    # ------------------------------------------------------------------

    def _group_words_into_lines(self, words: List[dict]) -> List[List[dict]]:
        """Cluster words into lines by top-coordinate proximity."""
        if not words:
            return []
        sorted_words = sorted(words, key=lambda w: (w.get("top", 0), w.get("x0", 0)))
        lines: List[List[dict]] = [[sorted_words[0]]]
        for word in sorted_words[1:]:
            last_line = lines[-1]
            last_top = last_line[-1].get("top", 0)
            cur_top = word.get("top", 0)
            if abs(cur_top - last_top) <= self.LINE_GAP_THRESHOLD:
                last_line.append(word)
            else:
                lines.append([word])
        return lines

    def _group_lines_into_blocks(self, lines: List[List[dict]]) -> List[List[List[dict]]]:
        """Group lines into blocks separated by vertical gaps > BLOCK_GAP_THRESHOLD."""
        if not lines:
            return []
        blocks: List[List[List[dict]]] = [[lines[0]]]
        for line in lines[1:]:
            prev_line = blocks[-1][-1]
            prev_bottom = max(w.get("bottom", w.get("top", 0)) for w in prev_line)
            cur_top = min(w.get("top", 0) for w in line)
            gap = cur_top - prev_bottom
            if gap > self.BLOCK_GAP_THRESHOLD:
                blocks.append([line])
            else:
                blocks[-1].append(line)
        return blocks

    # ------------------------------------------------------------------
    # Block → Markdown
    # ------------------------------------------------------------------

    def _block_to_markdown(
        self,
        block: List[List[dict]],
        median_size: float,
        pw: float,
        ph: float,
    ) -> Tuple[str, float, float, float, float]:
        """Return (markdown_text, x, y, w, h) for a block."""
        all_words_flat = [w for line in block for w in line]
        if not all_words_flat:
            return "", 0, 0, 0, 0

        bx0 = min(w.get("x0", 0) for w in all_words_flat) / pw
        by0 = min(w.get("top", 0) for w in all_words_flat) / ph
        bx1 = max(w.get("x1", pw) for w in all_words_flat) / pw
        by1 = max(w.get("bottom", ph) for w in all_words_flat) / ph

        # Determine size of each line (max word size in line)
        lines_md: List[str] = []
        for line in block:
            raw_text = " ".join(w.get("text", "") for w in line)
            line_text = self._clean_text(raw_text).strip()
            if not line_text:
                continue
            line_size = max((w.get("size", 12) for w in line), default=12)
            md_line = self._classify_line(line_text, line_size, median_size, all_words_flat)
            lines_md.append(md_line)

        return "\n".join(lines_md), bx0, by0, bx1 - bx0, by1 - by0

    def _classify_line(
        self,
        text: str,
        size: float,
        median_size: float,
        block_words: List[dict],
    ) -> str:
        if not text:
            return ""

        # Heading detection: significantly larger than median
        if size >= median_size + self.HEADING_SIZE_MARGIN:
            # Find the largest size across the whole block to rank headings
            max_size = max(w.get("size", 12) for w in block_words)
            second_max = sorted({w.get("size", 12) for w in block_words}, reverse=True)
            if len(second_max) >= 2:
                if size >= second_max[0]:
                    return f"# {text}"
                if size >= second_max[1]:
                    return f"## {text}"
                return f"### {text}"
            return f"# {text}"

        # List detection
        if re.match(r"^[\u2022\u2023\u25E6\-\*]\s+", text):
            item = re.sub(r"^[\u2022\u2023\u25E6\-\*]\s+", "", text)
            return f"- {item}"
        if re.match(r"^\d+[\.\)]\s+", text):
            item = re.sub(r"^\d+[\.\)]\s+", "", text)
            return f"- {item}"

        return text

    # ------------------------------------------------------------------
    # Text cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Remove unresolved PDF glyph references that pdfplumber emits when it
        cannot map a CID to a Unicode character, e.g. "(cid:466)".
        """
        return re.sub(r"\(cid:\d+\)", "", text)

    # ------------------------------------------------------------------
    # Image extraction
    # ------------------------------------------------------------------

    def _extract_image(
        self,
        page,
        img_info: dict,
        assets_dir: Path,
        img_counter: List[int],
        pw: float,
        ph: float,
    ) -> str:
        try:
            from PIL import Image
            import io

            img_counter[0] += 1
            assets_dir.mkdir(parents=True, exist_ok=True)

            x0 = img_info.get("x0", 0)
            top = img_info.get("top", 0)
            x1 = img_info.get("x1", pw)
            bottom = img_info.get("bottom", ph)

            # Crop the region from the page raster
            cropped = page.crop((x0, top, x1, bottom))
            pil_img = cropped.to_image(resolution=150)

            img_path = assets_dir / f"img_{img_counter[0]}.png"
            pil_img.save(str(img_path))
            return f"![]({assets_dir.name}/img_{img_counter[0]}.png)"
        except Exception:
            return ""
