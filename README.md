# Marp to Reveal.js Wrapper

This project converts **Markdown presentations (Marp style)** into **Reveal.js** HTML presentations.
It supports advanced features such as:

* ✅ **Customizable configuration** via `config.properties`
* ✅ **External HTML template** with Jinja2 rendering
* ✅ **Image handling** (copies images and preserves folder structure)
* ✅ **Breadcrumb navigation**
* ✅ **Fragments** for progressive bullet display
* ✅ **Tables** rendered from Markdown
* ✅ **Math equations** using MathJax
* ✅ **Syntax highlighting** with support for line highlighting (`[2|4-6]`)
* ✅ **Step-by-step code focus** via Reveal.js `code-focus` plugin
* ✅ **Highlight.js themes** loaded from CDN or local fallback
* ✅ Project modular structure for easy customization

---

## 📂 Project Structure

```
marp-to-reveal/
│
├── marp_to_reveal.py             # Main script
├── config.properties             # Configuration file
├── templates/
│   └── reveal_template.html      # HTML template for Reveal.js
├── utils/
│   ├── __init__.py
│   └── config_loader.py          # Utility to load configurations
├── requirements.txt
└── README.md
```

---

## ⚙️ Configuration (`config.properties`)

The `config.properties` file defines all presentation settings:

```properties
# Reveal.js configuration
reveal_version=4.6.0
theme=white
transition=fade
slide_separator=---
reveal_cdn=https://cdnjs.cloudflare.com/ajax/libs/reveal.js

# Controls
enable_progress=true
enable_controls=true
enable_history=true
align_center=true

# Dimensions
width=960
height=700
margin=0.1
min_scale=0.2
max_scale=2.0

# Features
enable_fragments=true
show_header_trail=true

# Highlight.js theme (examples: monokai, atom-one-light, dracula, github)
highlight_theme=atom-one-light
enable_code_focus=true

# Fonts
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

You can change any value without modifying the Python code.

---

## 🖥 Requirements

Install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Contents of `requirements.txt`:

```
markdown-it-py
beautifulsoup4
jinja2
```

---

## 🚀 Usage

### 1. Prepare your Markdown presentation

Example `presentation.md`:

````markdown
# Welcome

This is a simple presentation.

---

## Math Example

$$ f(x) = a + b $$

---

## Code Example

```java [2|4-6]
class Calculator {
    int screen;

    void add(int a, int b) {
        screen = a + b;
    }
}
````

---

## Images

![Logo](images/logo.png)

````

---

### 2. Run the script
Execute the converter:

```bash
python marp_to_reveal.py presentation.md
````

The script will:

1. Parse your Markdown file.
2. Generate an HTML Reveal.js presentation.
3. Copy images into a temporary directory.
4. Open the presentation automatically in your browser.

---

## 🖌 Syntax Highlighting Themes

You can configure `highlight_theme` in `config.properties`:

| Category  | Themes                                                            |
| --------- | ----------------------------------------------------------------- |
| **Light** | `atom-one-light`, `github`, `vs`, `xcode`, `googlecode`           |
| **Dark**  | `monokai`, `dracula`, `atom-one-dark`, `vs2015`, `solarized-dark` |

Example:

```properties
highlight_theme=dracula
```

If the theme is not `monokai`, it will be loaded from the official Highlight.js CDN.

---

## ➕ Features

### Fragments

Lists automatically support fragments:

```markdown
- Item 1
- Item 2
- Item 3
```

Each bullet point appears on click.

---

### Breadcrumb Navigation

Each slide displays a breadcrumb trail (hierarchical titles) at the top-left corner, based on the heading levels.

---

### Math Support

MathJax is included:

```markdown
$$
E = mc^2
$$
```

---

### Line Highlighting

Highlight specific lines in code blocks:

````markdown
    ```python [2|4-6]
    print("Line 1")
    print("Line 2")
    print("Line 3")
    print("Line 4")
    ````
````

### Code Focus Plugin

Enable the official `code-focus` plugin to step through highlighted lines. Set `enable_code_focus=true` in `config.properties` and use bracket notation to define each step:

```java [2|4-6]
class Calculator {
    int screen;

    void add(int a, int b) {
        screen = a + b;
    }
}
```


---

## 🛠 Development

### Modify the template
The `templates/reveal_template.html` file controls the HTML output.  
You can edit it to:
- Add new plugins
- Change styles
- Modify structure

### Add more configuration
Update `config.properties` and pass variables into the Jinja2 template in `marp_to_reveal.py`.

---

## 📌 Notes

- Presentations are generated in a **temporary directory** and opened in the default browser.
- All assets (images) are copied automatically.
- You can export the final HTML from the temp folder if you want to host it.

---

## 🏆 License
This project is licensed under the MIT License.

---
