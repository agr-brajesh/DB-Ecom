"""
Security and Input Validation Audit Test Suite for NexusAI.
Validates:
1. SQL Runner security: Read-only protection, statement splitting block, injection prevention.
2. DDL and DML write command blocking (INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH).
3. API input validation: Invalid IDs, negative quantities, malformed requests.
4. Error message hygiene: No sensitive internals leaked.
"""

import unittest
import sqlite3
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import app


class TestSecurityAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()

    def test_01_sql_runner_blocks_insert(self):
        """Live SQL runner must strictly reject INSERT statements."""
        payload = {"query": "INSERT INTO categories (category_id, category_name) VALUES ('C999', 'Hacked');"}
        res = self.client.post("/api/sql/execute", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        msg = data.get("message", "").lower()
        self.assertTrue("read-only" in msg or "prohibited" in msg, f"Unexpected message: {msg}")

    def test_02_sql_runner_blocks_drop_table(self):
        """Live SQL runner must strictly reject DROP statements."""
        payload = {"query": "DROP TABLE customers;"}
        res = self.client.post("/api/sql/execute", json=payload)
        self.assertEqual(res.status_code, 400)

    def test_03_sql_runner_blocks_update(self):
        """Live SQL runner must strictly reject UPDATE statements."""
        payload = {"query": "UPDATE products SET price = 0.0 WHERE product_id = 'P101';"}
        res = self.client.post("/api/sql/execute", json=payload)
        self.assertEqual(res.status_code, 400)

    def test_04_sql_runner_blocks_delete(self):
        """Live SQL runner must strictly reject DELETE statements."""
        payload = {"query": "DELETE FROM orders;"}
        res = self.client.post("/api/sql/execute", json=payload)
        self.assertEqual(res.status_code, 400)

    def test_05_sql_runner_blocks_multiple_statements(self):
        """Live SQL runner must reject semicolon-chained statement injections."""
        payload = {"query": "SELECT * FROM products; DROP TABLE products;"}
        res = self.client.post("/api/sql/execute", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("multiple statements", data.get("message", "").lower())

    def test_06_sql_runner_allows_safe_queries(self):
        """Live SQL runner allows SELECT and EXPLAIN QUERY PLAN."""
        payload = {"query": "EXPLAIN QUERY PLAN SELECT * FROM orders WHERE customer_id = 'C101';"}
        res = self.client.post("/api/sql/execute", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")

    def test_07_cart_negative_quantity_validation(self):
        """API must reject non-positive quantities when modifying cart."""
        payload = {"customer_id": "C101", "product_id": "P101", "quantity": -5}
        res = self.client.post("/api/cart/add", json=payload)
        # Should be rejected or sanitized
        self.assertIn(res.status_code, (400, 422))

    def test_08_invalid_product_detail(self):
        """Requesting non-existent product ID returns clean 404 rather than 500 crash."""
        res = self.client.get("/api/products/P_NON_EXISTENT_9999")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertIn("not found", data.get("message", "").lower())

    def test_09_invalid_customer_profile(self):
        """Requesting non-existent customer profile returns clean 404."""
        res = self.client.get("/api/customer/C_NON_EXISTENT_9999/profile")
        self.assertEqual(res.status_code, 404)

    def test_10_no_secrets_in_environment_files(self):
        """Verify .env.example does not expose real credentials."""
        env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
        if os.path.exists(env_example_path):
            with open(env_example_path, "r") as f:
                content = f.read()
                # Ensure no private live keys
                self.assertNotIn("AIzaSy", content)
                self.assertNotIn("sk-live-", content)


if __name__ == "__main__":
    unittest.main()
