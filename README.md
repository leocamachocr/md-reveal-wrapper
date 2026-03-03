# md-reveal-wrapper

Converts **Markdown files** into self-contained **Reveal.js HTML presentations**, opened automatically in your browser.

---

## Features

- **Slide splitting** — use `---` as a separator (configurable, table-safe)
- **Multi-column grid layouts** — arrange content in 2, 3, or 4 columns per slide
- **Breadcrumb navigation** — heading hierarchy shown as a fixed trail at the top-left
- **Fragments** — list items appear one click at a time (optional)
- **Callout boxes** — `[info]`, `[warning]`, `[tip]` blockquote variants
- **Syntax highlighting** — Highlight.js with line-step support (`[2|4-6]`)
- **Math equations** — MathJax for inline (`\(…\)`) and block (`$$…$$`) math
- **Image handling** — local images are copied and `src` paths are rewritten
- **Image lightbox** — click any image to expand it fullscreen
- **Custom themes** — drop a `.css` file into `templates/themes/`, zero wiring
- **Configurable** — all settings in `config.properties`, no code changes needed

---

## Requirements

```bash
pip install -r requirements.txt
```

Python 3.9+ is required.

---

## Usage

### CLI

```bash
# Single file
python main.py presentation.md

# All .md files in a folder (opens each one)
python main.py examples/
```

The generated HTML is written to a temporary directory and opened in your default browser. Set `output_in_md_dir=true` in `config.properties` to write the HTML next to the source file instead.

### GUI

```bash
python app.py
```

A folder picker opens immediately. Select any folder containing `.md` files. The left panel lists them — double-click a file (or select it and click **Generate & Open**) to render and open the presentation. The right panel exposes all `config.properties` fields live.

---

## Project Structure

```
md-reveal-wrapper/
├── main.py                          CLI entry point — DI wiring only
├── app.py                           Tkinter desktop GUI
├── marp_to_reveal.py                Legacy script — do not modify
├── config.properties                Runtime configuration
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
│   │   ├── grid_processor.py        Multi-column grid layouts
│   │   ├── image_processor.py       Copy images, rewrite src attrs
│   │   ├── blockquote_processor.py  [info]/[warning]/[tip] callouts
│   │   ├── fragment_processor.py    .fragment on <li> elements
│   │   └── breadcrumb_processor.py  Heading context across slides
│   └── application/
│       ├── markdown_parser.py       MD → BeautifulSoup
│       ├── slide_processor_pipeline.py  Processor chain factory
│       └── presentation_generator.py    Orchestrates the full pipeline
│
├── templates/
│   ├── reveal_template.html         Jinja2 template
│   └── themes/                      CSS themes
│       ├── modern-idea-light.css    Default theme
│       └── ...
│
└── examples/
    ├── demo_presentation.md
    ├── grid-demo.md
    └── minimal-wide-serif-demo.md
```

---

## Configuration (`config.properties`)

```properties
# Reveal.js
reveal_version=4.6.0
reveal_cdn=https://cdnjs.cloudflare.com/ajax/libs/reveal.js
transition=fade
slide_separator=---

# Slide dimensions
width=1200
height=1080
margin=0.1
min_scale=0.6
max_scale=1.2

# Controls
enable_progress=true
enable_controls=true
enable_history=true
align_center=true

# Features
enable_fragments=true
show_header_trail=true

# Output
output_in_md_dir=true          # false = use temp dir (GUI always uses temp dir)
custom_theme=modern-idea-light.css

# Font scale
font_base=28px
font_h1=2.5em
font_h2=2em
font_h3=1.5em
font_h4=1.2em
font_h5=1em
font_h6=0.9em
font_p=1em
font_li=1em
```

---

## Markdown Syntax Guide

### Slides

Separate slides with `---` on its own line:

```markdown
# Slide 1

Content here.

---

## Slide 2

More content.
```

> **Note:** `---` inside Markdown table rows (e.g. `| --- |`) is never treated as a separator — only a whole line of `---` triggers a split.

---

### Grid layouts

Distribute content into **N equal columns** using HTML comments as delimiters and `-----` (5 dashes) as the column separator:

