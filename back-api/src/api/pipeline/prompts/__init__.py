"""Prompts package — re-exports the public API."""
from .routing import MODEL_ROUTING, get_model_config
from .builder import TOOL_PROMPTS, build_prompt

__all__ = ["MODEL_ROUTING", "get_model_config", "TOOL_PROMPTS", "build_prompt"]
