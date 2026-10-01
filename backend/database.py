"""
JARVIS Database Module
SQLite database for conversations, messages, and long-term memory.
"""
import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "jarvis.db"
)


def get_connection():
    """Get a database connection with row factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize the database tables."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT DEFAULT 'Nueva conversación',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            source_conversation_id INTEGER,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (source_conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
    """)
    conn.commit()
    conn.close()


# ─── Conversations ───────────────────────────────────────────

def create_conversation(title: str = "Nueva conversación") -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO conversations (title) VALUES (?)", (title,)
    )
    conv_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return conv_id


def get_conversations():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_conversation(conv_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM conversations WHERE id = ?", (conv_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_conversation_title(conv_id: int, title: str):
    conn = get_connection()
    conn.execute(
        "UPDATE conversations SET title = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (title, conv_id),
    )
    conn.commit()
    conn.close()


def delete_conversation(conv_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()


# ─── Messages ────────────────────────────────────────────────

def add_message(conversation_id: int, role: str, content: str) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content),
    )
    conn.execute(
        "UPDATE conversations SET updated_at = datetime('now', 'localtime') WHERE id = ?",
        (conversation_id,),
    )
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return msg_id


def get_messages(conversation_id: int, limit: int = 50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
        (conversation_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Memories ────────────────────────────────────────────────

def add_memory(
    category: str, content: str, source_conversation_id: Optional[int] = None
) -> int:
    conn = get_connection()
    # Check if similar memory already exists
    existing = conn.execute(
        "SELECT id FROM memories WHERE category = ? AND content = ?",
        (category, content),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE memories SET updated_at = datetime('now', 'localtime') WHERE id = ?",
            (existing["id"],),
        )
        conn.commit()
        conn.close()
        return existing["id"]

    cursor = conn.execute(
        "INSERT INTO memories (category, content, source_conversation_id) VALUES (?, ?, ?)",
        (category, content, source_conversation_id),
    )
    mem_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return mem_id


def get_memories(category: Optional[str] = None):
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT * FROM memories WHERE category = ? ORDER BY updated_at DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY updated_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_memory(memory_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()


def search_memories(query: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM memories WHERE content LIKE ? ORDER BY updated_at DESC",
        (f"%{query}%",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
