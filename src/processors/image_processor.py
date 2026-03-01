import os
import shutil
from pathlib import Path

from bs4 import BeautifulSoup

from src.processors.base import SlideProcessor


class ImageProcessor(SlideProcessor):
    """
    Handles local image references in a slide:
      - copies the file to the assets directory
      - rewrites the src attribute to the relative assets path
      - adds data-preview-image to enable the lightbox on all images
    SRP: sole responsibility is image asset management.
    """

    def __init__(self, assets_dir: Path, md_base_path: Path) -> None:
        self._assets_dir = assets_dir
        self._md_base_path = md_base_path

    def process(self, soup: BeautifulSoup, context: dict) -> None:
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and not src.startswith(("http://", "https://", "data:")):
                abs_path = os.path.abspath(
                    os.path.join(str(self._md_base_path), src)
                )
                if os.path.exists(abs_path):
                    rel_path = os.path.normpath(src)
                    dest_path = os.path.join(str(self._assets_dir), rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy(abs_path, dest_path)
                    img["src"] = f"assets/{rel_path.replace(os.sep, '/')}"

            img["data-preview-image"] = ""  # enable lightbox for all images
