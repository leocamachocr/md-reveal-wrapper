"""
convert.py — CLI entry point for PPTX/PDF → Markdown conversion.

Wraps the existing src.converters pipeline.

Usage:
    python convert.py path/to/presentation.pptx
    python convert.py path/to/document.pdf output.md
"""

import sys
from pathlib import Path

from src.converters.pptx_converter import PPTXConverter
from src.converters.pdf_converter import PDFConverter

_CONVERTERS = {
    ".pptx": PPTXConverter,
    ".ppt":  PPTXConverter,
    ".pdf":  PDFConverter,
}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python convert.py <file.pptx|file.pdf> [output.md]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_path.with_suffix(".md")

    if not input_path.is_file():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    ext = input_path.suffix.lower()
    converter_cls = _CONVERTERS.get(ext)
    if converter_cls is None:
        supported = ", ".join(_CONVERTERS)
        print(f"Error: Unsupported format '{ext}'. Supported: {supported}")
        sys.exit(1)

    md_content = converter_cls().convert(input_path)
    output_path.write_text(md_content, encoding="utf-8")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()