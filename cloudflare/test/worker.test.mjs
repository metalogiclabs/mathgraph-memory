import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import worker from '../src/index.mjs';

const ddl = readFileSync(fileURLToPath(new URL('../schema.sql', import.meta.url)), 'utf8');

// Minimal D1 API backed by real SQLite + FTS5; the deployed binding is tested separately.
function db() {
  const sqlite = new DatabaseSync(':memory:');
  sqlite.exec(ddl);
  const prepare = sql => {
    const statement = sqlite.prepare(sql);
    return {
      bind(...args) {
        return {
          first: async () => statement.get(...args) ?? null,
          all: async () => ({ results: statement.all(...args) }),
          run: async () => ({ success: true, meta: { changes: statement.run(...args).changes } }),
          _run: () => { statement.run(...args); return []; },
        };
      },
    };
  };
  return {
    prepare,
    batch: async statements => {
      sqlite.exec('BEGIN');
      try {
        const results = statements.map(statement => ({ success: true, results: statement._run() }));
        sqlite.exec('COMMIT');
        return results;
      } catch (error) {
        sqlite.exec('ROLLBACK');
        throw error;
      }
    },
    count: () => sqlite.prepare('SELECT count(*) n FROM memories').get().n,
  };
}

function client(database = db()) {
  const env = { DB: database, MEMORY_API_KEY: 'test-secret' };
  async function get(path, headers = {}) {
    return worker.fetch(new Request(`https://test.example${path}`, { headers }), env);
  }
  async function post(path, body, headers = { 'X-Api-Key': 'test-secret' }) {
    const response = await worker.fetch(new Request(`https://test.example${path}`, {
      method: 'POST', headers, body: JSON.stringify(body),
    }), env);
    return [response.status, await response.json()];
  }
  return { get, post, db: database };
}

function add(userId = 'alice', requestId = 'r1', messages = [{ role: 'user', content: 'The blue kite is on the porch.' }]) {
  return { request_id: requestId, user_id: userId, session_id: 's1', messages };
}

function search(userId = 'alice', query = 'blue kite', topK = 100) {
  return { user_id: userId, query, top_k: topK };
}

test('public health, authorization, and strict paths', async () => {
  const c = client();
  assert.equal((await c.get('/health')).status, 200);
  assert.equal((await c.post('/add', add(), {}))[0], 401);
  assert.equal((await c.post('/wrong', add()))[0], 404);
  assert.equal((await c.post('/add', add(), { Authorization: 'Bearer test-secret' }))[0], 200);
});

test('synchronous Add, indexed Search, stable IDs, timestamps, and Top K', async () => {
  const c = client();
  const original = add('alice', 'r1', [
    { role: 'user', content: 'The blue kite is on the porch.', timestamp: 1704067200000 },
    { role: 'assistant', content: 'The red plane is in the garden.' },
  ]);
  assert.deepEqual(await c.post('/add', original), [200, {
    success: true, request_id: 'r1', user_id: 'alice', session_id: 's1',
  }]);
  const [status, body] = await c.post('/search', search());
  assert.equal(status, 200);
  assert.equal(body.data.length, 1);
  assert.equal(body.data[0].content, original.messages[0].content);
  assert.equal(body.data[0].created_at, '2024-01-01T00:00:00.000Z');
  assert.ok(typeof body.data[0].id === 'string' && body.data[0].id.length > 0);
  assert.ok(Number.isFinite(body.data[0].score));
  assert.deepEqual((await c.post('/search', search('alice', 'kite', 0)))[1], { data: [] });
});

test('Add is idempotent across JSON key order but rejects conflicting reuse', async () => {
  const c = client();
  const payload = add();
  assert.equal((await c.post('/add', payload))[0], 200);
  const same = { messages: [{ content: payload.messages[0].content, role: 'user' }], session_id: 's1', user_id: 'alice', request_id: 'r1' };
  assert.equal((await c.post('/add', same))[0], 200);
  assert.equal(c.db.count(), 1);
  assert.equal((await c.post('/add', add('alice', 'r1', [{ role: 'user', content: 'different' }])))[0], 422);
  assert.equal(c.db.count(), 1);
});

test('user_id prevents cross-user recall even with same request_id', async () => {
  const c = client();
  assert.equal((await c.post('/add', add('alice', 'same')))[0], 200);
  assert.equal((await c.post('/add', add('bob', 'same', [{ role: 'user', content: 'The orange comet.' }])))[0], 200);
  assert.deepEqual((await c.post('/search', search('bob', 'blue kite')))[1], { data: [] });
  assert.equal((await c.post('/search', search('bob', 'orange comet')))[1].data.length, 1);
  assert.equal((await c.post('/search', search('alice', 'orange comet')))[1].data.length, 0);
});

test('reject malformed Add/Search; do not throw on FTS special characters', async () => {
  const c = client();
  assert.equal((await c.post('/add', { ...add(), messages: [{ role: 'system', content: 'no' }] }))[0], 422);
  assert.equal((await c.post('/add', { ...add(), messages: [{ role: 'user', content: '   ' }] }))[0], 422);
  assert.equal((await c.post('/search', search('alice', 'abc', 101)))[0], 422);
  assert.equal((await c.post('/search', search('alice', 'abc', true)))[0], 422);
  assert.equal((await c.post('/search', { ...search(), query: ['image'] }))[0], 422);
  assert.equal((await c.post('/add', add()))[0], 200);
  assert.equal((await c.post('/search', search('alice', '" OR ) - * fts5:')))[0], 200);
  assert.deepEqual((await c.post('/search', search('alice', '****')))[1], { data: [] });
});

test('large but bounded request persists atomically', async () => {
  const c = client();
  const messages = Array.from({ length: 24 }, (_, i) => ({ role: 'user', content: `Galaxy event_${i} is visible` }));
  assert.equal((await c.post('/add', add('alice', 'large', messages)))[0], 200);
  assert.equal(c.db.count(), 24);
  assert.equal((await c.post('/search', search('alice', 'event_23')))[1].data.length >= 1, true);
});

test('oversized records fail explicitly and leave no partial writes', async () => {
  const c = client();
  assert.equal((await c.post('/add', add('alice', 'too-big', [{ role: 'user', content: 'X'.repeat(1_800_001) }])))[0], 413);
  assert.equal(c.db.count(), 0);
  assert.equal((await c.post('/add', add('alice', 'too-many', Array.from({ length: 501 }, () => ({ role: 'user', content: 'hi' })))))[0], 413);
  assert.equal(c.db.count(), 0);
});

test('scheduled retention removes expired data without confusing source timestamps', async () => {
  const c = client();
  assert.equal((await c.post('/add', add()))[0], 200);
  // New ingestions stay despite an arbitrary old source timestamp.
  await worker.scheduled({}, { DB: c.db });
  assert.equal(c.db.count(), 1);
  await c.db.prepare('UPDATE memories SET ingested_at=?').bind('2000-01-01T00:00:00.000Z').run();
  await c.db.prepare('UPDATE requests SET ingested_at=?').bind('2000-01-01T00:00:00.000Z').run();
  await worker.scheduled({}, { DB: c.db });
  assert.equal(c.db.count(), 0);
  assert.deepEqual((await c.post('/search', search()))[1], { data: [] });
  // The expired idempotency key is also removed, so clean reingestion works.
  assert.equal((await c.post('/add', add()))[0], 200);
});
