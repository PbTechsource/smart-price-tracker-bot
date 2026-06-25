import sqlite3
from datetime import datetime

DB_PATH = "price_tracker.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            available INTEGER DEFAULT 1,
            tracked_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)

    conn.commit()
    conn.close()


# ─── Products ───────────────────────────────────────────────

def add_product(user_id: int, name: str, url: str, source: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (user_id, name, url, source) VALUES (?, ?, ?, ?)",
        (user_id, name, url, source)
    )
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return product_id


def get_user_products(user_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM products WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_product(product_id: int, user_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM products WHERE id = ? AND user_id = ?",
        (product_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Price History ───────────────────────────────────────────

def save_price(product_id: int, price: int, available: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO price_history (product_id, price, available) VALUES (?, ?, ?)",
        (product_id, price, int(available))
    )
    conn.commit()
    conn.close()


def get_price_history(product_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM price_history WHERE product_id = ? ORDER BY tracked_at ASC",
        (product_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
