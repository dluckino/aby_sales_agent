import sqlite3

DB_PATH = "chat.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                name TEXT,
                email TEXT NOT NULL,
                phone TEXT,
                product_interest TEXT,
                question TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
        """)


def save_message(session_id, role, content):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )

def save_lead(session_id, email, question, name=None, phone=None, product_interest=None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO leads (session_id, email, question, name, phone, product_interest) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, email, question, name, phone, product_interest)
        )


def get_history(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,)
        ).fetchall()
    return [{"role": role, "content": content} for role, content in rows]