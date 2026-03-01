import shutil
import tempfile
from pathlib import Path

from src.domain.config import PresentationConfig
from src.infrastructure.resource_resolver import resolve_resource


class FileManager:
    """
    Handles all file-system operations for a presentation build.
    SRP: sole responsibility is managing output directories and file I/O.
    DIP: consumers depend on this abstraction, not on os/shutil directly.
    """

    def prepare_output_dir(
        self, md_file: Path, config: PresentationConfig
    ) -> tuple[Path, Path]:
        """Create and return (output_dir, assets_dir)."""
        if config.output_in_md_directory:
            output_dir = md_file.parent / f"md_reveal_{md_file.stem}"
        else:
            output_dir = Path(tempfile.mkdtemp())

        assets_dir = output_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        return output_dir, assets_dir

    def copy_base(self, assets_dir: Path) -> None:
        """Copy the structural base CSS into the assets directory."""
        src = resolve_resource("templates/base.css")
        dst = assets_dir / "base.css"
        shutil.copy(src, str(dst))

    def copy_theme(self, theme_filename: str, assets_dir: Path) -> None:
        """Copy a bundled CSS theme into the assets directory."""
        src = resolve_resource(f"templates/themes/{theme_filename}")
        dst = assets_dir / theme_filename
        shutil.copy(src, str(dst))

    def write_html(self, output_dir: Path, html_content: str) -> Path:
        """Write the rendered HTML and return the output file path."""
        output_file = output_dir / "presentation.html"
        output_file.write_text(html_content, encoding="utf-8")
        return output_file
