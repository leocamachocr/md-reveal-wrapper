# Minimal Wide Serif

## A typographic theme for md-reveal-wrapper

Designed for readability at any screen width.
No gradients · No decorative icons · No animations

---

# Typography

## Heading level 2

### Heading level 3

#### Heading level 4

##### Heading level 5

###### Heading level 6

Plain paragraph text set in a serif stack. The quick brown fox jumps over the lazy dog.
Line height is generous to support dense technical content without crowding.

---

## Lists

Unordered list with nested items:

- Readability comes first
- Contrast is achieved through weight and size, not color
  - Nested item A
  - Nested item B
    - Third level of nesting

Ordered list:

1. Choose a working directory
2. Select the Markdown file
3. Adjust settings in the config panel
4. Click **Generate & Open**

---

## Code

Inline code: `python main.py examples/` or `custom_theme = minimal-wide-serif.css`.

Block code with syntax highlighting:

```python
from src.infrastructure.config_loader import ConfigLoader
from src.infrastructure.resource_resolver import resolve_resource

config = ConfigLoader().load(resolve_resource("config.properties"))
print(config.custom_theme)
```

```java [2|5-7]
public class Presentation {
    private final String theme;

    public Presentation(String theme) {
        this.theme = theme;
    }
}
```

---

## Callout Boxes

> Standard blockquote — plain italic text, left-border only.

> [info] **Information** — This is an info callout.
> Use it for notes that add context without urgency.

> [warning] **Warning** — This is a warning callout.
> Highlight potential issues or required preconditions.

> [tip] **Tip** — This is a tip callout.
> Share shortcuts, best practices, or helpful patterns.

---

## Table

| Component                | File                          | Responsibility              |
|--------------------------|-------------------------------|-----------------------------|
| Config loader            | `config_loader.py`            | Parse `.properties` → dataclass |
| Presentation generator   | `presentation_generator.py`  | Orchestrate the pipeline    |
| Template renderer        | `template_renderer.py`        | Jinja2 → HTML               |
| File manager             | `file_manager.py`             | Output dirs, asset copying  |
| Breadcrumb processor     | `breadcrumb_processor.py`     | Heading context across slides |

---

# Programming

## Python

### Decorators

A decorator wraps a function to extend its behavior without modifying it:

```python
def log_call(fn):
    def wrapper(*args, **kwargs):
        print(f"Calling {fn.__name__}")
        return fn(*args, **kwargs)
    return wrapper

@log_call
def generate(path):
    ...
```

- **Transparent** — callers use the decorated function normally
- **Composable** — stack multiple decorators
- **Reusable** — apply to any function signature

---

## End of Demo

The **minimal-wide-serif** theme.

To use:
1. Open `app.py`
2. Set **Custom Theme** → `minimal-wide-serif.css`
3. Set **Reveal.js Theme** → `white` (or `simple`)
4. Click **Generate & Open**
