# CLAUDE.md — md-reveal-wrapper

Project instructions for Claude Code. Read this fully before touching any file.

---

## What this project does

`md-reveal-wrapper` converts **Markdown files** into self-contained
**Reveal.js HTML presentations**, opened automatically in the browser.
The Markdown uses `---` as a slide separator (configurable).

There are **two entry points**:

| Entry point | Status | Use |
|---|---|---|
| `main.py` | Active (SOLID refactor) | All new work lives here |
| `marp_to_reveal.py` | Legacy, kept intact | Do not modify |
| `app.py` | Tkinter GUI | Wraps `main.py` pipeline |

---

## Project layout

```
md-reveal-wrapper/
├── main.py                          CLI entry point — DI wiring only
├── app.py                           Tkinter desktop GUI
├── marp_to_reveal.py                Legacy script — do not modify
├── config.properties                Default runtime config
├── requirements.txt
│
├── src/
│   ├── domain/
│   │   └── config.py                PresentationConfig dataclass
│   ├── infrastructure/
│   │   ├── config_loader.py         .properties → PresentationConfig
│   │   ├── file_manager.py          Output dirs, asset copy, temp dirs
│   │   ├── resource_resolver.py     PyInstaller-safe path resolution
│   │   └── template_renderer.py     Jinja2 → HTML
│   ├── processors/
│   │   ├── base.py                  Abstract SlideProcessor
│   │   ├── image_processor.py       Copy images, rewrite src attrs
│   │   ├── blockquote_processor.py  [info]/[warning]/[tip] callouts
│   │   ├── fragment_processor.py    .fragment on <li> elements
│   │   └── breadcrumb_processor.py  Heading context across slides
│   └── application/
│       ├── markdown_parser.py       MD → BeautifulSoup (patches fence)
│       ├── slide_processor_pipeline.py  DefaultSlideProcessorPipeline factory
│       └── presentation_generator.py    Orchestrates the full pipeline
│
├── templates/
│   ├── reveal_template.html         Jinja2 template (do not break DOM)
│   └── themes/                      CSS themes — one file = one theme
│       ├── modern-idea-light.css    Default theme
│       ├── minimal-light.css
│       ├── minimal-dark.css
│       ├── minimal-wide-serif.css
│       └── ...
│
├── examples/
│   ├── demo_presentation.md
│   └── minimal-wide-serif-demo.md
│
└── tests/
    └── test_processors.py           50 unit + regression tests
```

---

## Architecture (SOLID)

- **SRP** — each class has one reason to change.
- **OCP** — add a new processor by subclassing `SlideProcessor`; no existing code touched.
- **LSP** — all processors are interchangeable via `SlideProcessor.process(soup, context)`.
- **ISP** — `SlideProcessor` exposes a single method.
- **DIP** — `PresentationGenerator` depends on injected abstractions; `main.py` is the DI root.

### Pipeline flow

```
Markdown file
  → read_text()
  → re.split(whole-line separator)        ← slide splitting (see bug history)
  → MarkdownParser.parse()                ← markdown-it-py + BeautifulSoup
  → [processor1, processor2, ...].process(soup, context)
  → wrap in <div class="slide-content">
  → TemplateRenderer.render()             ← Jinja2 → reveal_template.html
  → FileManager.write_html()              ← temp dir (GUI) or md dir (CLI)
  → webbrowser.open()
```

### PresentationConfig

Dataclass in `src/domain/config.py`. All fields are **strings** (`"true"`/`"false"` for booleans).
Two computed bool properties: `fragments_enabled`, `output_in_md_directory`.

Key fields:

| Field | Default | Notes |
|---|---|---|
| `slide_separator` | `---` | Must be whole-line to avoid table conflicts |
| `custom_theme` | `None` | Filename only, e.g. `modern-idea-light.css` |
| `output_in_md_dir` | `"false"` | GUI always forces `"false"` (uses temp dir) |
| `enable_fragments` | `"true"` | Adds `.fragment` to all `<li>` elements |
| `show_header_trail` | `"true"` | Enables breadcrumb bar |

---

## Theme system

- **Location**: `templates/themes/*.css` — one CSS file = one theme.
- **Discovery**: automatic — `Path.glob("*.css")` in both `app.py` and `FileManager`.
- **Injection**: `FileManager.copy_theme()` copies the CSS into `output_dir/assets/`.
  The template loads it last: `<link rel="stylesheet" href="assets/{{ custom_theme }}>`.
  Since it loads after the Reveal.js base theme and highlight.js, it wins all cascade battles.
