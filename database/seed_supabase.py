"""
Sync Full Dataset from Local SQLite to Remote Supabase PostgreSQL
Pushes all 25 customers, 303 orders, 965 order items, 213 reviews,
and search queries into remote Supabase.
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce.db")
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF") or (SUPABASE_URL.split("//")[1].split(".")[0] if "//" in SUPABASE_URL else "kxipulbczlqfenntmqzv")
DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")
HOST = os.getenv("SUPABASE_DB_HOST", "aws-0-ap-southeast-2.pooler.supabase.com")
PORT = int(os.getenv("SUPABASE_DB_PORT", 5432))
USER = f"postgres.{PROJECT_REF}"

print("[*] Connecting to local SQLite and remote Supabase PostgreSQL...")
s_conn = sqlite3.connect(SQLITE_PATH)
s_cur = s_conn.cursor()

p_conn = psycopg2.connect(
    host=HOST,
    port=5432,
    user=USER,
    password=DB_PASSWORD,
    dbname="postgres",
    sslmode="require"
)
p_conn.autocommit = True
p_cur = p_conn.cursor()

# 1. Sync Customers
s_cur.execute("SELECT customer_id, name, email, phone, city FROM customers;")
customers = s_cur.fetchall()
execute_batch(p_cur, """
    INSERT INTO customers (customer_id, name, email, phone, city)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (customer_id) DO NOTHING;
""", customers)
print(f"[+] Synced {len(customers)} customers.")

# 2. Sync Orders
s_cur.execute("SELECT order_id, customer_id, order_date, total_amount, order_status FROM orders;")
orders = s_cur.fetchall()
execute_batch(p_cur, """
    INSERT INTO orders (order_id, customer_id, order_date, total_amount, order_status)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (order_id) DO NOTHING;
""", orders)
print(f"[+] Synced {len(orders)} orders.")

# 3. Sync Order Items (Temporarily disable stock trigger during historical bulk load so stock isn't depleted)
p_cur.execute("ALTER TABLE order_items DISABLE TRIGGER trg_decrement_product_stock;")
p_cur.execute("ALTER TABLE order_items DISABLE TRIGGER trg_validate_stock_before_order;")

s_cur.execute("SELECT order_id, product_id, quantity, unit_price FROM order_items;")
order_items = s_cur.fetchall()
execute_batch(p_cur, """
    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (order_id, product_id) DO NOTHING;
""", order_items)
print(f"[+] Synced {len(order_items)} order items.")

p_cur.execute("ALTER TABLE order_items ENABLE TRIGGER trg_decrement_product_stock;")
p_cur.execute("ALTER TABLE order_items ENABLE TRIGGER trg_validate_stock_before_order;")

# 4. Sync Payments
s_cur.execute("SELECT payment_id, order_id, payment_method, payment_status, payment_date, amount FROM payments;")
payments = s_cur.fetchall()
execute_batch(p_cur, """
    INSERT INTO payments (payment_id, order_id, payment_method, payment_status, payment_date, amount)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (order_id) DO NOTHING;
""", payments)
print(f"[+] Synced {len(payments)} payments.")

# 5. Sync Reviews
s_cur.execute("SELECT customer_id, product_id, rating, comment, review_date FROM reviews;")
reviews = s_cur.fetchall()
execute_batch(p_cur, """
    INSERT INTO reviews (customer_id, product_id, rating, comment, review_date)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (customer_id, product_id) DO NOTHING;
""", reviews)
print(f"[+] Synced {len(reviews)} product reviews.")

# 6. Sync Search History
s_cur.execute("SELECT customer_id, search_query, searched_at FROM search_history;")
searches = s_cur.fetchall()
execute_batch(p_cur, """
    INSERT INTO search_history (customer_id, search_query, searched_at)
    VALUES (%s, %s, %s);
""", searches)
print(f"[+] Synced {len(searches)} search history logs.")

# Verify View counts
p_cur.execute("SELECT COUNT(*) FROM v_market_basket;")
baskets = p_cur.fetchone()[0]
print(f"[+] Verified Remote Market Baskets for Apriori: {baskets} baskets ready!")

s_conn.close()
p_conn.close()
print("[OK] Complete database state fully synchronized with Supabase!")
