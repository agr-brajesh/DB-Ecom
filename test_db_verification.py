import sqlite3
import os
import tempfile
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "ecommerce.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
VIEWS_TRIGGERS_PATH = os.path.join(BASE_DIR, "database", "views_triggers.sql")

def verify_existing_db():
    print("--- 1. VERIFYING EXISTING ECOMMERCE.DB ---")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()

    # Tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = sorted([r[0] for r in c.fetchall()])
    expected_tables = sorted([
        "categories", "products", "customers", "orders", 
        "order_items", "payments", "shopping_cart", "reviews", "search_history", "wishlist"
    ])
    print("Tables found:", tables)
    assert tables == expected_tables, f"Tables mismatch! Expected {expected_tables}, got {tables}"

    # Row counts
    print("\nRow counts in ecommerce.db:")
    for t in tables:
        c.execute(f"SELECT COUNT(*) FROM {t};")
        count = c.fetchone()[0]
        print(f"  - {t}: {count}")

    # Views
    c.execute("SELECT name FROM sqlite_master WHERE type='view';")
    views = sorted([r[0] for r in c.fetchall()])
    expected_views = sorted([
        "v_market_basket", "v_customer_purchase_summary", 
        "v_product_performance", "v_frequent_product_pairs"
    ])
    print("\nViews found:", views)
    assert views == expected_views, f"Views mismatch! Expected {expected_views}, got {views}"

    # Triggers
    c.execute("SELECT name FROM sqlite_master WHERE type='trigger';")
    triggers = sorted([r[0] for r in c.fetchall()])
    expected_triggers = sorted([
        "trg_decrement_product_stock", "trg_validate_stock_before_order"
    ])
    print("\nTriggers found:", triggers)
    assert triggers == expected_triggers, f"Triggers mismatch! Expected {expected_triggers}, got {triggers}"

    # Indexes
    c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
    indexes = sorted([r[0] for r in c.fetchall()])
    expected_indexes = sorted([
        "idx_products_category", "idx_orders_customer", "idx_order_items_product",
        "idx_order_items_order", "idx_reviews_product_rating", "idx_search_customer",
        "idx_cart_customer", "idx_wishlist_customer"
    ])
    print("\nIndexes found:", indexes)
    for idx in expected_indexes:
        assert idx in indexes, f"Index {idx} missing!"

    # Foreign key check
    c.execute("PRAGMA foreign_key_check;")
    fk_errors = c.fetchall()
    print("\nPRAGMA foreign_key_check errors:", fk_errors)
    assert len(fk_errors) == 0, f"Foreign key constraint violations found: {fk_errors}"

    conn.close()
    print("\n[PASS] Existing database verification succeeded.")


def verify_views_execution():
    print("\n--- 2. VERIFYING VIEW EXECUTIONS ---")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    views = [
        "v_market_basket", "v_customer_purchase_summary", 
        "v_product_performance", "v_frequent_product_pairs"
    ]
    for v in views:
        c.execute(f"SELECT * FROM {v} LIMIT 5;")
        cols = [col[0] for col in c.description]
        rows = c.fetchall()
        print(f"View {v}: {len(cols)} columns, fetched {len(rows)} sample rows.")
        print(f"  Columns: {cols}")
        assert len(cols) > 0
        assert len(rows) > 0

    conn.close()
    print("[PASS] Views execution verification succeeded.")