- **No build step** — raw CSS only, no SCSS, no bundler.
- **Adding a theme**: drop a `.css` file into `templates/themes/`. Zero wiring needed.

### DOM structure themes must respect

```html
<div class="reveal">
  <div id="header-trail" class="header-trail"></div>   <!-- breadcrumb, fixed -->
  <div class="slides">
    <section data-breadcrumb="Chapter › Section">
      <div class="slide-content">
        <!-- rendered Markdown content -->
      </div>
    </section>
  </div>
</div>
```

Key selectors every theme must style:

| Selector | Purpose |
|---|---|
| `.reveal` | Root container — background, font-family |
| `.reveal .slides section` | Slide surface |
| `.header-trail` | Breadcrumb strip (fixed, top-left) |
| `.header-trail .crumb-text` | Ancestor crumb text (truncated) |
| `.header-trail .crumb-separator` | `›` character between crumbs |
| `.reveal .progress span` | Progress bar fill |
| `.reveal .controls` | Navigation arrows |
| `blockquote.info/warning/tip` | Callout boxes from blockquote_processor |
| `.image-overlay` | Lightbox (injected by JS on img click) |

---

## Slide splitting — critical invariant

**The slide separator must match only whole lines.**

`presentation_generator.py:_build_slides` uses:

```python
sep_pattern = r"(?m)^\s*" + re.escape(config.slide_separator) + r"\s*$"
raw_slides = re.split(sep_pattern, md_content)
```

**Never replace this with `str.split()`.**
`str.split("---")` also matches `---` inside table separator rows like `| --- | --- |`,
splitting the table and producing broken HTML. This was a confirmed bug, now fixed.

---

## Callout boxes

`blockquote_processor.py` detects the first `[tag]` token in a blockquote's first `<p>`:

```markdown
> [info] This is an info box.
> [warning] Be careful.
> [tip] Here is a tip.
```

It strips the tag token from the text and adds the class (`info`, `warning`, `tip`) to
the `<blockquote>` element. Themes style these via `blockquote.info`, etc.

---

## GUI (app.py)

- `python app.py` — opens window, immediately shows a folder dialog.
- Left panel: `Listbox` of `*.md` files. Double-click = generate.
- Right panel: scrollable config form (all `PresentationConfig` fields).
- Bottom bar: `⚡ Generate & Open` button + status label.
- Generation runs in a daemon `threading.Thread`; UI callbacks via `self.after(0, ...)`.
- Always uses `output_in_md_dir = "false"` (temp dir).
- Custom theme `"(none)"` → `custom_theme = None`.

---

## Running tests

```bash
python -m pytest tests/test_processors.py -v
```

50 tests, all must pass before committing. Test classes:

- `TestBlockquoteProcessor` — callout class injection
- `TestFragmentProcessor` — `.fragment` on `<li>`
- `TestBreadcrumbProcessor` — heading context propagation
- `TestMarkdownParser` — MD → HTML element checks
- `TestSlideTableSplitting` — regression for table/separator conflict
- `TestImageProcessor` — local copy, src rewrite, lightbox attr
- `TestConfigLoader` — `.properties` parsing, defaults, bool properties

---

## Running the CLI

```bash
# Single file
python main.py examples/demo_presentation.md

# All .md files in a folder
python main.py examples/
```

Output goes to `%TEMP%\<tmpXXX>\presentation.html` (default) or next to the
source file when `output_in_md_dir=true` in `config.properties`.

---

## Key invariants — never break these

1. `marp_to_reveal.py` — legacy file, do not touch.
2. `templates/reveal_template.html` — DOM structure must stay intact. JS breadcrumb,
   fragment stabilizer, lightbox, and auto-resize all depend on it.
3. `src/` public interfaces — `SlideProcessor.process(soup, context)`,
   `PresentationGenerator.generate(md_file, config)`. Don't change signatures.
4. Slide separator split — always whole-line regex, never `str.split()`.
5. Themes — never add CSS rules that target shared JS-managed IDs (`#header-trail`
   is the only one). Style via classes only.
6. No new external dependencies without updating `requirements.txt`.

---

## Workflow conventions

- Branch: feature work happens on `multi-screen-size`; PRs target `main`.
- Commit style: `type: short description` (feat / fix / refactor / test / docs).
- Co-author line: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.
- Tests must be green before every commit.