```markdown
<!-- $grid(N) -->

Column 1 content

-----

Column 2 content

<!-- $grid/ -->
```

- `<!-- $grid(N) -->` — opens a grid with **N** columns (any positive integer, typical values: 2, 3, 4)
- `-----` — separates grid items (5 dashes, distinct from the 3-dash slide separator)
- `<!-- $grid/ -->` — closes the grid block
- If `<!-- $grid/ -->` is missing the slide is left untouched (fail-safe)
- Each cell can contain any valid Markdown: headings, lists, tables, code blocks, callouts

**Two-column comparison:**

```markdown
## Approach comparison

<!-- $grid(2) -->

### Option A
- Fast to implement
- Simple API

-----

### Option B
- More flexible
- Better for large projects

<!-- $grid/ -->
```

**Three-column summary cards:**

```markdown
## Key metrics

<!-- $grid(3) -->

### Speed
Processing under **200 ms** for 100-slide decks.

-----

### Compatibility
Works on Chrome, Firefox, Safari, and Edge.

-----

### Extensibility
Add processors by subclassing `SlideProcessor`.

<!-- $grid/ -->
```

**Mixed content inside cells:**

```markdown
<!-- $grid(2) -->

### Reference table

| Separator | Use          |
|-----------|--------------|
| `---`     | Slide break  |
| `-----`   | Grid column  |

> [info] Separators do not collide — 3 vs 5 dashes.

-----

### Numbered list

1. First point
2. Second point
3. Third point

<!-- $grid/ -->
```

---

### Callout boxes

Add semantic callout boxes inside blockquotes:

```markdown
> [info] This is an informational note.

> [warning] Pay attention to this.

> [tip] Here is a useful tip.
```

The tag token (`[info]`, `[warning]`, `[tip]`) is stripped from the rendered text and the CSS class is applied to the `<blockquote>` element.

---

### Fragments

When `enable_fragments=true`, every list item (`<li>`) gets the `.fragment` class, so items appear one at a time on each keypress:

```markdown
- First point   ← appears on click 1
- Second point  ← appears on click 2
- Third point   ← appears on click 3
```

Disable globally with `enable_fragments=false` in `config.properties`.

---

### Breadcrumb navigation

A fixed trail at the top-left reflects the heading hierarchy across slides. Any heading (`#`, `##`, `###`) updates the breadcrumb for all subsequent slides until a new heading at the same level replaces it.

```markdown
# Chapter 1

## Introduction

### Overview

Content — breadcrumb shows: Chapter 1 › Introduction › Overview
```

Disable with `show_header_trail=false`.

---

### Math equations

Inline math:

```markdown
The formula is \( f(x) = ax^2 + bx + c \).
```

Block math:

```markdown
$$
E = mc^2
$$
```

---

### Syntax highlighting with line steps

Use bracket notation after the language tag to step through highlighted lines:

````markdown
```java [2|4-6]
class Calculator {
    int screen;

    void add(int a, int b) {
        screen = a + b;
    }
}
```
````

- `[2]` — highlight line 2
- `[4-6]` — highlight lines 4 through 6
- `[2|4-6]` — step: first line 2, then lines 4–6

---

### Images

Local images are copied into the output directory automatically. Paths are rewritten to point to the copied file:

```markdown
![Diagram](images/diagram.png)
```

Click any image in the presentation to open it in a fullscreen lightbox.

---

## Themes

Themes are plain CSS files in `templates/themes/`. To add a theme, drop a `.css` file there — it appears automatically in the GUI dropdown and is available via `config.properties`:

```properties
custom_theme=my-theme.css
```

Set `custom_theme=` (empty) to use the Reveal.js built-in styles only.

Included themes:

| File | Description |
|---|---|
| `modern-idea-light.css` | Default — clean light with accent colors |
| `minimal-light.css` | Minimal light |
| `minimal-dark.css` | Minimal dark |
| `minimal-wide-serif.css` | Wide layout with serif fonts |

---

## Running Tests

```bash
python -m pytest tests/test_processors.py -v
```

All 50 tests must pass before committing.

---

## License

MIT