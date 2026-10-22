"""Incremental per-user SQLite FTS5 retrieval; safe and bounded candidate lookup.

This module is lexical, not an embedding model. Optional dense retrieval is not
claimed or enabled. Index rows share the authoritative memory table rowid.
"""
import re, sqlite3
from collections import Counter

TOKEN = re.compile(r'\w+', re.UNICODE)

def ensure_index(conn):
    conn.execute('CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(content, content="memories", content_rowid="rowid", tokenize="unicode61")')
    conn.executescript('''
    CREATE TRIGGER IF NOT EXISTS memory_fts_ai AFTER INSERT ON memories BEGIN
      INSERT INTO memory_fts(rowid,content) VALUES (new.rowid,new.content);
    END;
    CREATE TRIGGER IF NOT EXISTS memory_fts_ad AFTER DELETE ON memories BEGIN
      INSERT INTO memory_fts(memory_fts,rowid,content) VALUES('delete',old.rowid,old.content);
    END;
    CREATE TRIGGER IF NOT EXISTS memory_fts_au AFTER UPDATE ON memories BEGIN
      INSERT INTO memory_fts(memory_fts,rowid,content) VALUES('delete',old.rowid,old.content);
      INSERT INTO memory_fts(rowid,content) VALUES(new.rowid,new.content);
    END;
    ''')
    # A one-time migration from pre-index databases. No per-request full scan.
    conn.execute('CREATE TABLE IF NOT EXISTS index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    if not conn.execute("SELECT 1 FROM index_meta WHERE key='fts_rebuilt_v1'").fetchone():
        conn.execute("INSERT INTO memory_fts(memory_fts) VALUES('rebuild')")
        conn.execute("INSERT INTO index_meta VALUES('fts_rebuilt_v1','1')")

def candidates(conn, uid, query, limit=160):
    """Return candidate rows and normalized lexical score, stable over ties.

    Empty/out-of-vocabulary queries deliberately return [] instead of leaking
    another user's content or doing a full-table fallback.
    """
    terms=list(dict.fromkeys(t.lower() for t in TOKEN.findall(query) if len(t)>1))[:40]
    if not terms: return []
    expression=' OR '.join('"'+t.replace('"','""')+'"' for t in terms)
    try:
        rows=conn.execute('''SELECT m.id,m.content,m.created_at,bm25(memory_fts) as rank
        FROM memory_fts JOIN memories m ON m.rowid=memory_fts.rowid
        WHERE memory_fts MATCH ? AND m.user_id=?
        ORDER BY rank ASC,m.id ASC LIMIT ?''',(expression,uid,min(max(1,limit),1000))).fetchall()
    except sqlite3.OperationalError as e:
        raise ValueError('invalid search query') from e
    return [(dict(id=r[0],content=r[1],created_at=r[2]), 1/(1+max(0,-float(r[3])))) for r in rows]