# Agent Governance Spec

## Agent

- name: `ARHIAX-Dx-v1`
- version: `5.1.0`
- initial autonomy: `A1`
- max packaged autonomy: `A2`

## Purpose

Run a governed organizational diagnostics workflow that can design instruments, analyze responses, quantify bottlenecks, produce process redesign insights, and prepare executive reports.

## Explicit Non-Goals

- changing client systems
- making operational decisions for the client
- storing raw respondent data
- publishing reports without human approval

## Required Governance Outcomes

- `ALLOW`
- `DENY`
- `ESCALATE_TO_HUMAN`
- `ALLOW_WITH_HIC_NOTIFICATION`

## Hard Controls

- undeclared tools are denied
- undeclared operations are denied
- non-anonymized respondent handling is denied
- retention beyond 30 days is denied
- publication always escalates
- autonomy promotion requires metrics and human approval

## Human Governance

Human approval is mandatory for:

- final publication
- autonomy promotion to `A2`
- critical perception gaps
- low IRR follow-up
