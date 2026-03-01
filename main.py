import sys
from pathlib import Path

from src.application.markdown_parser import MarkdownParser
from src.application.presentation_generator import PresentationGenerator
from src.application.slide_processor_pipeline import DefaultSlideProcessorPipeline
from src.infrastructure.config_loader import ConfigLoader
from src.infrastructure.file_manager import FileManager
from src.infrastructure.resource_resolver import resolve_resource
from src.infrastructure.template_renderer import TemplateRenderer


def build_generator(open_browser: bool = True) -> PresentationGenerator:
    """
    Compose the object graph (poor-man's DI container).
    All concrete dependencies are wired here — application code only sees
    abstractions.
    """
    file_manager = FileManager()
    return PresentationGenerator(
        parser=MarkdownParser(),
        pipeline=DefaultSlideProcessorPipeline(),
        renderer=TemplateRenderer(file_manager),
        file_manager=file_manager,
        open_browser=open_browser,
    )


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python main.py <file.md | folder>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    config = ConfigLoader().load(resolve_resource("config.properties"))
    generator = build_generator()

    if input_path.is_dir():
        md_files = list(input_path.glob("*.md"))
        if not md_files:
            print("No Markdown files found in the folder.")
            sys.exit(1)
        for md_file in md_files:
            generator.generate(md_file, config)
    elif input_path.is_file():
        generator.generate(input_path, config)
    else:
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
