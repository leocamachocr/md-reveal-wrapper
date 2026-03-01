"""
Unit tests for the slide processor pipeline.

Each test class covers one processor, verifying that it:
  - mutates the BeautifulSoup tree correctly
  - does not produce side-effects outside its own scope
  - handles edge cases gracefully
"""

import pytest
from bs4 import BeautifulSoup
from pathlib import Path

from src.processors.blockquote_processor import BlockquoteProcessor
from src.processors.breadcrumb_processor import BreadcrumbProcessor
from src.processors.fragment_processor import FragmentProcessor
from src.processors.image_processor import ImageProcessor
from src.application.markdown_parser import MarkdownParser
from src.infrastructure.config_loader import ConfigLoader
from src.domain.config import PresentationConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ---------------------------------------------------------------------------
# BlockquoteProcessor
# ---------------------------------------------------------------------------

class TestBlockquoteProcessor:
    def test_info_callout_class_applied(self):
        soup = make_soup("<blockquote><p>[info] Important message</p></blockquote>")
        BlockquoteProcessor().process(soup, {})
        bq = soup.find("blockquote")
        assert "info" in bq.get("class", [])

    def test_warning_callout_class_applied(self):
        soup = make_soup("<blockquote><p>[warning] Be careful</p></blockquote>")
        BlockquoteProcessor().process(soup, {})
        bq = soup.find("blockquote")
        assert "warning" in bq.get("class", [])

    def test_tip_callout_class_applied(self):
        soup = make_soup("<blockquote><p>[tip] Use this approach</p></blockquote>")
        BlockquoteProcessor().process(soup, {})
        bq = soup.find("blockquote")
        assert "tip" in bq.get("class", [])

    def test_callout_message_preserved(self):
        soup = make_soup("<blockquote><p>[info] Important message</p></blockquote>")
        BlockquoteProcessor().process(soup, {})
        bq = soup.find("blockquote")
        assert bq.find("p").get_text() == "Important message"

    def test_non_matching_blockquote_is_unchanged(self):
        soup = make_soup("<blockquote><p>Regular quote</p></blockquote>")
        BlockquoteProcessor().process(soup, {})
        bq = soup.find("blockquote")
        assert bq.get("class") is None
        assert "Regular quote" in bq.get_text()

    def test_matching_is_case_insensitive(self):
        soup = make_soup("<blockquote><p>[INFO] Uppercase tag</p></blockquote>")
        BlockquoteProcessor().process(soup, {})
        bq = soup.find("blockquote")
        assert "info" in bq.get("class", [])

    def test_multiple_blockquotes_processed_independently(self):
        soup = make_soup(
            "<blockquote><p>[info] First</p></blockquote>"
            "<blockquote><p>[warning] Second</p></blockquote>"
        )
        BlockquoteProcessor().process(soup, {})
        bqs = soup.find_all("blockquote")
        assert "info" in bqs[0].get("class", [])
        assert "warning" in bqs[1].get("class", [])

    def test_context_dict_is_not_modified(self):
        soup = make_soup("<blockquote><p>[tip] Hint</p></blockquote>")
        context = {"some_key": "value"}
        BlockquoteProcessor().process(soup, context)
        assert context == {"some_key": "value"}


# ---------------------------------------------------------------------------
# FragmentProcessor
# ---------------------------------------------------------------------------

