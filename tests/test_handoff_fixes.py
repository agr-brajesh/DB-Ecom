"""
Regression and verification unit tests for the 5 handoff fixes:
1. Frontend window bindings & review inspector references
2. Order total calculation & line items consistency
3. Database connection lifecycle & Flask g request teardown
4. Cart stock ceiling validation & unknown customer 404
5. SQL runner bounded row limits & 3-second query timeout
"""

import os
import sys
import sqlite3
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.app import app, get_db_connection


class TestHandoffFixes(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.db_path = os.path.join(BASE_DIR, "database", "ecommerce.db")

    def test_01_frontend_bindings_valid(self):
        """Verify frontend/app.js does not reference deleted functions and has valid bindings."""
        app_js_path = os.path.join(BASE_DIR, "frontend", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Ensure problematic deleted/renamed bindings are fixed
        self.assertNotIn("window.resetShopFilters = resetShopFilters;", content)
        self.assertIn("window.filterShopByCategory = filterShopByCategory;", content)
        self.assertIn("window.removeProductFromCart = removeProductFromCart;", content)
        self.assertIn("openAdminReviewInspector", content)
        self.assertNotIn("onclick=\"openReviewInspector(", content)

    def test_02_order_totals_and_payments_reconciled(self):
        """Verify orders.total_amount equals SUM(quantity * unit_price) and payments.amount matches."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check orders vs line items
        cursor.execute("""
            SELECT o.order_id, o.total_amount, ROUND(SUM(oi.quantity * oi.unit_price), 2) as line_sum
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            GROUP BY o.order_id
            HAVING ABS(o.total_amount - line_sum) > 0.01;
        """)
        mismatched_orders = cursor.fetchall()
        self.assertEqual(len(mismatched_orders), 0, f"Found {len(mismatched_orders)} mismatched orders")

        # Check payments vs orders
        cursor.execute("""
            SELECT p.payment_id, p.amount, o.total_amount
            FROM payments p
            JOIN orders o ON p.order_id = o.order_id
            WHERE ABS(p.amount - o.total_amount) > 0.01;
        """)
        mismatched_payments = cursor.fetchall()
        self.assertEqual(len(mismatched_payments), 0, f"Found {len(mismatched_payments)} mismatched payments")
        conn.close()

    def test_03_db_connection_teardown_lifecycle(self):
        """Verify request-scoped DB connection on Flask g is closed upon request completion."""
        with self.app.test_request_context():
            conn = get_db_connection()
            # Verify connection is open during request
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            self.assertEqual(cursor.fetchone()[0], 1)

        # After request context exits, connection must be closed
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1;")

    def test_04a_cart_unknown_customer_returns_404(self):
        """Adding to cart with non-existent customer must return 404 Not Found."""
        res = self.client.post("/api/cart/add", json={
            "customer_id": "NON_EXISTENT_CUST_9999",
            "product_id": "P101",
            "quantity": 1
        })
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("Customer", data.get("message", ""))

    def test_04b_cart_exceeding_stock_with_existing_items_returns_400(self):
        """Adding to cart when existing_qty + requested_qty > stock must return 400."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT stock_quantity FROM products WHERE product_id = 'P101';")
        stock = cursor.fetchone()[0]

        # Stage existing cart with (stock - 1) items
        cursor.execute("DELETE FROM shopping_cart WHERE customer_id = 'C101' AND product_id = 'P101';")
        cursor.execute("INSERT INTO shopping_cart (customer_id, product_id, quantity) VALUES ('C101', 'P101', ?);", (stock - 1,))
        conn.commit()
        conn.close()

        try:
            # Requesting 2 more should fail because (stock - 1) + 2 = stock + 1 > stock
            res = self.client.post("/api/cart/add", json={
                "customer_id": "C101",
                "product_id": "P101",
                "quantity": 2
            })
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertEqual(data.get("status"), "error")
            self.assertIn("exceeds available stock", data.get("message", ""))
        finally:
            # Clean up test cart row
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM shopping_cart WHERE customer_id = 'C101' AND product_id = 'P101';")
            conn.commit()
            conn.close()

    def test_05a_sql_runner_bounded_fetch(self):
        """Cross join query in SQL runner must return at most 100 rows with has_more=True."""
        res = self.client.post("/api/sql/execute", json={
            "query": "SELECT a.order_item_id AS a_id, b.order_item_id AS b_id FROM order_items a, order_items b;"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("row_count"), 100)
        self.assertEqual(len(data.get("rows")), 100)
        self.assertTrue(data.get("has_more"))

    def test_05b_sql_runner_query_timeout(self):
        """Long-running infinite recursion query must be aborted within 3 seconds."""
        res = self.client.post("/api/sql/execute", json={
            "query": "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt) SELECT * FROM cnt WHERE x > 999999999;"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("timed out", data.get("message", "").lower())


if __name__ == "__main__":
    unittest.main()
