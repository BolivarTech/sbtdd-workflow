---
stack: python
author: "Julian Bolivar"
error_type: null
verification_commands:
  - "pytest"
  - "ruff check ."
  - "ruff format --check ."
  - "mypy ."
plan_path: "planning/claude-plan-tdd.md"
plan_org_path: "planning/claude-plan-tdd-org.md"
spec_base_path: "sbtdd/spec-behavior-base.md"
spec_path: "sbtdd/spec-behavior.md"
state_file_path: ".claude/session-state.json"
magi_threshold: "GO_WITH_CAVEATS"
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 1
auto_max_spec_review_seconds: 3600
tdd_guard_enabled: true
worktree_policy: "optional"
---

# Test config for Python stack
