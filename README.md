# MathGraph Memory — AML open-method prototype

Source for a SQLite-backed, API-key-protected Add/Search memory prototype targeting the [2026 Agent Memory Challenge](https://agentmemoryleaderboard.ai/competition/).

## Cloudflare free-tier compatibility preflight (28 October 2026)

- Live public health URL: https://mathgraph-aml-textual-2026.metalogiclabs-check.workers.dev/health
- Live HTTPS `POST /add` and `POST /search` backed by D1 in APAC, protected by a dedicated Cloudflare Worker secret.
- A real-provider synthetic HTTP probe passed Add, immediate Search, `top_k`, user isolation, same-payload retry, changed-payload rejection, and unauthorized access rejection.
- The port is a **distinct experimental version** using FTS5/BM25 indexed retrieval. It is not the Python service's default lineage scorer. See [`cloudflare/README.md`](cloudflare/README.md) for code, tests, quota limits, and method disclosure.
- **No official AML Smoke or Full run has been made.** A successful synthetic provider probe is not an official result.
- Cloudflare Free D1 has hard storage/write quotas; ability to finish the approximately 300M-token Textual Full track is **UNKNOWN**. Do not claim Full capacity or submit a scored run without a decisive capacity check.
- The former paid Render deployment proposal is superseded by the user's **Cloudflare/Vercel, $0 hosting only** constraint. It should not be merged.

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
- [x] Green GitHub Actions run on the published baseline commit
- [x] Public Cloudflare API with D1 persistence (distinct FTS5 version)
- [x] Real provider synthetic Add/Search contract probe
- [ ] Verify Cloudflare free-tier capacity for Full
- [ ] Official Smoke and Full evaluation
