from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class PresentationConfig:
    """
    Immutable value object holding all presentation settings.
    SRP: sole responsibility is to hold and expose configuration data.
    """
    slide_separator: str = "---"
    reveal_version: str = "4.6.0"
    theme: str = "white"
    transition: str = "fade"
    reveal_cdn: str = "https://cdnjs.cloudflare.com/ajax/libs/reveal.js"
    enable_progress: str = "true"
    enable_controls: str = "true"
    enable_history: str = "true"
    align_center: str = "true"
    width: str = "1200"
    height: str = "1080"
    margin: str = "0.1"
    min_scale: str = "0.6"
    max_scale: str = "1.2"
    enable_fragments: str = "true"
    show_header_trail: str = "true"
    highlight_theme: str = "atom-one-light"
    font_base: str = "28px"
    font_h1: str = "2.5em"
    font_h2: str = "2em"
    font_h3: str = "1.5em"
    font_h4: str = "1.2em"
    font_h5: str = "1em"
    font_h6: str = "0.9em"
    font_p: str = "1em"
    font_li: str = "1em"
    output_in_md_dir: str = "false"
    custom_theme: Optional[str] = None

    def to_dict(self) -> dict:
        """Return a flat dict for Jinja2 template rendering."""
        return asdict(self)

    @property
    def fragments_enabled(self) -> bool:
        return self.enable_fragments.lower() == "true"

    @property
    def output_in_md_directory(self) -> bool:
        return self.output_in_md_dir.lower() == "true"
