"""Pytest configuration and Hypothesis profiles for DX Pro test suite."""
from __future__ import annotations

from hypothesis import HealthCheck, settings

# CI profile: enough examples to catch regressions without being slow
settings.register_profile(
    "ci",
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)

# Fast profile for local dev
settings.register_profile(
    "dev",
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)

settings.load_profile("ci")
