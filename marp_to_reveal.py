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
import re

def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, compatible con PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def load_template(template_path):
    with open(template_path, "r", encoding="utf-8") as f:
        return Template(f.read())

def enable_code_line_numbers(md_parser):
    """Extiende MarkdownIt para soportar bloques con [x-y] para data-line-numbers."""
    default_fence = md_parser.renderer.rules.get("fence")

    def fence_with_line_numbers(tokens, idx, options, env):
        token = tokens[idx]
        info = token.info.strip()

        match = re.match(r"(\w+)\s*(?:\[(.+)\])?", info)
        if match:
            lang = match.group(1)
            lines = match.group(2)
            token.attrSet("class", f"language-{lang}")
            if lines:
                token.attrSet("data-line-numbers", lines)

        return default_fence(tokens, idx, options, env)

    md_parser.renderer.rules["fence"] = fence_with_line_numbers

def convert_markdown_to_reveal(md_content, assets_dir, md_base_path, config):
    md_parser = MarkdownIt("commonmark").enable("table")
    enable_code_line_numbers(md_parser)

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
            img["data-preview-image"] = ""  # Lightbox habilitado

        # Personalizar blockquotes según sintaxis [info], [warning], [tip]
        for blockquote in soup.find_all("blockquote"):
            text = blockquote.get_text(strip=True)
            match = re.match(r"\[(info|warning|tip)\]\s*(.*)", text, re.IGNORECASE)
            if match:
                tipo = match.group(1).lower()
                contenido = match.group(2)
                blockquote["class"] = blockquote.get("class", []) + [tipo]
                blockquote.clear()
                new_p = soup.new_tag("p")
                new_p.string = contenido
                blockquote.append(new_p)

        # Agregar clase fragment a listas si está habilitado
        if config.get("enable_fragments", "true").lower() == "true":
            for li in soup.find_all("li"):
                li["class"] = (li.get("class", []) + ["fragment"])

        # Breadcrumb
        first_heading = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if first_heading:
            level = int(first_heading.name[1])
            header_context[level] = first_heading.get_text()
            for k in list(header_context.keys()):
                if k > level:
                    del header_context[k]

        breadcrumb_text = " › ".join([header_context[i] for i in sorted(header_context.keys())]) if header_context else ""

        # Envolver todo el contenido de la slide en <div class="slide-content">
        wrapper = soup.new_tag("div", attrs={"class": "slide-content"})
        for element in soup.contents:
            wrapper.append(element.extract())
        soup.append(wrapper)

        slides_html.append(f"<section data-breadcrumb=\"{breadcrumb_text}\">{soup}</section>")
    return "\n".join(slides_html)

def generate_reveal_presentation(md_file, config):
    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    md_base_path = os.path.dirname(os.path.abspath(md_file))

    if config.get("output_in_md_dir", "false").lower() == "true":
        md_filename = Path(md_file).stem
        output_dir = os.path.join(md_base_path, f"md_reveal_{md_filename}")
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = tempfile.mkdtemp()

    assets_dir = os.path.join(output_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    slides_html = convert_markdown_to_reveal(md_content, assets_dir, md_base_path, config)

    # Copiar el tema personalizado si existe
    if "custom_theme" in config:
        custom_theme_src = resource_path(f"templates/themes/{config['custom_theme']}")
        custom_theme_dst = os.path.join(assets_dir, config['custom_theme'])
        shutil.copy(custom_theme_src, custom_theme_dst)

    template = load_template(resource_path("templates/reveal_template.html"))
    html_content = template.render(slides=slides_html, **config)

    output_file = Path(output_dir) / "presentation.html"
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

    config = load_config(resource_path("config.properties"))
    generate_reveal_presentation(md_file, config)

if __name__ == "__main__":
    main()
