# MathGraph Memory · AML 2026 Cloudflare Free preflight

Status: **Cloudflare-hosted compatibility candidate**, not a warranted official score.

This is a deliberate, inspectable port of the Python prototype's AML HTTP
contract and its `indexed.py` retrieval idea to Cloudflare Workers + D1.
It stores Textual/Coding strings durably and retrieves with SQLite FTS5 `bm25`.
It **does not** implement the Python prototype's default lineage reranker,
embeddings, multimodal inputs, or answer generation. It must be submitted as a
distinct version, with that method difference disclosed. The platform owns
Answer and Eval.

## Deployment (no paid plan required for a bounded Smoke)

- D1 database: `mathgraph_aml_textual_2026` (APAC)
- Worker: `mathgraph-aml-textual-2026`
- The `MEMORY_API_KEY` secret is configured at the Worker level, not in Git.
- Public health: `GET /health` (no auth).
- Authenticated `POST /add`, `POST /search` using `X-Api-Key`, `Bearer`, or `Token`.
- Apply `schema.sql` with `wrangler d1 execute mathgraph_aml_textual_2026 --file=./schema.sql --remote`.
- Deploy with `wrangler deploy` after creating the D1 database, setting the
  secret with `wrangler secret put MEMORY_API_KEY`, and authenticating Wrangler.
- A 03:00 UTC scheduled handler deletes ingestion data older than 25 days
  (including FTS entries via SQLite triggers). This addresses the competition's
  30-day deletion boundary without using source-provided timestamps.

## Checks

Run `node test/worker.test.mjs` from the `cloudflare` directory. Tests use
Node.js 24's native SQLite/FTS5 database and a small D1 adapter; these test
actual SQL query behavior but not Cloudflare deployment behavior. Remote
`GET /health` and an authenticated remote Add/Search probe are required before
calling the hosted preflight passed. Official AML Smoke must still be run on
the competition platform separately; local/remote synthetic probes are not
official results.

## Free-tier blockers (2026-10-28)

- Workers Free: 100,000 HTTP requests/day; 10ms CPU/request.
- D1 Free: 5 million rows read/day, 100,000 rows written/day, 500MB per DB,
  5GB total and up to 10 DBs. Quota exhaustion hard-stops queries until reset.
- This adapter does not silently truncate payloads; it returns 413 if a single
  message exceeds its safe D1 row size or if an Add call contains over 500
  messages. The latter is well above AML's documented Textual chunk size.
- **Full remains UNKNOWN**: ~6,000 instances and ~300M tokens for the Textual
  track can exceed these free limits. Sharding, lifecycle and load tests would
  have to prove otherwise. Do not file a capacity representation claiming Full
  support based on a Smoke pass.
- Coding and multimodal Full are not claimed. No spending or plan upgrade is
  authorized by this project.

Official references:

- https://agentmemoryleaderboard.ai/competition/
- https://agentmemoryleaderboard.ai/api-guide
- https://developers.cloudflare.com/d1/platform/limits/
- https://developers.cloudflare.com/d1/platform/pricing/
- https://developers.cloudflare.com/workers/platform/limits/