def verify_triggers_and_acid_isolated():
    print("\n--- 3. VERIFYING TRIGGERS AND ACID ON AN ISOLATED IN-MEMORY/TEMP DATABASE ---")
    temp_db = os.path.join(tempfile.gettempdir(), "test_verify_ecommerce.db")
    if os.path.exists(temp_db):
        os.remove(temp_db)

    conn = sqlite3.connect(temp_db)
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        c.executescript(f.read())
    with open(VIEWS_TRIGGERS_PATH, "r", encoding="utf-8") as f:
        c.executescript(f.read())

    # Insert test category, product, customer
    c.execute("INSERT INTO categories VALUES ('C1', 'Electronics', 'Tech', CURRENT_TIMESTAMP);")
    c.execute("INSERT INTO products VALUES ('P1', 'C1', 'Test Laptop', 'TestBrand', 1000.0, 10, 'Desc', CURRENT_TIMESTAMP);")
    c.execute("INSERT INTO customers VALUES ('U1', 'Test User', 'user@test.com', '123', 'City', CURRENT_TIMESTAMP);")
    c.execute("INSERT INTO orders VALUES ('O1', 'U1', CURRENT_TIMESTAMP, 2000.0, 'COMPLETED');")
    conn.commit()

    # Test 1: Stock decrement trigger
    c.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES ('O1', 'P1', 2, 1000.0);")
    conn.commit()
    c.execute("SELECT stock_quantity FROM products WHERE product_id='P1';")
    stock = c.fetchone()[0]
    print(f"Trigger Test 1 (Stock Decrement): stock went from 10 to {stock} (expected 8)")
    assert stock == 8, f"Expected 8, got {stock}"

    # Test 2: Stock validation trigger (insufficient stock)
    # Remaining stock is 8, try ordering 9
    c.execute("INSERT INTO orders VALUES ('O2', 'U1', CURRENT_TIMESTAMP, 9000.0, 'COMPLETED');")
    conn.commit()
    stock_rejection_caught = False
    try:
        c.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES ('O2', 'P1', 9, 1000.0);")
        conn.commit()
    except sqlite3.IntegrityError as e:
        stock_rejection_caught = True
        print(f"Trigger Test 2 (Stock Validation Rejection): Caught expected error -> {e}")

    assert stock_rejection_caught, "Trigger trg_validate_stock_before_order failed to abort insufficient stock insert!"

    # Test 3: Transaction Rollback
    conn.commit()
    conn.execute("BEGIN TRANSACTION;")
    c.execute("INSERT INTO orders VALUES ('O3', 'U1', CURRENT_TIMESTAMP, 1000.0, 'COMPLETED');")
    c.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES ('O3', 'P1', 1, 1000.0);")
    c.execute("SELECT stock_quantity FROM products WHERE product_id='P1';")
    in_trans_stock = c.fetchone()[0]
    assert in_trans_stock == 7
    conn.rollback()

    c.execute("SELECT stock_quantity FROM products WHERE product_id='P1';")
    post_rollback_stock = c.fetchone()[0]
    print(f"Trigger Test 3 (Rollback stock restore): stock restored to {post_rollback_stock} (expected 8)")
    assert post_rollback_stock == 8

    c.execute("SELECT COUNT(*) FROM orders WHERE order_id='O3';")
    assert c.fetchone()[0] == 0, "Rolled back order still exists!"

    conn.close()
    if os.path.exists(temp_db):
        os.remove(temp_db)
    print("[PASS] Triggers and ACID verification on isolated database succeeded.")

def verify_seed_data_on_temp_db():
    print("\n--- 4. VERIFYING SEED_DATA.PY EXECUTION ON ISOLATED TEMP DB ---")
    import importlib.util
    seed_spec = importlib.util.spec_from_file_location("seed_data_module", os.path.join(BASE_DIR, "database", "seed_data.py"))
    seed_module = importlib.util.module_from_spec(seed_spec)
    
    temp_seed_db = os.path.join(tempfile.gettempdir(), "test_seed_temp.db")
    if os.path.exists(temp_seed_db):
        os.remove(temp_seed_db)
        
    seed_spec.loader.exec_module(seed_module)
    original_db_path = seed_module.DB_PATH
    seed_module.DB_PATH = temp_seed_db
    try:
        seed_module.seed_database()
        
        # Verify seeded data
        conn = sqlite3.connect(temp_seed_db)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM products;")
        prod_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders;")
        ord_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM customers;")
        cust_count = c.fetchone()[0]
        print(f"Seeded Products: {prod_count}, Orders: {ord_count}, Customers: {cust_count}")
        assert prod_count >= 40
        assert ord_count >= 100
        assert cust_count >= 20
        conn.close()
        print("[PASS] seed_data.py successfully initialized isolated database.")
    finally:
        seed_module.DB_PATH = original_db_path
        if os.path.exists(temp_seed_db):
            os.remove(temp_seed_db)

if __name__ == "__main__":
    verify_existing_db()
    verify_views_execution()
    verify_triggers_and_acid_isolated()
    verify_seed_data_on_temp_db()