class TestFragmentProcessor:
    def test_fragment_class_added_when_enabled(self):
        soup = make_soup("<ul><li>Item 1</li><li>Item 2</li></ul>")
        FragmentProcessor(enabled=True).process(soup, {})
        for li in soup.find_all("li"):
            assert "fragment" in li.get("class", [])

    def test_no_fragment_class_when_disabled(self):
        soup = make_soup("<ul><li>Item 1</li><li>Item 2</li></ul>")
        FragmentProcessor(enabled=False).process(soup, {})
        for li in soup.find_all("li"):
            assert "fragment" not in li.get("class", [])

    def test_existing_classes_are_preserved(self):
        soup = make_soup('<ul><li class="custom">Item</li></ul>')
        FragmentProcessor(enabled=True).process(soup, {})
        li = soup.find("li")
        assert "fragment" in li.get("class", [])
        assert "custom" in li.get("class", [])

    def test_fragment_not_duplicated_if_already_present(self):
        soup = make_soup('<ul><li class="fragment">Item</li></ul>')
        FragmentProcessor(enabled=True).process(soup, {})
        li = soup.find("li")
        assert li.get("class", []).count("fragment") == 1

    def test_nested_list_items_all_get_fragment(self):
        soup = make_soup("<ul><li>A<ul><li>A1</li></ul></li></ul>")
        FragmentProcessor(enabled=True).process(soup, {})
        for li in soup.find_all("li"):
            assert "fragment" in li.get("class", [])

    def test_context_dict_is_not_modified(self):
        soup = make_soup("<ul><li>Item</li></ul>")
        context = {}
        FragmentProcessor(enabled=True).process(soup, context)
        assert context == {}


# ---------------------------------------------------------------------------
# BreadcrumbProcessor
# ---------------------------------------------------------------------------

class TestBreadcrumbProcessor:
    def test_single_h1_sets_breadcrumb(self):
        processor = BreadcrumbProcessor()
        soup = make_soup("<h1>Introduction</h1><p>Content</p>")
        context: dict = {}
        processor.process(soup, context)
        assert context["breadcrumb_text"] == "Introduction"

    def test_h2_appended_to_existing_h1(self):
        processor = BreadcrumbProcessor()
        context: dict = {}
        processor.process(make_soup("<h1>Chapter 1</h1>"), context)
        processor.process(make_soup("<h2>Section A</h2>"), context)
        assert context["breadcrumb_text"] == "Chapter 1 › Section A"

    def test_new_h1_clears_h2_context(self):
        processor = BreadcrumbProcessor()
        context: dict = {}
        processor.process(make_soup("<h1>Chapter 1</h1>"), context)
        processor.process(make_soup("<h2>Section A</h2>"), context)
        processor.process(make_soup("<h1>Chapter 2</h1>"), context)
        assert context["breadcrumb_text"] == "Chapter 2"

    def test_slide_without_heading_retains_previous_context(self):
        processor = BreadcrumbProcessor()
        context: dict = {}
        processor.process(make_soup("<h1>Chapter 1</h1>"), context)
        processor.process(make_soup("<p>No heading here</p>"), context)
        assert context["breadcrumb_text"] == "Chapter 1"

    def test_empty_slide_produces_empty_breadcrumb(self):
        processor = BreadcrumbProcessor()
        context: dict = {}
        processor.process(make_soup("<p>No heading</p>"), context)
        assert context["breadcrumb_text"] == ""

    def test_three_level_hierarchy(self):
        processor = BreadcrumbProcessor()
        context: dict = {}
        processor.process(make_soup("<h1>A</h1>"), context)
        processor.process(make_soup("<h2>B</h2>"), context)
        processor.process(make_soup("<h3>C</h3>"), context)
        assert context["breadcrumb_text"] == "A › B › C"

    def test_fresh_instance_starts_clean(self):
        p1 = BreadcrumbProcessor()
        context: dict = {}
        p1.process(make_soup("<h1>Chapter 1</h1>"), context)

        p2 = BreadcrumbProcessor()
        context2: dict = {}
        p2.process(make_soup("<p>No heading</p>"), context2)
        assert context2["breadcrumb_text"] == ""


# ---------------------------------------------------------------------------
# MarkdownParser
# ---------------------------------------------------------------------------

