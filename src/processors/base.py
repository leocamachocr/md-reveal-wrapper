from abc import ABC, abstractmethod

from bs4 import BeautifulSoup


class SlideProcessor(ABC):
    """
    Abstract base for all slide post-processors.

    OCP: new processing behaviour is added by creating a new subclass,
         without modifying existing processors or the pipeline.
    ISP: the interface is minimal — one method, one concern.
    LSP: every subclass can replace this base transparently.
    DIP: high-level orchestration depends on this abstraction, not on
         concrete processors.
    """

    @abstractmethod
    def process(self, soup: BeautifulSoup, context: dict) -> None:
        """
        Mutate *soup* in-place and/or update shared *context*.

        Args:
            soup:    BeautifulSoup tree for the current slide.
            context: Mutable dict shared across all slides in one run
                     (used for cross-slide state like breadcrumb tracking).
        """
