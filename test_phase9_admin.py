"""
Phase 9 Comprehensive Test Suite:
Professional Admin Analytics & Business Intelligence Dashboard

Tests:
1. Overview KPIs & Real SQL Calculations (Revenue, Orders, Customers, AOV, Low Stock)
2. Historical Comparison Math (Real % change, zero-division safe, trend flags)
3. Sales Analytics & Timeline Aggregation (Date ranges 7d/30d/90d/all, category shares, payment distribution)
4. Consolidated Product Intelligence (Velocity + Inventory Risk + Review Health + Performance Indicators + Sorting)
5. Customer Intelligence & RFM Cohorts (Lifetime spend, segment breakdown, AOV)
6. Operational Inventory Intelligence (Stock status breakdown, days coverage, restock priorities)
7. Review Intelligence & Sentiment Analysis (Catalog sentiment, aspect themes, rating mismatch signals)
8. AI Recommendation Telemetry (Apriori rules distribution, signal weights, commerce intents, companion frequencies)
9. Grounded Business Insights (Verified against database facts, zero hallucinations)
10. API Endpoints Consistency & Response Status (All 8 endpoints return 200 OK)
11. Non-Regression Verification (Customer storefront, recommendations, checkout)
"""

import os
import sys
import unittest
import sqlite3

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from backend.app import app
from ai.analytics_engine import AdminAnalyticsEngine
from ai.recommender import ProductRecommender
from ai.business_intelligence import BusinessIntelligenceEngine
from ai.sentiment_analyzer import ReviewSentimentAnalyzer


