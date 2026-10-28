# AML Hosted Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare and, when authorized, qualify a durable publicly hosted Textual Add/Search API for AML Cycle 2.

**Architecture:** Keep the published Python Docker container unchanged. Declare a single Render web service with one persistent SQLite disk and a Dashboard-provided API key; qualify local and hosted requests before applying for an official evaluation.

**Tech Stack:** Python 3.12 stdlib HTTP/SQLite/FTS5, Docker, Render Blueprint, AML Cycle 2 Add/Search.

**Spec:** `docs/superpowers/specs/2026-10-28-aml-hosted-preflight-design.md`

## Global Constraints

- Never put keys, private evaluation traces, or sensitive user data in Git.
- Textual track only; do not claim Multimodal support or official scoring.
- Materials due 2026-10-31 23:59 UTC+8; evaluations stop 2026-11-04 23:59 UTC+8.
- Do not provision paid resources until the workspace and cost are confirmed.
- No unverified deployment URL may be sent to AML.

## Review Focus

- Render disk absent: process must not be represented as durable.
- Secret unset: app must refuse production startup; never use the insecure local override.
- Restart after Add: Search must recover the same user-scoped memory.
- Authentication failure: 401; tenant-crossing Search: zero results.
- Full evaluation volume: choose capacity based on observed load, not the tiny local test suite.

---

### Task 1: Reproducible Render configuration

**Files:** Create `render.yaml`; preserve `Dockerfile` and `app.py`.

**Interfaces:** Dockerfile exposes port 8080 and starts `python app.py`; `MEMORY_DB` targets `/data/memory.sqlite3`; `MEMORY_API_KEY` is a private environment variable.

- [ ] Write the minimal one-service Blueprint with a Singapore region, health check, explicit disk, and dashboard-provided secret.
- [ ] Parse YAML and validate against current Render Blueprint schema/CLI if accessible.
- [ ] Review diff for secret exposure, unexpected resources, and autoscaling or preview settings.
- [ ] Commit the change on a branch, without applying the Blueprint.

### Task 2: Pin local release evidence

**Files:** Existing `test_*.py`, `release_smoke.py`, GitHub Actions workflow.

**Interfaces:** `python -m unittest discover -v`; `python release_smoke.py`.

- [x] Run all 50 unit tests on `c08e0605`; 50/50 PASS on 2026-10-28 (local).
- [x] Run the packaged HTTP Smoke; startup, Add/Search, indexed retrieval and isolation PASS.
- [x] Verify upstream Actions run `39721463948` SUCCESS on exact SHA `c08e0605d0a7716d550b5f49a02ab4f07c6c1f93`.
- [ ] Once the Blueprint changes the source SHA, rerun tests/CI on that exact new head before deployment.

### Task 3: Live hosted gate — blocked pending authorization

**Files:** No source changes anticipated.

**Interfaces:** Public HTTPS `/health`, authenticated `/add` and `/search`, persistent `/data` disk.

- [ ] Confirm Render workspace and permission to incur paid service/disk costs.
- [ ] Resolve any Render billing suspension and configure the API secret through the Dashboard.
- [ ] Apply Blueprint, observe the specific deploy ID reach `live`, and verify runtime logs.
- [ ] Add a unique test memory, restart/redeploy, then retrieve it under the same user and fail closed for another user.
- [ ] Measure request latency, concurrency, disk growth and capacity headroom on representative public-safe synthetic loads.

### Task 4: AML official evaluation gate — not started

**Files:** Run identifiers and evidence receipts stay private; publish only non-sensitive version metadata.

**Interfaces:** Official AML Evaluation access request and Textual Smoke, then Full.

- [ ] Apply for/bind the official Eval Key with fixed version, public commit, endpoints, auth and capacity declaration.
- [ ] Complete AML Textual Smoke; record success/error Run ID privately.
- [ ] Perform the eight-point Full safety and capacity checklist. If unsupported, hold Full.
- [ ] Start Full with one frozen version sufficiently before the evaluation-close date; track the official job to completion and review.
