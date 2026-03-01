from src.domain.config import PresentationConfig


class ConfigLoader:
    """
    Loads a .properties file and maps its keys to a PresentationConfig.
    SRP: sole responsibility is parsing config files.
    OCP: adding new config keys requires only updating PresentationConfig,
         not this loader.
    """

    def load(self, file_path: str) -> PresentationConfig:
        raw = self._parse_properties(file_path)
        return self._to_config(raw)

    def _parse_properties(self, file_path: str) -> dict:
        cfg: dict = {}
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    cfg[key.strip()] = value.strip()
        return cfg

    def _to_config(self, raw: dict) -> PresentationConfig:
        return PresentationConfig(
            slide_separator=raw.get("slide_separator", "---"),
            reveal_version=raw.get("reveal_version", "4.6.0"),
            transition=raw.get("transition", "fade"),
            reveal_cdn=raw.get("reveal_cdn", "https://cdnjs.cloudflare.com/ajax/libs/reveal.js"),
            enable_progress=raw.get("enable_progress", "true"),
            enable_controls=raw.get("enable_controls", "true"),
            enable_history=raw.get("enable_history", "true"),
            align_center=raw.get("align_center", "true"),
            width=raw.get("width", "1200"),
            height=raw.get("height", "1080"),
            margin=raw.get("margin", "0.1"),
            min_scale=raw.get("min_scale", "0.6"),
            max_scale=raw.get("max_scale", "1.2"),
            enable_fragments=raw.get("enable_fragments", "true"),
            show_header_trail=raw.get("show_header_trail", "true"),
            font_base=raw.get("font_base", "28px"),
            font_h1=raw.get("font_h1", "2.5em"),
            font_h2=raw.get("font_h2", "2em"),
            font_h3=raw.get("font_h3", "1.5em"),
            font_h4=raw.get("font_h4", "1.2em"),
            font_h5=raw.get("font_h5", "1em"),
            font_h6=raw.get("font_h6", "0.9em"),
            font_p=raw.get("font_p", "1em"),
            font_li=raw.get("font_li", "1em"),
            output_in_md_dir=raw.get("output_in_md_dir", "false"),
            custom_theme=raw.get("custom_theme"),
        )
