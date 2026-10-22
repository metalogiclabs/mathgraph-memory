# MathGraph Memory

Evidence-aware agent memory research prototype for the [Agent Memory Leaderboard](https://agentmemoryleaderboard.ai/competition/).

## Release state (22 October 2026)

The **v12 local release candidate** has 50 passing Python unit tests. The full source archive is not yet committed to this repository. Until it is, **do not treat this repository as deployable or competition-submitted**.

Prototype functionality in the local release:
- HTTP Add/Search service with API-key authentication and user-scoped SQLite storage
- FTS5 indexed lexical retrieval
- Optional dense-vector reciprocal-rank fusion (provider and scale unqualified)
- Explicit temporal and GitHub source-authority diagnostics
- Local regression and HTTP smoke tests

### Verification boundary

The 50 local unit tests do not establish accuracy on independent coding histories, the official AML benchmark, production durability, or successful Render deployment. No public API endpoint or leaderboard result is claimed.

## Publication checklist

- [ ] Commit the exact v12 release source files and Dockerfile
- [ ] Verify local tests match the pinned commit
- [ ] Enable GitHub Actions regression tests
- [ ] Configure Render persistent storage and API secret
- [ ] Verify real public HTTP Add/Search endpoints
- [ ] Run official AML Smoke, then Full if qualified

No credentials, API keys, raw memory database, or personal research data should be committed.
