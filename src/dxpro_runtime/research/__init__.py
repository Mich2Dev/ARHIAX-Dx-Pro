"""RGC research module: papers + patents → grounded hypothesis_pack."""

from .hypothesis_builder import HypothesisBuilder, build_hypothesis_pack
from .models import Hypothesis, Paper, Patent, ResearchEvidence
from .sources import LensClient, OpenAlexClient

__all__ = [
    "Hypothesis",
    "HypothesisBuilder",
    "LensClient",
    "OpenAlexClient",
    "Paper",
    "Patent",
    "ResearchEvidence",
    "build_hypothesis_pack",
]
