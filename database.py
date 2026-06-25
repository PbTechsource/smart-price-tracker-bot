import sqlite3


DB_FILE = "products.db"


conn = sqlite3.connect("prducts.db", check_same_thread=False)
cursor = conn.cursor()



cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name  TEXT,
               url TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS prices (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               product_id INTEGER,
               price INTEGER,
               data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

def add_product(name: str, url: str):
    cursor.execute(
        f"INSERT INTO products (name, url) VALUES ('{name}', '{url}')"
    )
    conn.commit()

def get_products():
    cursor.execute("SELECT id, name, url FROM products")
    return cursor.fetchall()

def get_product_url(product_id: int):
    cursor.execute(f"SELECT url FROM products WHERE id={product_id}")
    row = cursor.fetchone()
    return row[0] if row else None

def add_price(product_id: int, price: int):
    cursor.execute(
        f"INSERT INTO prices (product_id, price) VALUES ({product_id}, {price})"
    )
    conn.commit()

def get_price_history(product_id: int):
    cursor.execute(
        f"SELECT price FROM prices WHERE product_id={product_id} ORDER BY date ASC"
    )
    return [p[0] for p in cursor.fetchall()]
