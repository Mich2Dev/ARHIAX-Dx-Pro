"""RGC research module: papers + patents → grounded hypothesis_pack."""

from .deep_contraster import DeepResearchContraster, verify_contrast_provenance
from .grey_sources import GreySourceClient
from .hypothesis_builder import HypothesisBuilder, build_hypothesis_pack
from .models import GreySource, Hypothesis, Paper, Patent, ResearchEvidence
from .sources import LensClient, OpenAlexClient

__all__ = [
    "DeepResearchContraster",
    "GreySource",
    "GreySourceClient",
    "Hypothesis",
    "HypothesisBuilder",
    "LensClient",
    "OpenAlexClient",
    "Paper",
    "Patent",
    "ResearchEvidence",
    "build_hypothesis_pack",
    "verify_contrast_provenance",
]
