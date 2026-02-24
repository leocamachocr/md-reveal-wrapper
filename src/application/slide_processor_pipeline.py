from abc import ABC, abstractmethod
from pathlib import Path

from src.domain.config import PresentationConfig
from src.processors.base import SlideProcessor
from src.processors.blockquote_processor import BlockquoteProcessor
from src.processors.breadcrumb_processor import BreadcrumbProcessor
from src.processors.fragment_processor import FragmentProcessor
from src.processors.image_processor import ImageProcessor


class SlideProcessorPipelineBase(ABC):
    """
    Abstract factory for building the ordered list of slide processors.

    OCP: the default pipeline can be extended or replaced by subclassing
         without touching PresentationGenerator.
    DIP: PresentationGenerator depends on this abstraction, not on concrete
         processor classes.
    """

    @abstractmethod
    def build(
        self,
        md_base_path: Path,
        assets_dir: Path,
        config: PresentationConfig,
    ) -> list[SlideProcessor]:
        """Return an ordered list of processors to apply to each slide."""


class DefaultSlideProcessorPipeline(SlideProcessorPipelineBase):
    """
    Builds the standard processor pipeline:
      1. ImageProcessor     — copy local images, rewrite src
      2. BlockquoteProcessor — style [info]/[warning]/[tip] callouts
      3. FragmentProcessor  — add .fragment to list items
      4. BreadcrumbProcessor — track heading context across slides
    """

    def build(
        self,
        md_base_path: Path,
        assets_dir: Path,
        config: PresentationConfig,
    ) -> list[SlideProcessor]:
        return [
            ImageProcessor(assets_dir, md_base_path),
            BlockquoteProcessor(),
            FragmentProcessor(enabled=config.fragments_enabled),
            BreadcrumbProcessor(),
        ]
