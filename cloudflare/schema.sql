-- Textual/Coding evidence only. The multimodal track is not implemented.
CREATE TABLE IF NOT EXISTS requests (
  user_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  ingested_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (user_id, request_id)
);
CREATE INDEX IF NOT EXISTS ix_requests_retention ON requests(ingested_at);

CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  request_id TEXT NOT NULL,
  ord INTEGER NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  ingested_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS ix_scope ON memories(user_id);
CREATE INDEX IF NOT EXISTS ix_memories_retention ON memories(ingested_at);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
  content, content='memories', content_rowid='rowid', tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS memory_fts_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memory_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER IF NOT EXISTS memory_fts_ad AFTER DELETE ON memories BEGIN
  INSERT INTO memory_fts(memory_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
END;
CREATE TRIGGER IF NOT EXISTS memory_fts_au AFTER UPDATE ON memories BEGIN
  INSERT INTO memory_fts(memory_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
  INSERT INTO memory_fts(rowid, content) VALUES (new.rowid, new.content);
END;
