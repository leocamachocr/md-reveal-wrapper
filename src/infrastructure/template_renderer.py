from pathlib import Path

from jinja2 import Template

from src.domain.config import PresentationConfig
from src.infrastructure.file_manager import FileManager
from src.infrastructure.resource_resolver import resolve_resource


class TemplateRenderer:
    """
    Renders the Jinja2 HTML template with slide content and config.
    SRP: sole responsibility is template rendering.
    DIP: depends on FileManager abstraction for writing output.
    """

    def __init__(self, file_manager: FileManager) -> None:
        self._file_manager = file_manager

    def render(
        self, slides_html: str, output_dir: Path, config: PresentationConfig
    ) -> Path:
        template_path = resolve_resource("templates/reveal_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            template = Template(f.read())

        html_content = template.render(slides=slides_html, **config.to_dict())
        return self._file_manager.write_html(output_dir, html_content)