class TestMarkdownParser:
    def test_h1_parsed(self):
        soup = MarkdownParser().parse("# Hello World")
        assert soup.find("h1").get_text() == "Hello World"

    def test_paragraph_parsed(self):
        soup = MarkdownParser().parse("This is a paragraph.")
        assert "This is a paragraph." in soup.get_text()

    def test_unordered_list_parsed(self):
        soup = MarkdownParser().parse("- Item 1\n- Item 2\n- Item 3")
        assert len(soup.find_all("li")) == 3

    def test_code_block_produces_code_element(self):
        soup = MarkdownParser().parse("```python\nprint('hello')\n```")
        assert soup.find("code") is not None

    def test_code_block_with_line_numbers(self):
        soup = MarkdownParser().parse("```java [1|3-5]\nclass Foo {}\n```")
        code = soup.find("code")
        assert code is not None
        assert code.get("data-line-numbers") == "1|3-5"

    def test_code_block_language_class(self):
        soup = MarkdownParser().parse("```python\npass\n```")
        code = soup.find("code")
        assert "language-python" in (code.get("class") or [])

    def test_table_parsed(self):
        md = "| Col1 | Col2 |\n|------|------|\n| A    | B    |"
        soup = MarkdownParser().parse(md)
        assert soup.find("table") is not None

    def test_bold_text(self):
        soup = MarkdownParser().parse("**bold text**")
        assert soup.find("strong") is not None

    def test_inline_code(self):
        soup = MarkdownParser().parse("Use `my_function()` here.")
        assert soup.find("code") is not None


# ---------------------------------------------------------------------------
# ImageProcessor
# ---------------------------------------------------------------------------

class TestImageProcessor:
    def test_external_http_image_src_unchanged(self, tmp_path):
        soup = make_soup('<img src="https://example.com/img.png">')
        ImageProcessor(tmp_path / "assets", tmp_path).process(soup, {})
        assert soup.find("img")["src"] == "https://example.com/img.png"

    def test_external_data_uri_src_unchanged(self, tmp_path):
        soup = make_soup('<img src="data:image/png;base64,abc123">')
        ImageProcessor(tmp_path / "assets", tmp_path).process(soup, {})
        assert soup.find("img")["src"] == "data:image/png;base64,abc123"

    def test_all_images_get_lightbox_attribute(self, tmp_path):
        soup = make_soup('<img src="https://example.com/img.png">')
        ImageProcessor(tmp_path / "assets", tmp_path).process(soup, {})
        assert soup.find("img").has_attr("data-preview-image")

    def test_local_image_copied_and_src_rewritten(self, tmp_path):
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        (img_dir / "logo.png").write_bytes(b"fake png")

        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()

        soup = make_soup('<img src="images/logo.png">')
        ImageProcessor(assets_dir, tmp_path).process(soup, {})

        img = soup.find("img")
        assert img["src"] == "assets/images/logo.png"
        assert (assets_dir / "images" / "logo.png").exists()

    def test_missing_local_image_src_unchanged(self, tmp_path):
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        soup = make_soup('<img src="missing/image.png">')
        ImageProcessor(assets_dir, tmp_path).process(soup, {})
        assert soup.find("img")["src"] == "missing/image.png"

    def test_context_dict_is_not_modified(self, tmp_path):
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        soup = make_soup('<img src="https://example.com/img.png">')
        context = {"key": "value"}
        ImageProcessor(assets_dir, tmp_path).process(soup, context)
        assert context == {"key": "value"}


# ---------------------------------------------------------------------------
# PresentationGenerator — slide-splitting regression tests
# ---------------------------------------------------------------------------

from src.application.presentation_generator import PresentationGenerator
from src.application.slide_processor_pipeline import DefaultSlideProcessorPipeline
from src.infrastructure.file_manager import FileManager
from src.infrastructure.template_renderer import TemplateRenderer


def _make_generator() -> PresentationGenerator:
    fm = FileManager()
    return PresentationGenerator(
        parser=MarkdownParser(),
        pipeline=DefaultSlideProcessorPipeline(),
        renderer=TemplateRenderer(fm),
        file_manager=fm,
        open_browser=False,
    )


