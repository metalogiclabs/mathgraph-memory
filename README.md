# MathGraph Memory — AML open-method prototype

Source for a SQLite-backed, API-key-protected Add/Search memory prototype targeting the [2026 Agent Memory Challenge](https://agentmemoryleaderboard.ai/competition/).

## Status (22 October 2026)

- Full v12 Python source tree and test suite published in this repository.
- 50/50 Python unit tests passed locally on the source archive prior to publication.
- GitHub Actions is configured to run the suite; check its actual result before claiming a CI qualification.
- A public hosted API and official AML Smoke/Full evaluation are **not** verified.
- The attempted Render creation returned `402 billing_suspended`. **Do not submit** an undeployed URL.
- The current Dockerfile defaults to `MEMORY_DB=/data/memory.sqlite3` and requires an external persistent disk mounted at `/data` to preserve memories across restarts.

## Run locally

```sh
python -m unittest discover -q
MEMORY_API_KEY=replace-with-strong-random-key MEMORY_DB=./memory.sqlite3 MEMORY_RANKER=indexed python app.py
```

Routes: `GET /health`, authenticated `POST /add` and `POST /search`.

### Docker

```sh
docker build -t mathgraph-memory .
mkdir -p local-memory
docker run --rm -p 8080:8080 -v "$PWD/local-memory:/data" -e MEMORY_API_KEY=replace-with-random-key mathgraph-memory
```

Do not publicly expose the service without a strong secret, HTTPS, rate-limiting, durable storage, and an official protocol smoke test.

## Experimental components

- `indexed.py`: FTS5 lexical candidate generation
- `hybrid.py`: optional vector and lexical rank fusion; no production semantic provider qualified
- `trusted_evidence.py` and related modules: bounded GitHub status authority experiments
- `test_*.py`: local regression cases

## Verification boundary

Local unit tests do not demonstrate superior independent retrieval, coding-task resolution, production resilience, or an official AML score. Evidence-authority features are experimental and should not be represented as independent source-verification of arbitrary user statements.

## Submission checklist

- [x] Public source repository
- [x] Local unit suite (50/50 on release archive)
- [ ] Confirm green GitHub Actions run on the pinned source commit
- [ ] Public API with persistent storage
- [ ] Real provider and competition-protocol compatibility check
- [ ] Official Smoke and Full evaluation
