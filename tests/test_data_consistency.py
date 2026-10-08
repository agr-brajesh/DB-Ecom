"""
Data Consistency Audit Test Suite for NexusAI E-Commerce Platform.
Validates referential integrity, orphan records, foreign key constraints,
stock boundaries, rating bounds, and monetary consistency across 3NF schema.
"""

import unittest
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "ecommerce.db")


class TestDataConsistencyAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(DB_PATH)
        cls.conn.row_factory = sqlite3.Row
        cls.cursor = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_foreign_key_pragmas(self):
        """PRAGMA foreign_key_check must return 0 violations."""
        self.cursor.execute("PRAGMA foreign_key_check;")
        violations = self.cursor.fetchall()
        self.assertEqual(len(violations), 0, f"Foreign key violations detected: {violations}")

    def test_02_no_orphan_orders(self):
        """All orders must belong to a valid registered customer."""
        self.cursor.execute("""
            SELECT COUNT(*) FROM orders 
            WHERE customer_id NOT IN (SELECT customer_id FROM customers);
        """)
        orphans = self.cursor.fetchone()[0]
        self.assertEqual(orphans, 0, "Found orphan orders with non-existent customer_id")

    def test_03_no_orphan_order_items(self):
        """All order items must reference an existing order and an existing product."""
        self.cursor.execute("""
            SELECT COUNT(*) FROM order_items 
            WHERE order_id NOT IN (SELECT order_id FROM orders);
        """)
        invalid_orders = self.cursor.fetchone()[0]
        self.assertEqual(invalid_orders, 0, "Found order_items referencing non-existent order_id")

        self.cursor.execute("""
            SELECT COUNT(*) FROM order_items 
            WHERE product_id NOT IN (SELECT product_id FROM products);
        """)
        invalid_products = self.cursor.fetchone()[0]
        self.assertEqual(invalid_products, 0, "Found order_items referencing non-existent product_id")

    def test_04_no_orphan_payments(self):
        """All payments must reference an existing order."""
        self.cursor.execute("""
            SELECT COUNT(*) FROM payments 
            WHERE order_id NOT IN (SELECT order_id FROM orders);
        """)
        orphans = self.cursor.fetchone()[0]
        self.assertEqual(orphans, 0, "Found payments referencing non-existent order_id")

    def test_05_payment_amount_consistency(self):
        """Payment amount must match order total_amount within floating point tolerance."""
        self.cursor.execute("""
            SELECT p.payment_id, p.amount, o.total_amount
            FROM payments p
            JOIN orders o ON p.order_id = o.order_id
            WHERE ABS(p.amount - o.total_amount) > 0.05;
        """)
        mismatches = self.cursor.fetchall()
        self.assertEqual(len(mismatches), 0, f"Found payments with amount differing from order total: {mismatches}")

    def test_06_product_stock_bounds(self):
        """Stock quantities must never be negative."""
        self.cursor.execute("SELECT COUNT(*) FROM products WHERE stock_quantity < 0;")
        neg_stock = self.cursor.fetchone()[0]
        self.assertEqual(neg_stock, 0, "Found products with negative stock quantity")

    def test_07_review_ratings_bounds(self):
        """Review ratings must strictly be integers between 1 and 5."""
        self.cursor.execute("SELECT COUNT(*) FROM reviews WHERE rating < 1 OR rating > 5;")
        invalid_ratings = self.cursor.fetchone()[0]
        self.assertEqual(invalid_ratings, 0, "Found review ratings outside 1..5 range")

    def test_08_shopping_cart_integrity(self):
        """Shopping cart records must reference valid customer and valid product."""
        self.cursor.execute("""
            SELECT COUNT(*) FROM shopping_cart 
            WHERE customer_id NOT IN (SELECT customer_id FROM customers)
               OR product_id NOT IN (SELECT product_id FROM products);
        """)
        invalid_carts = self.cursor.fetchone()[0]
        self.assertEqual(invalid_carts, 0, "Found invalid shopping cart entries")

    def test_09_order_status_validity(self):
        """Orders must have valid status according to schema CHECK constraint."""
        valid_statuses = ('PENDING', 'PROCESSING', 'COMPLETED', 'CANCELLED')
        self.cursor.execute("SELECT DISTINCT order_status FROM orders;")
        statuses = [r[0] for r in self.cursor.fetchall()]
        for s in statuses:
            self.assertIn(s, valid_statuses, f"Invalid order status found: {s}")


if __name__ == "__main__":
    unittest.main()
