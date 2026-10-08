"""
Phase 7 Verification Test Suite: Business Intelligence & Inventory Intelligence
Tests:
A. Customer segmentation with multiple customers
B. New customer
C. Frequent customer
D. High-value customer
E. Customer with no orders (division-by-zero safety)
F. Product with high sales velocity
G. Low-stock product
H. Out-of-stock product
I. Product with insufficient sales history (division-by-zero safety)
J. REST API endpoints verification (/api/admin/...)
K. Non-regression: Hybrid recommendations, Phase 6 explainability, and database integrity
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from ai.business_intelligence import BusinessIntelligenceEngine
from backend.app import app, recommender, DB_PATH


class TestPhase7BusinessIntelligence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_path = DB_PATH
        cls.bi = BusinessIntelligenceEngine(cls.db_path)
        cls.client = app.test_client()

    # =========================================================================
    # Test A: Customer segmentation with multiple customers
    # =========================================================================
    def test_a_customer_segmentation_multiple_customers(self):
        summary = self.bi.get_customer_segments_summary()
        self.assertEqual(summary["status"], "success")
        
        customers = summary["customers"]
        self.assertGreaterEqual(len(customers), 20, "Should have at least 20 customers")

        # Verify segments distribution
        counts = summary["segment_counts"]
        total_from_counts = sum(counts.values())
        self.assertEqual(total_from_counts, len(customers), "Sum of segment counts must equal total customers")

        # Check breakdown percentages sum to ~100%
        percentages = [s["percentage"] for s in summary["segment_breakdown"]]
        self.assertAlmostEqual(sum(percentages), 100.0, delta=1.0)

        # Check KPIs are sensible
        ov = summary["overall_metrics"]
        self.assertGreater(ov["total_revenue"], 50000.0)
        self.assertGreater(ov["overall_aov"], 100.0)
        self.assertGreater(ov["avg_order_frequency"], 5.0)

        print("\n[TEST A PASS] Customer segmentation with multiple customers verified.")
        print(f"      Total customers: {len(customers)} | Segments: {counts}")

    # =========================================================================
    # Test B: New customer
    # =========================================================================
    def test_b_new_customer_classification(self):
        # 1 order recently
        seg, reasons, action = self.bi.classify_customer(frequency=1, monetary=249.99, recency_days=5)
        self.assertEqual(seg, "NEW CUSTOMER")
        self.assertTrue(any("Early customer lifecycle" in r or "initial" in r.lower() for r in reasons))
        self.assertTrue("Nurturing" in action or "15%" in action or "Post-Purchase" in action)

        scores = self.bi.compute_rfm_scores(recency_days=5, frequency=1, monetary=249.99)
        self.assertEqual(scores["recency_score"], 5)
        self.assertEqual(scores["frequency_score"], 1)
        self.assertEqual(scores["monetary_score"], 1)
        self.assertEqual(scores["rfm_tier"], "R5F1M1")

        print("[TEST B PASS] New customer classification & RFM scoring verified.")

    # =========================================================================
    # Test C: Frequent customer
    # =========================================================================
    def test_c_frequent_customer_classification(self):
        # 15 orders with moderate spend
        seg, reasons, action = self.bi.classify_customer(frequency=15, monetary=7500.0, recency_days=35)
        self.assertEqual(seg, "FREQUENT SHOPPER")
        self.assertTrue(any("repeat" in r.lower() or "15" in r for r in reasons))
        self.assertTrue("Loyalty" in action)

        scores = self.bi.compute_rfm_scores(recency_days=35, frequency=15, monetary=7500.0)
        self.assertEqual(scores["frequency_score"], 4)
        self.assertEqual(scores["monetary_score"], 3)
        self.assertGreaterEqual(scores["composite_score"], 3.0)

        print("[TEST C PASS] Frequent customer classification verified.")

    # =========================================================================
    # Test D: High-value customer
    # =========================================================================
    def test_d_high_value_customer_classification(self):
        # High lifetime spend >= $12,000
        seg, reasons, action = self.bi.classify_customer(frequency=18, monetary=16500.0, recency_days=25)
        self.assertEqual(seg, "HIGH VALUE")
        self.assertTrue(any("spend" in r.lower() for r in reasons))
        self.assertTrue("VIP" in action)

        scores = self.bi.compute_rfm_scores(recency_days=25, frequency=18, monetary=16500.0)
        self.assertEqual(scores["recency_score"], 4)
        self.assertEqual(scores["frequency_score"], 4)
        self.assertEqual(scores["monetary_score"], 5)

        # Also verify live database customer C111 or C102
        c102 = self.bi.get_customer_insights("C102")
        self.assertEqual(c102["status"], "success")
        self.assertEqual(c102["customer"]["segment"], "HIGH VALUE")

        print(f"[TEST D PASS] High-value customer classification verified (C102: ${c102['customer']['lifetime_spend']}).")

    # =========================================================================
    # Test E: Customer with no orders (division-by-zero check)
    # =========================================================================
    def test_e_customer_with_no_orders(self):
        # 0 orders, 0 spend, None recency
        seg, reasons, action = self.bi.classify_customer(frequency=0, monetary=0.0, recency_days=None)
        self.assertEqual(seg, "NEW CUSTOMER")
        self.assertTrue(any("Zero completed transactions" in r for r in reasons))
        self.assertTrue("Activation" in action)

        # RFM score calculation must not throw division by zero
        scores = self.bi.compute_rfm_scores(recency_days=None, frequency=0, monetary=0.0)
        self.assertEqual(scores["recency_score"], 1)
        self.assertEqual(scores["frequency_score"], 1)
        self.assertEqual(scores["monetary_score"], 1)
        self.assertEqual(scores["composite_score"], 1.0)
        self.assertEqual(scores["rfm_tier"], "R1F1M1")

        print("[TEST E PASS] Customer with zero orders handles gracefully without division-by-zero.")

    # =========================================================================
    # Test F: Product with high sales velocity
    # =========================================================================
    def test_f_product_with_high_sales_velocity(self):
        # Current stock = 42, daily velocity = 8.1 units/day -> cover = 5.2 days
        stock = 42
        velocity = 8.1
        cover = round(stock / velocity, 1)
        self.assertEqual(cover, 5.2)

        risk, label, action, reorder = self.bi.classify_inventory_risk(stock, velocity, cover)
        self.assertEqual(risk, "CRITICAL")
        self.assertTrue("Expedite" in action or "priority" in action.lower())
        self.assertGreater(reorder, 0)

        print(f"[TEST F PASS] High sales velocity product correctly evaluated (Stock: {stock}, Vel: {velocity}/day, Cover: {cover} days -> {risk}).")

    # =========================================================================
    # Test G: Low-stock product
    # =========================================================================
    def test_g_low_stock_product(self):
        # Current stock = 50, velocity = 0.25 -> cover = 200 days -> LOW STOCK
        stock = 50
        velocity = 0.25
        cover = round(stock / velocity, 1)

        risk, label, action, reorder = self.bi.classify_inventory_risk(stock, velocity, cover)
        self.assertIn(risk, ["CRITICAL", "LOW STOCK"])
        self.assertGreater(reorder, 0)

        print(f"[TEST G PASS] Low stock product correctly classified as {risk} with reorder qty {reorder}.")

    # =========================================================================
    # Test H: Out-of-stock product
    # =========================================================================
    def test_h_out_of_stock_product(self):
        stock = 0
        velocity = 1.5
        cover = 0.0

        risk, label, action, reorder = self.bi.classify_inventory_risk(stock, velocity, cover)
        self.assertEqual(risk, "OUT OF STOCK")
        self.assertTrue("Immediate" in action or "OUT OF STOCK" in action)
        self.assertGreaterEqual(reorder, 50)

        print("[TEST H PASS] Out-of-stock product classified as OUT OF STOCK with immediate replenishment.")

    # =========================================================================
    # Test I: Product with insufficient sales history (division-by-zero check)
    # =========================================================================
    def test_i_product_with_insufficient_sales_history(self):
        # 0 units sold -> velocity = 0.0, cover = None
        stock = 100
        velocity = 0.0
        cover = None

        risk, label, action, reorder = self.bi.classify_inventory_risk(stock, velocity, cover)
        self.assertEqual(risk, "INSUFFICIENT HISTORY")
        self.assertEqual(reorder, 0)
        self.assertTrue("Monitor" in action or "baseline" in action)

        # Verify live database product P106 (4K monitor with 0 sales)
        inv = self.bi.get_inventory_intelligence()
        p106 = next((p for p in inv["inventory_matrix"] if p["product_id"] == "P106"), None)
        self.assertIsNotNone(p106)
        self.assertEqual(p106["units_sold"], 0)
        self.assertIsNone(p106["estimated_stock_cover_days"])
        self.assertEqual(p106["risk_state"], "INSUFFICIENT HISTORY")

        print(f"[TEST I PASS] SKU with 0 sales (P106) evaluated safely without division by zero (Risk: {p106['risk_state']}).")

    # =========================================================================
    # Test J: REST API Endpoints Verification
    # =========================================================================
    def test_j_api_endpoints(self):
        # 1. /api/admin/customer-segments
        r1 = self.client.get("/api/admin/customer-segments")
        self.assertEqual(r1.status_code, 200)
        j1 = r1.get_json()
        self.assertEqual(j1["status"], "success")
        self.assertIn("customers", j1)
        self.assertIn("segment_breakdown", j1)

        # 2. /api/admin/customer/<id>/insights
        r2 = self.client.get("/api/admin/customer/C101/insights")
        self.assertEqual(r2.status_code, 200)
        j2 = r2.get_json()
        self.assertEqual(j2["status"], "success")
        self.assertEqual(j2["customer"]["customer_id"], "C101")
        self.assertIn("reasons", j2["customer"])
        self.assertIn("suggested_action", j2["customer"])

        # 3. /api/admin/customer/NONEXISTENT/insights -> 404
        r2_bad = self.client.get("/api/admin/customer/NONEXISTENT/insights")
        self.assertEqual(r2_bad.status_code, 404)

        # 4. /api/admin/inventory-intelligence
        r3 = self.client.get("/api/admin/inventory-intelligence?recent_days=30")
        self.assertEqual(r3.status_code, 200)
        j3 = r3.get_json()
        self.assertEqual(j3["status"], "success")
        self.assertIn("kpis", j3)
        self.assertIn("restock_recommendations", j3)
        self.assertIn("inventory_matrix", j3)

        # 5. /api/admin/product-intelligence
        r4 = self.client.get("/api/admin/product-intelligence")
        self.assertEqual(r4.status_code, 200)
        j4 = r4.get_json()
        self.assertEqual(j4["status"], "success")
        self.assertEqual(j4["total_products"], 45)

        # 6. /api/admin/ai-insights
        r5 = self.client.get("/api/admin/ai-insights")
        self.assertEqual(r5.status_code, 200)
        j5 = r5.get_json()
        self.assertEqual(j5["status"], "success")
        self.assertGreaterEqual(j5["insights_count"], 4)
        for insight in j5["insights"]:
            self.assertIn("title", insight)
            self.assertIn("description", insight)
            self.assertIn("metrics", insight)
            self.assertIn("action", insight)

        print("[TEST J PASS] All 5 Phase 7 Admin REST endpoints verified.")

    # =========================================================================
    # Test K: Non-Regression of Existing Phases
    # =========================================================================
    def test_k_non_regression_hybrid_and_xai(self):
        # 1. Existing Recommender for C101
        res = recommender.recommend("C101", top_n=4)
        self.assertIn("recommendations", res)
        self.assertGreaterEqual(len(res["recommendations"]), 1)

        # 2. Phase 6 Explanations still present
        rec1 = res["recommendations"][0]
        self.assertIn("reason", rec1)
        self.assertIn("reasons", rec1)
        self.assertIn("technical_explanation", rec1)
        self.assertIn("signals", rec1)

        # 3. Storefront products endpoint
        r_prod = self.client.get("/api/products")
        self.assertEqual(r_prod.status_code, 200)
        self.assertEqual(len(r_prod.get_json()["products"]), 45)

        # 4. View inspection
        r_view = self.client.get("/api/analytics/view/v_customer_purchase_summary")
        self.assertEqual(r_view.status_code, 200)
        self.assertGreater(len(r_view.get_json()["data"]), 0)

        print("[TEST K PASS] Zero regression on Hybrid recommendations, Phase 6 XAI explanations, and DBMS views.")


if __name__ == "__main__":
    unittest.main()
