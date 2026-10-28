/**
 * Cloudflare Workers + D1 adaptation of the open MathGraph Memory AML prototype.
 * Distinct method version: indexed FTS5/BM25 retrieval, not the Python lineage scorer.
 * No external inference, embeddings, or benchmark-specific answer generation.
 */

const MAX_TOP_K = 100;
const MAX_MESSAGES = 500; // D1 Free's 50-query per invocation bound; explicit 413 if exceeded.
const MAX_CONTENT_BYTES = 1_800_000; // Below the D1 2 MB SQLite row limit.
const INSERT_GROUP = 13; // 7 fields per memory + 3 idempotency guard params < 100.
const ENCODER = new TextEncoder();

function json(body, status = 200, headers = {}) {
  return Response.json(body, {
    status,
    headers: { 'Cache-Control': 'no-store', ...headers },
  });
}

class ClientError extends Error {
  constructor(detail, status = 422) {
    super(detail);
    this.status = status;
  }
}

function validId(x) { return typeof x === 'string' && x.length > 0; }

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

async function sha256(text) {
  const buf = await crypto.subtle.digest('SHA-256', ENCODER.encode(text));
  return [...new Uint8Array(buf)].map(x => x.toString(16).padStart(2, '0')).join('');
}

function createdAt(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const date = new Date(value);
    if (!Number.isNaN(date.valueOf())) return date.toISOString();
  }
  return new Date().toISOString();
}

function validateAdd(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new ClientError('expected JSON object');
  const { request_id: rid, user_id: uid, session_id: sid, messages } = payload;
  if (![rid, uid, sid].every(validId) || !Array.isArray(messages)) throw new ClientError('missing or invalid Add fields');
  if (messages.length > MAX_MESSAGES) throw new ClientError(`Add exceeds ${MAX_MESSAGES} messages per request`, 413);
  for (const m of messages) {
    if (!m || typeof m !== 'object' || !['user', 'assistant'].includes(m.role) ||
        typeof m.content !== 'string' || !m.content.trim()) throw new ClientError('invalid Add message');
    if (ENCODER.encode(m.content).length > MAX_CONTENT_BYTES) throw new ClientError('message exceeds D1 row size', 413);
  }
  return { rid, uid, sid, messages };
}

async function add(payload, db) {
  const { rid, uid, sid, messages } = validateAdd(payload);
  const digest = await sha256(canonicalJson(payload));
  const scopeHash = (await sha256(`${uid}\u0000${rid}`)).slice(0, 24);
  const batch = [db.prepare(`INSERT INTO requests(user_id, request_id, payload_hash)
    VALUES(?, ?, ?) ON CONFLICT(user_id, request_id) DO NOTHING`).bind(uid, rid, digest)];

  for (let start = 0; start < messages.length; start += INSERT_GROUP) {
    const chunk = messages.slice(start, start + INSERT_GROUP);
    const values = [];
    const binds = [];
    for (let offset = 0; offset < chunk.length; offset++) {
      const i = start + offset;
      values.push('(?, ?, ?, ?, ?, ?, ?)');
      binds.push(`${scopeHash}${i.toString(16).padStart(8, '0')}`, uid, sid, rid, i,
        chunk[offset].content, createdAt(chunk[offset].timestamp));
    }
    // The hash guard prevents a concurrent retry with a changed payload from
    // writing extra rows, even if its INSERT requests is ignored by the PK.
    const sql = `INSERT OR IGNORE INTO memories(id, user_id, session_id, request_id, ord, content, created_at)
      SELECT column1, column2, column3, column4, column5, column6, column7
      FROM (VALUES ${values.join(', ')})
      WHERE EXISTS (SELECT 1 FROM requests WHERE user_id=? AND request_id=? AND payload_hash=?)`;
    batch.push(db.prepare(sql).bind(...binds, uid, rid, digest));
  }
  await db.batch(batch); // D1 batch is a transaction; no 200 before persistence.
  const stored = await db.prepare('SELECT payload_hash FROM requests WHERE user_id=? AND request_id=?')
    .bind(uid, rid).first();
  if (!stored || stored.payload_hash !== digest) throw new ClientError('request_id reused for different payload');
  return { success: true, request_id: rid, user_id: uid, session_id: sid };
}

