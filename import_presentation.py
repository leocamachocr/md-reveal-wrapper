"""
import_presentation.py — CLI entry point for the presentation importer.

Converts .pptx or .pdf files to md-reveal-wrapper Markdown, extracting
images with slide-aware naming and optionally opening a preview.

Usage:
    python import_presentation.py path/to/presentation.pptx
    python import_presentation.py path/to/presentation.pdf --output custom.md
    python import_presentation.py path/to/presentation.pptx --preview
"""

import sys
import webbrowser
from pathlib import Path

from src.presentation_importer import PresentationImporter


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        _print_help()
        sys.exit(0)

    input_path, output_path, preview = _parse_args(args)

    if not input_path.is_file():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    try:
        importer = PresentationImporter.for_file(input_path)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    try:
        result = importer.import_file(input_path, output_path)
    except ImportError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    print(f"Slides processed : {result.slide_count}")
    print(f"Images extracted : {result.image_count}")
    print(f"Output           : {result.output_path}")

    if preview:
        _open_preview(result.output_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_args(args: list):
    """Return (input_path, output_path | None, preview: bool)."""
    input_path = Path(args[0])
    output_path = None
    preview = False

    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--output" and i + 1 < len(args):
            output_path = Path(args[i + 1])
            i += 2
        elif arg == "--preview":
            preview = True
            i += 1
        else:
            print(f"Warning: Unknown argument '{arg}' ignored.")
            i += 1

    return input_path, output_path, preview


def _open_preview(md_path: Path) -> None:
    """
    Generate and open a Reveal.js presentation from the produced Markdown.
    Delegates to main.py's build_generator (the SOLID pipeline).
    """
    try:
        from main import build_generator
        from src.infrastructure.config_loader import ConfigLoader
        from src.infrastructure.resource_resolver import resolve_resource

        config = ConfigLoader().load(resolve_resource("config.properties"))
        build_generator(open_browser=True).generate(md_path, config)
    except Exception as exc:
        print(f"Preview error: {exc}")
        print(f"Open manually: {md_path}")


def _print_help() -> None:
    print(__doc__.strip())


if __name__ == "__main__":
    main()
