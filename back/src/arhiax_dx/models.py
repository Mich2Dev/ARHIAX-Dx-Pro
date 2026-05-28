"""Shared models for ARHIAX Dx requests, decisions, and certificates."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DecisionStatus(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    ALLOW_WITH_HIC_NOTIFICATION = "ALLOW_WITH_HIC_NOTIFICATION"


class RuleOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ESCALATE = "ESCALATE"
    LOG_ONLY = "LOG_ONLY"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MandateInput(BaseModel):
    organization_name: str
    domain: str
    subprocess: str
    size_org: str | None = None
    objective: str | None = None
    confidentiality: str = "Confidencial - Uso Estrategico"


class ClientContext(BaseModel):
    client_id: str
    legal_name: str
    authorized_boundary_id: str = "boundary-diagnostico-org"
    data_residency: str = "CO"
    contact_channel: str | None = None


class ProcessingProfile(BaseModel):
    store_raw_respondent_data: bool = False
    publish_report: bool = False
    issue_certificate: bool = True
    retention_days: int = Field(default=30, ge=1, le=365)


class DiagnosticRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    channel: str = "rest"
    requested_autonomy_level: str = "A1"
    mandate: MandateInput
    client: ClientContext
    requested_tools: list[str] = Field(default_factory=list)
    requested_operations: list[str] = Field(default_factory=list)
    requested_data_scopes: list[str] = Field(default_factory=list)
    processing_profile: ProcessingProfile = Field(default_factory=ProcessingProfile)
    simulation: dict[str, Any] = Field(default_factory=dict)


class CapabilityRecord(BaseModel):
    capability: str
    criticality: Severity
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any]
    payload_hash: str


class RuleResult(BaseModel):
    rule_id: str
    description: str
    outcome: RuleOutcome
    severity: Severity
    message: str


class GovernanceDecision(BaseModel):
    status: DecisionStatus
    reasons: list[str] = Field(default_factory=list)
    policy_bundles: list[str] = Field(default_factory=list)
    requires_human: bool = False


class GovernanceMetadata(BaseModel):
    agent_version: str
    governance_spec_version: str
    policy_bundle_version: str
    tool_catalog_version: str


class PlannedTool(BaseModel):
    name: str
    severity: Severity
    minimum_autonomy: str
    phase: str
    allowed: bool
    reason: str


class ExecutionPlan(BaseModel):
    pipeline_name: str
    execution_fingerprint: str
    execution_status: str
    requested_tools: list[str]
    planned_tools: list[PlannedTool]
    active_models: list[dict[str, Any]] = Field(default_factory=list)
    required_human_gates: list[str] = Field(default_factory=list)
    promotion_readiness: dict[str, Any] = Field(default_factory=dict)


class SignedCertificate(BaseModel):
    certificate_id: str
    issued_at: datetime
    execution_fingerprint: str
    decision: DecisionStatus
    policy_bundles: list[str]
    governance_metadata: GovernanceMetadata
    consulted_capabilities: list[dict[str, str]]
    rules: list[RuleResult]
    evidence_hash: str
    public_key_id: str
    signature: str


class DiagnosticResponse(BaseModel):
    request_id: str
    decision: GovernanceDecision
    execution_plan: ExecutionPlan
    certificate: SignedCertificate | None = None
    rule_results: list[RuleResult]
    human_review_required: bool = False