function validateSearch(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new ClientError('expected JSON object');
  const { user_id: uid, query, top_k: topK } = payload;
  if (!validId(uid) || typeof query !== 'string' || !Number.isInteger(topK) || topK < 0 || topK > MAX_TOP_K)
    throw new ClientError('invalid Search fields');
  return { uid, query, topK };
}

async function search(payload, db) {
  const { uid, query, topK } = validateSearch(payload);
  if (topK === 0) return { data: [] };
  // Quotes/parentheses/operators are never allowed to control FTS syntax.
  const terms = [...new Set((query.toLowerCase().match(/[\p{L}\p{N}_]+/gu) ?? [])
    .filter(t => t.length > 1))].slice(0, 40);
  if (!terms.length) return { data: [] };
  const ftsQuery = terms.map(t => `"${t.replaceAll('"', '""')}"`).join(' OR ');
  const result = await db.prepare(`SELECT m.id, m.content, m.created_at, bm25(memory_fts) AS relevance
    FROM memory_fts JOIN memories m ON m.rowid=memory_fts.rowid
    WHERE memory_fts MATCH ? AND m.user_id=?
    ORDER BY relevance ASC, m.id ASC LIMIT ?`).bind(ftsQuery, uid, topK).all();
  return { data: result.results.map(r => ({
    id: r.id, content: r.content, created_at: r.created_at,
    // SQLite BM25 sorts ascending (negative is better): flip sign so higher=better.
    score: Math.max(0, -Number(r.relevance)),
  })) };
}

function authenticated(request, key) {
  if (!key) return false;
  const header = request.headers;
  return header.get('X-Api-Key') === key ||
    header.get('Authorization') === `Bearer ${key}` ||
    header.get('Authorization') === `Token ${key}`;
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (request.method === 'GET' && path === '/health')
      return json({ status: env.DB && env.MEMORY_API_KEY ? 'ok' : 'unconfigured' }, env.DB && env.MEMORY_API_KEY ? 200 : 503);
    if (request.method !== 'POST' || !['/add', '/search'].includes(path)) return json({ detail: 'not found' }, 404);
    if (!env.DB || !env.MEMORY_API_KEY) return json({ detail: 'service not configured' }, 503);
    if (!authenticated(request, env.MEMORY_API_KEY)) return json({ detail: 'unauthorized' }, 401);
    try {
      let payload;
      try { payload = await request.json(); } catch { throw new ClientError('invalid JSON body', 400); }
      return json(path === '/add' ? await add(payload, env.DB) : await search(payload, env.DB));
    } catch (e) {
      if (e instanceof ClientError) return json({ detail: e.message }, e.status);
      // D1's Free plan hard-stops after its daily quotas. No silent fallback.
      if (/exceeded.*free tier|row (read|write) limit/i.test(String(e.message)))
        return json({ detail: 'D1 free-tier quota exceeded; retry after reset at midnight UTC' }, 429, { 'Retry-After': '60' });
      return json({ detail: 'internal storage error' }, 503);
    }
  },
  async scheduled(_event, env) {
    // AML requires evaluation data/derivatives erased within 30 days of a job.
    // Keep a five-day buffer; source timestamps are not ingestion timestamps.
    const cutoff = new Date(Date.now() - 25 * 24 * 60 * 60 * 1000).toISOString();
    await env.DB.prepare('DELETE FROM memories WHERE ingested_at < ?').bind(cutoff).run();
    await env.DB.prepare('DELETE FROM requests WHERE ingested_at < ?').bind(cutoff).run();
  },
};
