import os
import sys
import tempfile
import webbrowser
import shutil
from pathlib import Path
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from utils.config_loader import load_config
from jinja2 import Template

def load_template(template_path):
    with open(template_path, "r", encoding="utf-8") as f:
        return Template(f.read())

def convert_markdown_to_reveal(md_content, assets_dir, md_base_path, config):
    md_parser = MarkdownIt("commonmark").enable("table")
    slides_md = md_content.split(config["slide_separator"])
    slides_html = []
    header_context = {}

    for slide in slides_md:
        html_content = md_parser.render(slide)
        soup = BeautifulSoup(html_content, "html.parser")

        # Procesar imágenes
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and not src.startswith(("http://", "https://", "data:")):
                abs_path = os.path.abspath(os.path.join(md_base_path, src))
                if os.path.exists(abs_path):
                    rel_path = os.path.normpath(src)
                    dest_path = os.path.join(assets_dir, rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy(abs_path, dest_path)
                    img["src"] = f"assets/{rel_path.replace(os.sep, '/')}"

        # Breadcrumb
        first_heading = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if first_heading:
            level = int(first_heading.name[1])
            header_context[level] = first_heading.get_text()
            for k in list(header_context.keys()):
                if k > level:
                    del header_context[k]

        breadcrumb_text = " › ".join([header_context[i] for i in sorted(header_context.keys())]) if header_context else ""
        slides_html.append(f"<section data-breadcrumb=\"{breadcrumb_text}\">{soup}</section>")
    return "\n".join(slides_html)

def generate_reveal_presentation(md_file, config):
    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    md_base_path = os.path.dirname(os.path.abspath(md_file))
    temp_dir = tempfile.mkdtemp()
    assets_dir = os.path.join(temp_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    slides_html = convert_markdown_to_reveal(md_content, assets_dir, md_base_path, config)

    template = load_template("templates/reveal_template.html")

    html_content = template.render(slides=slides_html, **config)

    output_file = Path(temp_dir) / "presentation.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Presentación generada en: {output_file}")
    webbrowser.open(f"file://{output_file}")

def main():
    if len(sys.argv) != 2:
        print("Uso: python marp_to_reveal.py archivo.md")
        sys.exit(1)

    md_file = sys.argv[1]
    if not os.path.isfile(md_file):
        print(f"Error: No se encontró el archivo {md_file}")
        sys.exit(1)

    config = load_config("config.properties")
    generate_reveal_presentation(md_file, config)

if __name__ == "__main__":
    main()