class TestSlideTableSplitting:
    """Regression: table separator rows must not be treated as slide breaks."""

    def _split(self, md: str, separator: str = "---") -> list[str]:
        """Call the private _build_slides and return the list of <section> tags."""
        from src.domain.config import PresentationConfig
        gen = _make_generator()
        config = PresentationConfig(slide_separator=separator, output_in_md_dir="false")
        html = gen._build_slides(md, config, [])
        # Each slide becomes a <section>; count them
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return soup.find_all("section")

    def test_table_not_split_by_separator(self):
        """A single slide containing a table must produce exactly one section."""
        md = "## Data\n\n| A | B |\n|---|---|\n| 1 | 2 |"
        sections = self._split(md)
        assert len(sections) == 1

    def test_table_renders_as_table_element(self):
        """The table must appear as a <table> inside the section, not broken markup."""
        md = "## Data\n\n| A | B |\n|---|---|\n| 1 | 2 |"
        sections = self._split(md)
        assert sections[0].find("table") is not None

    def test_table_with_many_dashes_not_split(self):
        """Wider column separators like |-----|-----| must also be safe."""
        md = "| Col1 | Col2 |\n|------|------|\n| x    | y    |"
        sections = self._split(md)
        assert len(sections) == 1

    def test_explicit_slide_break_still_works(self):
        """A real --- separator between two slides must still split correctly."""
        md = "# Slide one\n\n---\n\n# Slide two"
        sections = self._split(md)
        assert len(sections) == 2

    def test_table_and_slide_break_together(self):
        """Slide with table followed by a separator and a second slide."""
        md = (
            "## Slide 1\n\n"
            "| A | B |\n|---|---|\n| 1 | 2 |\n\n"
            "---\n\n"
            "## Slide 2\n\nJust text."
        )
        sections = self._split(md)
        assert len(sections) == 2
        assert sections[0].find("table") is not None
        assert sections[1].find("table") is None


# ---------------------------------------------------------------------------
# ConfigLoader
# ---------------------------------------------------------------------------

class TestConfigLoader:
    def test_loads_transition(self, tmp_path):
        cfg = tmp_path / "config.properties"
        cfg.write_text("transition=slide\n", encoding="utf-8")
        config = ConfigLoader().load(str(cfg))
        assert config.transition == "slide"

    def test_comments_are_ignored(self, tmp_path):
        cfg = tmp_path / "config.properties"
        cfg.write_text("# comment\ntransition=fade\n", encoding="utf-8")
        config = ConfigLoader().load(str(cfg))
        assert config.transition == "fade"

    def test_missing_keys_use_defaults(self, tmp_path):
        cfg = tmp_path / "config.properties"
        cfg.write_text("transition=slide\n", encoding="utf-8")
        config = ConfigLoader().load(str(cfg))
        assert config.reveal_version == "4.6.0"
        assert config.transition == "slide"

    def test_custom_theme_loaded(self, tmp_path):
        cfg = tmp_path / "config.properties"
        cfg.write_text("custom_theme=modern.css\n", encoding="utf-8")
        config = ConfigLoader().load(str(cfg))
        assert config.custom_theme == "modern.css"

    def test_empty_file_uses_all_defaults(self, tmp_path):
        cfg = tmp_path / "config.properties"
        cfg.write_text("", encoding="utf-8")
        config = ConfigLoader().load(str(cfg))
        assert isinstance(config, PresentationConfig)
        assert config.custom_theme is None

    def test_fragments_enabled_property_true(self, tmp_path):
        cfg = tmp_path / "config.properties"
        cfg.write_text("enable_fragments=true\n", encoding="utf-8")
        config = ConfigLoader().load(str(cfg))
        assert config.fragments_enabled is True

    def test_fragments_enabled_property_false(self, tmp_path):
        cfg = tmp_path / "config.properties"
        cfg.write_text("enable_fragments=false\n", encoding="utf-8")
        config = ConfigLoader().load(str(cfg))
        assert config.fragments_enabled is False

    def test_to_dict_contains_all_template_keys(self, tmp_path):
        cfg = tmp_path / "config.properties"
        cfg.write_text("", encoding="utf-8")
        config = ConfigLoader().load(str(cfg))
        d = config.to_dict()
        required_keys = {
            "reveal_cdn", "reveal_version",
            "enable_controls", "enable_progress", "enable_history",
            "align_center", "transition", "show_header_trail",
        }
        assert required_keys.issubset(d.keys())
