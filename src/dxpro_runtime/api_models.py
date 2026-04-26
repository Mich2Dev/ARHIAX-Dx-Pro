"""Pydantic request models for the DX Pro API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FlexiblePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class PmelPolicyRequest(FlexiblePayload):
    package: str
    input: dict[str, Any] = Field(default_factory=dict)
    subject: str = "pmel-runtime"
    trace_id: str | None = None


class PmelStepRequest(FlexiblePayload):
    subject: str = "pmel-runtime"
    step: str = "unspecified"
    input: dict[str, Any] = Field(default_factory=dict)
    packages: list[str] | None = None
    trace_id: str | None = None


class PmelCaptureRequest(FlexiblePayload):
    subject: str = "pmel-capture-agent"
    interview_text: str = ""
    trace_id: str | None = None


class DiagnosticEvaluateRequest(FlexiblePayload):
    request_id: str | None = None
    trace_id: str | None = None
    requested_autonomy_level: str = "A1"
    mandate: dict[str, Any] = Field(default_factory=dict)
    client: dict[str, Any] = Field(default_factory=dict)
    requested_tools: list[str] | None = None
    requested_operations: list[str] | None = None
    requested_data_scopes: list[str] | None = None
    processing_profile: dict[str, Any] = Field(default_factory=dict)
    simulation: dict[str, Any] = Field(default_factory=dict)
    pmel: dict[str, Any] = Field(default_factory=dict)


class CertificateVerifyRequest(BaseModel):
    certificate: dict[str, Any]