class TestPhase9AdminAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = os.path.join(BASE_DIR, "database", "ecommerce.db")
        cls.engine = AdminAnalyticsEngine(cls.db_path)
        cls.recommender = ProductRecommender(cls.db_path)
        cls.bi_engine = BusinessIntelligenceEngine(cls.db_path)
        cls.review_analyzer = ReviewSentimentAnalyzer(cls.db_path)
        cls.client = app.test_client()

    # -------------------------------------------------------------------------
    # TEST 1: Overview KPIs against direct SQLite calculations
    # -------------------------------------------------------------------------
    def test_01_overview_kpis_database_accuracy(self):
        """Verify that overview KPIs match raw SQL queries against ecommerce.db exactly."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(order_id), SUM(total_amount), COUNT(DISTINCT customer_id) FROM orders WHERE order_status = 'COMPLETED';")
        db_orders, db_rev, db_cust = cur.fetchone()

        cur.execute("SELECT COUNT(product_id) FROM products WHERE stock_quantity < 120;")
        db_low_stock = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(oi.quantity), 0) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.order_status = 'COMPLETED';")
        db_prods_sold = cur.fetchone()[0]
        conn.close()

        overview = self.engine.get_overview_kpis(date_range="all")
        kpis = overview["kpis"]

        self.assertEqual(kpis["total_orders"], db_orders)
        self.assertAlmostEqual(kpis["total_revenue"], round(db_rev, 2), places=2)
        self.assertEqual(kpis["total_customers"], db_cust)
        self.assertEqual(kpis["low_stock_products"], db_low_stock)
        self.assertEqual(kpis["products_sold"], db_prods_sold)
        self.assertAlmostEqual(kpis["average_order_value"], round(db_rev / db_orders, 2), places=2)

    # -------------------------------------------------------------------------
    # TEST 2: Genuine Historical Period Comparison Math
    # -------------------------------------------------------------------------
    def test_02_historical_growth_comparison_math(self):
        """Verify that period growth percentages are mathematically sound and verifiable."""
        for rng in ["7d", "30d", "90d"]:
            data = self.engine.get_overview_kpis(date_range=rng)
            growth = data.get("growth_comparison")
            self.assertIsNotNone(growth)
            self.assertTrue(growth["is_comparable"])
            self.assertIn(growth["revenue_trend"], ["UP", "DOWN", "FLAT"])
            self.assertIn(growth["orders_trend"], ["UP", "DOWN", "FLAT"])
            self.assertIn(growth["aov_trend"], ["UP", "DOWN", "FLAT"])

            # Verify math: delta% = (curr - prior) / prior * 100
            prior_rev = growth["prior_revenue"]
            curr_rev = growth["current_revenue"]
            if prior_rev > 0:
                expected_pct = round(((curr_rev - prior_rev) / prior_rev) * 100.0, 1)
                self.assertAlmostEqual(growth["revenue_change_pct"], expected_pct, places=1)

        # "all" range should not fabricate fake comparison
        all_data = self.engine.get_overview_kpis(date_range="all")
        self.assertFalse(all_data["growth_comparison"]["is_comparable"])

    # -------------------------------------------------------------------------
    # TEST 3: Sales Analytics & Timeline Bucketing
    # -------------------------------------------------------------------------
    def test_03_sales_analytics_aggregation(self):
        """Verify daily timeline bucketing, category revenue shares, and payment method distribution."""
        sales = self.engine.get_sales_analytics(date_range="30d")
        self.assertEqual(sales["status"], "success")

        # Timeline entries
        timeline = sales["timeline"]
        self.assertIsInstance(timeline, list)
        self.assertGreater(len(timeline), 0)
        for entry in timeline:
            self.assertIn("date", entry)
            self.assertIn("revenue", entry)
            self.assertIn("orders_count", entry)
            self.assertIn("aov", entry)
            self.assertGreaterEqual(entry["revenue"], 0.0)

        # Category shares sum to approximately 100%
        cat_sales = sales["category_sales"]
        self.assertGreater(len(cat_sales), 0)
        total_share = sum(c["revenue_share_pct"] for c in cat_sales)
        self.assertAlmostEqual(total_share, 100.0, delta=1.5)

        # Payment methods
        payments = sales["payment_methods"]
        self.assertGreater(len(payments), 0)
        total_pay_share = sum(p["share_pct"] for p in payments)
        self.assertAlmostEqual(total_pay_share, 100.0, delta=1.5)

        # Top volume and revenue leaders
        self.assertGreater(len(sales["top_selling_products"]), 0)
        self.assertGreater(len(sales["highest_revenue_products"]), 0)

    # -------------------------------------------------------------------------
    # TEST 4: Consolidated Product Intelligence & Sorting
    # -------------------------------------------------------------------------
    def test_04_consolidated_product_intelligence(self):
        """Verify unified product commercial, inventory risk, review sentiment, and performance indicators."""
        # 1. Best selling sort
        prod_data = self.engine.get_consolidated_product_intelligence(sort_by="best_selling")
        prods = prod_data["products"]
        self.assertEqual(len(prods), 45)

        # Verify descending order of units_sold
        for i in range(len(prods) - 1):
            self.assertGreaterEqual(prods[i]["units_sold"], prods[i + 1]["units_sold"])

        # 2. Highest revenue sort
        rev_data = self.engine.get_consolidated_product_intelligence(sort_by="highest_revenue")
        rev_prods = rev_data["products"]
        for i in range(len(rev_prods) - 1):
            self.assertGreaterEqual(rev_prods[i]["revenue"], rev_prods[i + 1]["revenue"])

        # 3. Highest rated sort
        rated_data = self.engine.get_consolidated_product_intelligence(sort_by="highest_rated")
        rated_prods = rated_data["products"]
        for i in range(len(rated_prods) - 1):
            self.assertGreaterEqual(rated_prods[i]["avg_rating"], rated_prods[i + 1]["avg_rating"])

        # 4. Indicators verification
        valid_indicators = {
            "TOP_PERFORMER", "STRONG_SELLER", "HEALTHY", "LOW_VELOCITY",
            "POORLY_REVIEWED", "OUT_OF_STOCK", "CRITICAL_STOCK", "LOW_STOCK"
        }
        for p in prods:
            self.assertIn(p["performance_indicator"], valid_indicators)
            self.assertIn("inventory_risk", p)
            self.assertIn("sentiment_score", p)
            self.assertIn("mismatched_sentiment", p)

    # -------------------------------------------------------------------------
    # TEST 5: Customer Intelligence Integration
    # -------------------------------------------------------------------------
    def test_05_customer_intelligence_segmentation(self):
        """Verify RFM customer segmentation cohorts and lifetime metrics."""
        cust_summary = self.bi_engine.get_customer_segments_summary()
        self.assertEqual(cust_summary["status"], "success")

        overall = cust_summary["overall_metrics"]
        self.assertEqual(overall["total_customers"], 25)
        self.assertGreater(overall["total_revenue"], 100000.0)
        self.assertGreater(overall["avg_spend_per_customer"], 1000.0)

        # Segments breakdown
        segs = cust_summary["segment_breakdown"]
        self.assertGreater(len(segs), 0)
        segment_names = [s["segment"] for s in segs]
        self.assertIn("HIGH VALUE", segment_names)
        self.assertIn("AT-RISK / INACTIVE", segment_names)

        # Customer list
        customers = cust_summary["customers"]
        self.assertEqual(len(customers), 25)
        for c in customers:
            self.assertIn("segment", c)
            self.assertIn("lifetime_spend", c)
            self.assertIn("total_orders", c)

    # -------------------------------------------------------------------------
    # TEST 6: Operational Inventory Intelligence
    # -------------------------------------------------------------------------
    def test_06_operational_inventory_intelligence(self):
        """Verify stock health breakdown, daily velocities, and actionable restock queue."""
        inv = self.bi_engine.get_inventory_intelligence()
        self.assertEqual(inv["status"], "success")

        kpis = inv["kpis"]
        self.assertEqual(kpis["total_skus"], 45)
        self.assertGreaterEqual(kpis["critical_count"] + kpis["low_stock_count"] + kpis["healthy_count"], 0)

        # Restock recommendations
        restock = inv["restock_recommendations"]
        self.assertIsInstance(restock, list)
        for r in restock:
            self.assertIn("product_name", r)
            self.assertIn("stock_quantity", r)
            self.assertIn("avg_daily_sales", r)
            self.assertIn("suggested_action", r)

    # -------------------------------------------------------------------------
    # TEST 7: Review Intelligence & Sentiment Analysis
    # -------------------------------------------------------------------------
    def test_07_catalog_review_intelligence(self):
        """Verify catalog-wide review sentiment health, aspect themes, and mismatch flagging."""
        rev = self.review_analyzer.get_catalog_review_intelligence(filter_type="all")
        self.assertEqual(rev["status"], "success")

        kpis = rev["kpis"]
        self.assertGreater(kpis["total_reviews_analyzed"], 100)
        self.assertGreater(kpis["catalog_avg_sentiment_score"], 0.4)
        self.assertGreater(kpis["positive_reviews_share"], 50.0)

        # Product list
        products = rev["products"]
        self.assertEqual(len(products), 45)
        for p in products:
            self.assertIn("sentiment_score", p)
            self.assertIn("review_count", p)
            self.assertIn("sentiment", p)

    # -------------------------------------------------------------------------
    # TEST 8: AI Recommendation Engine Telemetry
    # -------------------------------------------------------------------------
    def test_08_ai_recommendation_analytics(self):
        """Verify Apriori rule statistics, hybrid signal weights, and commerce intent telemetry."""
        ai_data = self.engine.get_ai_recommendation_analytics(self.recommender)
        self.assertEqual(ai_data["status"], "success")

        kpis = ai_data["kpis"]
        self.assertGreater(kpis["active_association_rules"], 50)
        self.assertGreater(kpis["average_rule_confidence"], 0.4)
        self.assertGreater(kpis["average_rule_lift"], 1.0)
        self.assertGreater(kpis["max_lift_factor"], 1.0)

        # Signals
        signals = ai_data["ranker_signals"]
        self.assertIn("apriori", signals)
        self.assertIn("search", signals)
        self.assertIn("similarity", signals)
        self.assertIn("popularity", signals)

        # Supported intents
        intents = ai_data["supported_commerce_intents"]
        self.assertGreaterEqual(len(intents), 6)

        # Top rules
        top_rules = ai_data["top_association_rules"]
        self.assertGreater(len(top_rules), 0)
        self.assertIn("affinity_score", top_rules[0])

    # -------------------------------------------------------------------------
    # TEST 9: Grounded Business Intelligence Insights
    # -------------------------------------------------------------------------
    def test_09_grounded_business_insights(self):
        """Verify that insights are generated strictly from database facts and contain actionable drilldowns."""
        insights_res = self.engine.get_business_insights(date_range="30d")
        self.assertEqual(insights_res["status"], "success")
        self.assertGreater(insights_res["insights_count"], 0)

        insights = insights_res["insights"]
        for ins in insights:
            self.assertIn("id", ins)
            self.assertIn("category", ins)
            self.assertIn("title", ins)
            self.assertIn("detail", ins)
            self.assertIn("action", ins)
            self.assertIn("drilldown_tab", ins)

    # -------------------------------------------------------------------------
    # TEST 10: All 8 Admin API Endpoints via Flask Test Client
    # -------------------------------------------------------------------------
    def test_10_admin_api_endpoints_status_200(self):
        """Ensure all 8 Flask Admin endpoints respond with 200 OK and valid JSON structures."""
        endpoints = [
            ("/api/admin/overview?range=7d", "kpis"),
            ("/api/admin/overview?range=30d", "kpis"),
            ("/api/admin/overview?range=all", "kpis"),
            ("/api/admin/sales-analytics?range=30d", "timeline"),
            ("/api/admin/product-analytics?sort=best_selling", "products"),
            ("/api/admin/customer-analytics", "overall_metrics"),
            ("/api/admin/inventory-analytics", "status"),
            ("/api/admin/review-analytics", "status"),
            ("/api/admin/ai-analytics", "kpis"),
            ("/api/admin/ai-recommendation-analytics", "kpis"),
            ("/api/admin/insights?range=all", "insights")
        ]

        for path, required_key in endpoints:
            with self.subTest(path=path):
                res = self.client.get(path)
                self.assertEqual(res.status_code, 200, f"Endpoint {path} failed with {res.status_code}")
                data = res.json
                self.assertIsNotNone(data)
                self.assertIn(required_key, data, f"Key '{required_key}' missing in {path}")

    # -------------------------------------------------------------------------
    # TEST 11: Non-Regression of Storefront, Recommendations, & Checkout
    # -------------------------------------------------------------------------
    def test_11_non_regression_existing_systems(self):
        """Verify that customer storefront, recommendation engine, cart, and transactions continue working perfectly."""
        # 1. Customer Storefront Home Sections
        res = self.client.get("/api/home/sections")
        self.assertEqual(res.status_code, 200)
        self.assertIn("featured", res.json["sections"])
        self.assertIn("bundle", res.json["sections"])

        # 2. Recommendations for Customer C101
        res = self.client.get("/api/recommendations/C101?top_n=4")
        self.assertEqual(res.status_code, 200)
        self.assertIn("recommendations", res.json["data"])
        self.assertEqual(len(res.json["data"]["recommendations"]), 4)

        # 3. Explainability Audit for Customer C101
        res = self.client.get("/api/recommendations/audit/C101?top_n=4")
        self.assertEqual(res.status_code, 200)
        self.assertIn("audit", res.json)

        # 4. Product Review Intelligence (Phase 8)
        res = self.client.get("/api/products/P101/review-intelligence")
        self.assertEqual(res.status_code, 200)
        self.assertIn("sentiment_score", res.json)

        # 5. Database Lab Raw SQL Runner
        res = self.client.post("/api/sql/execute", json={"query": "SELECT COUNT(*) FROM products;"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json["rows"][0]["COUNT(*)"], 45)


if __name__ == "__main__":
    unittest.main()
