import os
import sys
from pathlib import Path


def resolve_resource(relative_path: str) -> str:
    """
    Resolve a resource path relative to the project root.
    Compatible with both normal execution and PyInstaller bundles.
    SRP: sole responsibility is path resolution across execution contexts.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        # __file__ lives at src/infrastructure/resource_resolver.py
        # parents[2] is the project root
        base_path = Path(__file__).parents[2]
    return str(base_path / relative_path)
