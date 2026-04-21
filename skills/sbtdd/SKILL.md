---
name: sbtdd
description: >
  SBTDD + Superpowers multi-agent workflow orchestrator. Use when working on a
  project that follows the SBTDD methodology (Spec + Behavior + Test Driven
  Development) and needs to execute one of the nine workflow operations:
  init, spec, close-phase, close-task, status, pre-merge, finalize, auto,
  resume. Trigger phrases: "sbtdd init", "sbtdd close phase", "advance TDD
  phase", "run pre-merge review", "finalize SBTDD plan", "sbtdd auto",
  "shoot-and-forget SBTDD run", "resume SBTDD", "sbtdd resume", "continue
  interrupted SBTDD session", or any "/sbtdd <subcommand>" invocation. NOT
  suitable for projects that do not use SBTDD -- only invoke when the project
  has `sbtdd/spec-behavior-base.md` or `.claude/plugin.local.md` with `stack` set.
---

# SBTDD Workflow -- Spec + Behavior + Test Driven Development Orchestrator

<!-- SKELETON: Tasks 2-4 populate the seven mandated sections (Overview,
     Subcommand dispatch, Complexity gate, Execution pipeline, sbtdd-rules,
     sbtdd-tdd-cycle, Fallback). This comment is a **skeleton sentinel**
     that is rejected by `test_skill_has_no_skeleton_sentinel` (added in
     Task 2 alongside sentinel removal, per Caspar iter 3 fix) so that the
     Milestone E ship cannot silently land with an empty body. -->
