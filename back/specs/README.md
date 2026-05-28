# ARHIAX Dx Specs

This folder contains the packaged governance contract for the ARHIAX Dx Agent.

Files:

- `agent_identity.json`: immutable identity and operating window
- `tool_catalog.json`: closed list of governed tools
- `data_scopes.json`: allowed data scopes and retention limits
- `operation_catalog.json`: allowed runtime operations
- `autonomy_profile.json`: autonomy model and promotion rules
- `policy_matrix.json`: policy bundles and mapped rule IDs
- `model_strategy.json`: primary/fallback routing for packaged model stages
- `bbr_baseline.json`: behavioral baseline metrics for drift and promotion checks

These specs are versioned artifacts. They are intended to be reviewed by client architecture, compliance, and audit teams.
