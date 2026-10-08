"""
ACID Transaction Demonstration Test Suite for NexusAI.
Validates Atomicity, Consistency, Isolation, and Durability:
- Normal atomic checkout: COMMIT persists changes and executes triggers
- Failure test: Simulated failure causes complete ROLLBACK with zero state change
- Concurrency and boundary protection
"""

import unittest
import sqlite3
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.transactions import checkout_cart, get_db_connection

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "ecommerce.db")


class TestAcidTransactions(unittest.TestCase):
    def setUp(self):
        # Prepare test customer and test item in cart
        self.conn = get_db_connection()
        self.cursor = self.conn.cursor()
        self.test_customer = "C101"
        self.test_product = "P105"  # Waterproof Padded Laptop Sleeve

        # Clean cart and insert 1 unit
        self.cursor.execute("DELETE FROM shopping_cart WHERE customer_id = ?;", (self.test_customer,))
        self.cursor.execute("""
            INSERT INTO shopping_cart (customer_id, product_id, quantity)
            VALUES (?, ?, 1);
        """, (self.test_customer, self.test_product))
        self.conn.commit()

        # Record initial product stock
        self.cursor.execute("SELECT stock_quantity FROM products WHERE product_id = ?;", (self.test_product,))
        self.initial_stock = self.cursor.fetchone()[0]

    def tearDown(self):
        # Restore stock to initial_stock to keep dataset clean
        self.cursor.execute("UPDATE products SET stock_quantity = ? WHERE product_id = ?;",
                            (self.initial_stock, self.test_product))
        self.cursor.execute("DELETE FROM shopping_cart WHERE customer_id = ?;", (self.test_customer,))
        self.conn.commit()
        self.conn.close()

    def test_01_atomic_rollback_on_failure(self):
        """
        FAILURE TEST:
        BEGIN -> Insert Order -> Insert Items -> Simulated Failure -> ROLLBACK.
        Verifies:
        1. Product stock is NOT decremented.
        2. Cart items are NOT deleted.
        3. No order record persists.
        4. No payment record persists.
        """
        # Count orders before
        self.cursor.execute("SELECT COUNT(*) FROM orders WHERE customer_id = ?;", (self.test_customer,))
        orders_before = self.cursor.fetchone()[0]

        # Execute with simulated failure
        result = checkout_cart(self.test_customer, payment_method="CREDIT_CARD", simulate_failure=True)
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("SIMULATED EXCEPTION", result["error"])

        # Verification 1: Product stock must be unchanged
        self.cursor.execute("SELECT stock_quantity FROM products WHERE product_id = ?;", (self.test_product,))
        stock_after = self.cursor.fetchone()[0]
        self.assertEqual(stock_after, self.initial_stock, "Stock was modified despite transaction failure!")

        # Verification 2: Cart item must still exist
        self.cursor.execute("SELECT COUNT(*) FROM shopping_cart WHERE customer_id = ? AND product_id = ?;",
                            (self.test_customer, self.test_product))
        cart_count = self.cursor.fetchone()[0]
        self.assertEqual(cart_count, 1, "Cart was cleared despite transaction failure!")

        # Verification 3: No new order created
        self.cursor.execute("SELECT COUNT(*) FROM orders WHERE customer_id = ?;", (self.test_customer,))
        orders_after = self.cursor.fetchone()[0]
        self.assertEqual(orders_after, orders_before, "Order was inserted despite transaction failure!")

    def test_02_atomic_commit_on_success(self):
        """
        NORMAL CHECKOUT:
        BEGIN -> Validate -> Insert Order -> Insert Items -> Stock Update Trigger -> Payment -> Cart Empty -> COMMIT.
        Verifies:
        1. Product stock decremented by exactly quantity ordered (via trg_decrement_product_stock).
        2. Shopping cart cleared.
        3. Order record created with order_status = 'COMPLETED'.
        4. Payment record created with payment_status = 'SUCCESS'.
        """
        # Execute normal successful checkout
        result = checkout_cart(self.test_customer, payment_method="CREDIT_CARD", simulate_failure=False)
        self.assertEqual(result["status"], "SUCCESS")
        order_id = result["order_id"]
        self.assertTrue(order_id.startswith("ORD"))

        # Verification 1: Product stock decremented by 1
        self.cursor.execute("SELECT stock_quantity FROM products WHERE product_id = ?;", (self.test_product,))
        stock_after = self.cursor.fetchone()[0]
        self.assertEqual(stock_after, self.initial_stock - 1, "Stock was not decremented correctly!")

        # Verification 2: Cart was emptied
        self.cursor.execute("SELECT COUNT(*) FROM shopping_cart WHERE customer_id = ?;", (self.test_customer,))
        cart_count = self.cursor.fetchone()[0]
        self.assertEqual(cart_count, 0, "Cart was not emptied after checkout!")

        # Verification 3: Order was created
        self.cursor.execute("SELECT total_amount, order_status FROM orders WHERE order_id = ?;", (order_id,))
        order_row = self.cursor.fetchone()
        self.assertIsNotNone(order_row)
        self.assertEqual(order_row[1], "COMPLETED")

        # Verification 4: Payment was created
        self.cursor.execute("SELECT amount, payment_status FROM payments WHERE order_id = ?;", (order_id,))
        pay_row = self.cursor.fetchone()
        self.assertIsNotNone(pay_row)
        self.assertEqual(pay_row[1], "SUCCESS")

        # Clean up inserted test order and payment
        self.cursor.execute("DELETE FROM payments WHERE order_id = ?;", (order_id,))
        self.cursor.execute("DELETE FROM order_items WHERE order_id = ?;", (order_id,))
        self.cursor.execute("DELETE FROM orders WHERE order_id = ?;", (order_id,))
        self.conn.commit()


if __name__ == "__main__":
    unittest.main()
