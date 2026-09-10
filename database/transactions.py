"""
Database Transaction Demonstration: ACID-Compliant Checkout
Demonstrates Atomicity, Consistency, Isolation, and Durability (ACID)
using SQLite transactions, error handling, and trigger verification.
"""

import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def checkout_cart(customer_id: str, payment_method: str = "CREDIT_CARD", simulate_failure: bool = False):
    """
    Executes an atomic checkout transaction:
    1. Reads items from customer's shopping cart
    2. Validates stock availability
    3. Inserts into orders table
    4. Inserts into order_items table (triggers automatic stock decrement)
    5. Inserts into payments table
    6. Removes items from shopping cart
    7. Commits if all succeeded, or Rolls back completely if any step fails.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"\n{'='*60}")
    print(f" TRANSACTION: CHECKOUT FOR CUSTOMER {customer_id}")
    print(f" Mode: {'SIMULATED FAILURE TEST' if simulate_failure else 'NORMAL SUCCESSFUL'}")
    print(f"{'='*60}")

    try:
        # Step 1: Explicitly BEGIN Transaction
        conn.execute("BEGIN TRANSACTION;")
        print("[1] BEGIN TRANSACTION initiated.")

        # Step 2: Fetch current cart items
        cursor.execute("""
            SELECT sc.product_id, sc.quantity, p.product_name, p.price, p.stock_quantity
            FROM shopping_cart sc
            JOIN products p ON sc.product_id = p.product_id
            WHERE sc.customer_id = ?
        """, (customer_id,))
        cart_items = cursor.fetchall()

        if not cart_items:
            raise ValueError(f"Shopping cart for customer {customer_id} is empty!")

        total_amount = 0.0
        print(f"[2] Items in cart to checkout ({len(cart_items)} item(s)):")
        for item in cart_items:
            pid, qty, name, price, stock = item
            print(f"    - {name} ({pid}): Qty {qty} @ ${price:.2f} (In Stock: {stock})")
            if stock < qty:
                raise ValueError(f"Stock Insufficient! Product {name} has only {stock} left, but {qty} requested.")
            total_amount += qty * price

        print(f"[3] Total computed order amount: ${total_amount:.2f}")

        # Step 3: Insert Order Record
        order_id = f"ORD{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO orders (order_id, customer_id, order_date, total_amount, order_status)
            VALUES (?, ?, ?, ?, 'COMPLETED');
        """, (order_id, customer_id, now, round(total_amount, 2)))
        print(f"[4] Created Order record: {order_id}")

        # Step 4: Insert Order Items (will fire trg_decrement_product_stock)
        for item in cart_items:
            pid, qty, name, price, stock = item
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                VALUES (?, ?, ?, ?);
            """, (order_id, pid, qty, price))
            print(f"    - Inserted order item: {name} (Qty: {qty})")

        # Step 5: Insert Payment
        payment_id = f"PAY{uuid.uuid4().hex[:6].upper()}"
        cursor.execute("""
            INSERT INTO payments (payment_id, order_id, payment_method, payment_status, payment_date, amount)
            VALUES (?, ?, ?, 'SUCCESS', ?, ?);
        """, (payment_id, order_id, payment_method, now, round(total_amount, 2)))
        print(f"[5] Processed Payment: {payment_id} via {payment_method}")

        # Simulated Failure Check (e.g. gateway timeout or business validation failure)
        if simulate_failure:
            raise RuntimeError("SIMULATED EXCEPTION: Network payment gateway timeout after order items created!")

        # Step 6: Empty Shopping Cart
        cursor.execute("DELETE FROM shopping_cart WHERE customer_id = ?;", (customer_id,))
        print(f"[6] Cleared customer {customer_id}'s shopping cart.")

        # Step 7: Commit Transaction
        conn.commit()
        print("[7] [COMMIT] Transaction successfully committed! All changes persisted.")
        return {"status": "SUCCESS", "order_id": order_id, "amount": total_amount}

    except Exception as e:
        conn.rollback()
        print(f"[!] [ROLLBACK] Transaction rolled back due to error: {e}")
        return {"status": "FAILED", "error": str(e)}

    finally:
        conn.close()


def test_transactions():
    conn = get_db_connection()
    c = conn.cursor()

    # Ensure C101 has an item in cart for testing
    c.execute("INSERT OR REPLACE INTO shopping_cart (customer_id, product_id, quantity) VALUES ('C101', 'P105', 1);")
    conn.commit()

    # Read stock before
    c.execute("SELECT stock_quantity FROM products WHERE product_id = 'P105';")
    stock_before = c.fetchone()[0]
    conn.close()

    print(f"\nInitial Stock of P105 (Laptop Sleeve): {stock_before}")

    # 1. Test Rollback on Failure
    print("\n--- TEST CASE A: Transaction Rollback (Simulated Failure) ---")
    res_fail = checkout_cart("C101", payment_method="CREDIT_CARD", simulate_failure=True)
    print("Result:", res_fail)

    # Check that stock was NOT decremented and cart was NOT cleared
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT stock_quantity FROM products WHERE product_id = 'P105';")
    stock_after_fail = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM shopping_cart WHERE customer_id = 'C101' AND product_id = 'P105';")
    cart_count_fail = c.fetchone()[0]
    print(f"Stock after failed transaction: {stock_after_fail} (Should match {stock_before})")
    print(f"Cart item exists: {cart_count_fail == 1} (Should be True)")

    # 2. Test Successful Commit
    print("\n--- TEST CASE B: Successful Transaction Commit ---")
    res_success = checkout_cart("C101", payment_method="CREDIT_CARD", simulate_failure=False)
    print("Result:", res_success)

    c.execute("SELECT stock_quantity FROM products WHERE product_id = 'P105';")
    stock_after_success = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM shopping_cart WHERE customer_id = 'C101' AND product_id = 'P105';")
    cart_count_success = c.fetchone()[0]
    print(f"Stock after successful transaction: {stock_after_success} (Should be {stock_before - 1})")
    print(f"Cart cleared: {cart_count_success == 0} (Should be True)")
    conn.close()


if __name__ == "__main__":
    test_transactions()
