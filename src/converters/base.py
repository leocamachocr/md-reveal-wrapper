from abc import ABC, abstractmethod
from pathlib import Path


class PresentationConverter(ABC):
    """
    Abstract base for all presentation-to-Markdown converters.

    OCP: new format support is added by subclassing — no existing code touched.
    ISP: single method, single concern.
    DIP: convert.py depends on this abstraction, not on concrete converters.
    """

    @abstractmethod
    def convert(self, input_path: Path) -> str:
        """
        Convert a presentation file to md-reveal-wrapper Markdown.

        Args:
            input_path: Path to the source file (.pptx or .pdf).

        Returns:
            Full Markdown string for all slides, separated by '---'.
        """
