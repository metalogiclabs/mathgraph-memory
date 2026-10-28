# AML 2026 hosted preflight — design

## Intent

Qualify the existing MathGraph Memory v12 Textual Add/Search system for the 2026 Agent Memory Challenge before the submission-materials cutoff. The immediate residual is a reachable, durable, authenticated API that can pass official Smoke. Do not infer a public score from local tests.

## Approaches

1. **Render Blueprint, Docker web service, attached SQLite disk (selected provisional path).** Reuses the released implementation, records infrastructure in source control, and keeps persistent storage. Requires a paid service/disk and explicit workspace and billing confirmation.
2. Render manual/direct service creation followed by manual disk attachment. Potentially quick but weakly reproducible, and easy to omit a required storage or secret setting.
3. Rewrite for an external managed datastore or serverless platform. Better potential horizontal scale, but changes the core and verification boundary under an imminent deadline.

## Scope

- Target Textual track and Open-source Methods division. Source remains the full public Python implementation, with fixed commit and exact external Add/Search versions.
- Use the existing Dockerfile and HTTP routes; no model or retrieval-policy changes during hosting preflight.
- Mount SQLite at `/data`, use an HTTPS public Render URL, and configure the API key as a secret outside Git. Prefer one web-service instance because Render disks do not support horizontal scaling.
- Enable `/health` and deploy only after CI success. Keep additional preview environments disabled to avoid unintentional charges.
- Treat disk capacity, concurrency, latency, official acceptance, competition score, and cost as UNKNOWN until independently measured.
- Do not commit any AML Eval Key or Memory System Key. The latter must be supplied privately to AML. No user data or private evaluation traces are published.

## Acceptance and stop conditions

1. Published release commit and its CI result are pinned; local Python test suite and black-box HTTP Smoke pass.
2. Render YAML is validated against the current Blueprint schema; a remote service is **not** created until the user confirms the Render workspace and paid-resource budget.
3. Live service must show expected version, successful authenticated Add/Search across a restart, and isolation across user IDs on persistent storage.
4. Official AML Smoke must pass using the issued Eval Key; only then consider Full. The Full gate requires quantified capacity and version/attribution disclosures.
5. Stop and report on any billing suspension, missing credential, official protocol rejection, failed capacity check, or material cost increase. A failed or absent official run remains UNKNOWN, not a submitted entry.
