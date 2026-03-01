import re
import webbrowser
from pathlib import Path

from bs4 import BeautifulSoup

from src.application.markdown_parser import MarkdownParser
from src.application.slide_processor_pipeline import SlideProcessorPipelineBase
from src.domain.config import PresentationConfig
from src.infrastructure.file_manager import FileManager
from src.infrastructure.template_renderer import TemplateRenderer


class PresentationGenerator:
    """
    Orchestrates the full Markdown → Reveal.js HTML generation pipeline.

    SRP: coordinates the steps; each step is delegated to a specialist.
    DIP: all collaborators are injected as abstractions — this class never
         instantiates concrete infrastructure or processor classes directly.
    OCP: new processors are added via the pipeline builder, new rendering
         backends via TemplateRenderer, without modifying this class.
    """

    def __init__(
        self,
        parser: MarkdownParser,
        pipeline: SlideProcessorPipelineBase,
        renderer: TemplateRenderer,
        file_manager: FileManager,
        open_browser: bool = True,
    ) -> None:
        self._parser = parser
        self._pipeline = pipeline
        self._renderer = renderer
        self._file_manager = file_manager
        self._open_browser = open_browser

    def generate(self, md_file: Path, config: PresentationConfig) -> Path:
        md_content = md_file.read_text(encoding="utf-8")
        output_dir, assets_dir = self._file_manager.prepare_output_dir(md_file, config)

        processors = self._pipeline.build(md_file.parent, assets_dir, config)
        slides_html = self._build_slides(md_content, config, processors)

        self._file_manager.copy_base(assets_dir)
        if config.custom_theme:
            self._file_manager.copy_theme(config.custom_theme, assets_dir)

        output_file = self._renderer.render(slides_html, output_dir, config)
        print(f"Presentation generated at: {output_file}")

        if self._open_browser:
            webbrowser.open(f"file://{output_file}")

        return output_file

    def _build_slides(self, md_content: str, config: PresentationConfig, processors) -> str:
        # Use a whole-line regex match so that `---` inside table separator
        # rows (e.g. `| --- | --- |`) is never mistaken for a slide boundary.
        sep_pattern = r"(?m)^\s*" + re.escape(config.slide_separator) + r"\s*$"
        raw_slides = re.split(sep_pattern, md_content)
        context: dict = {}
        sections: list[str] = []

        for raw_slide in raw_slides:
            soup: BeautifulSoup = self._parser.parse(raw_slide)

            for processor in processors:
                processor.process(soup, context)

            breadcrumb = context.get("breadcrumb_text", "")

            # Wrap all slide elements in a .slide-content div
            wrapper = soup.new_tag("div", attrs={"class": "slide-content"})
            for element in list(soup.contents):
                wrapper.append(element.extract())
            soup.append(wrapper)

            sections.append(f'<section data-breadcrumb="{breadcrumb}">{soup}</section>')

        return "\n".join(sections)
