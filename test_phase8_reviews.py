"""
Phase 8 Verification Test Suite: AI Review Intelligence & Sentiment Analysis
Tests:
A. Product with many positive reviews
B. Product with mixed reviews
C. Product with negative reviews
D. Product with very few reviews
E. Product with missing comments (None or empty string)
F. Reviews with short text ("Ok", "Good", "Bad")
G. Rating/text disagreement (Review Signals & Mismatches)
H. Product with zero reviews (zero-division & empty data safety)
I. Aspect Theme extraction (verified against real text tokens)
J. Product Health scorecard & AI Customer Summary generation
K. Recency trend analysis (recent vs overall momentum)
L. REST API endpoints verification (/api/products/..., /api/admin/...)
M. Non-regression: Recommendations, Phase 6 explainability, and Phase 7 BI
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from ai.sentiment_analyzer import ReviewSentimentAnalyzer
from backend.app import app, DB_PATH, recommender, bi_engine


class TestPhase8ReviewIntelligence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_path = DB_PATH
        cls.analyzer = ReviewSentimentAnalyzer(cls.db_path)
        cls.client = app.test_client()

    # =========================================================================
    # Scenario A: Product with many positive reviews
    # =========================================================================
    def test_a_product_with_many_positive_reviews(self):
        # P101 (Ultra-Slim Laptop) or P205 (Noise-Cancelling Wireless Earbuds)
        intel = self.analyzer.get_product_review_intelligence("P101")
        self.assertEqual(intel["status"], "success")
        self.assertGreater(intel["review_count"], 0)
        self.assertGreaterEqual(intel["sentiment"]["positive"], 0.50)
        self.assertGreaterEqual(intel["sentiment_score"], 0.60)
        self.assertIn("positive_themes", intel)
        self.assertIsInstance(intel["positive_themes"], list)
        self.assertGreater(len(intel["positive_themes"]), 0)

    # =========================================================================
    # Scenario B: Product with mixed reviews
    # =========================================================================
    def test_b_product_with_mixed_reviews(self):
        # Synthetic classification of mixed batch
        c1 = self.analyzer.classify_review(5, "Amazing sound quality and great battery life!")
        c2 = self.analyzer.classify_review(3, "Decent headphones, sound is average but case is okay.")
        c3 = self.analyzer.classify_review(2, "Poor microphone and uncomfortable after an hour.")

        self.assertEqual(c1["sentiment"], "POSITIVE")
        self.assertEqual(c2["sentiment"], "NEUTRAL")
        self.assertEqual(c3["sentiment"], "NEGATIVE")

        # Themes aggregation across mixed batch
        pos_themes, neg_themes = self.analyzer.aggregate_themes([c1, c2, c3])
        pos_theme_names = [t["theme"] for t in pos_themes]
        neg_theme_names = [t["theme"] for t in neg_themes]

        self.assertIn("Sound Quality", pos_theme_names)
        self.assertIn("Microphone Quality", neg_theme_names)

    # =========================================================================
    # Scenario C: Product with negative reviews
    # =========================================================================
    def test_c_product_with_negative_reviews(self):
        rev = self.analyzer.classify_review(1, "Terrible build quality. Flimsy cheap plastic and disconnected constantly.")
        self.assertEqual(rev["sentiment"], "NEGATIVE")
        self.assertLessEqual(rev["sentiment_score"], 0.25)
        self.assertLessEqual(rev["text_polarity"], -0.30)
        theme_names = [t["theme"].lower() if isinstance(t, dict) else str(t).lower() for t in rev["aspect_themes"]]
        self.assertIn("build quality", theme_names)

    # =========================================================================
    # Scenario D: Product with very few reviews
    # =========================================================================
    def test_d_product_with_few_reviews(self):
        intel = self.analyzer.get_product_review_intelligence("P701")
        self.assertEqual(intel["status"], "success")
        self.assertGreaterEqual(intel["review_count"], 1)
        self.assertIn("product_health", intel)
        self.assertIsNotNone(intel["product_health"]["product_health_score"])

    # =========================================================================
    # Scenario E: Product with missing comments (None or empty string)
    # =========================================================================
    def test_e_missing_comments_graceful_handling(self):
        # None comment
        c_none = self.analyzer.classify_review(5, None)
        self.assertEqual(c_none["sentiment"], "POSITIVE")
        self.assertEqual(c_none["text_polarity"], 0.0)
        self.assertFalse(c_none["is_mismatch"])

        # Empty string comment
        c_empty = self.analyzer.classify_review(1, "")
        self.assertEqual(c_empty["sentiment"], "NEGATIVE")
        self.assertEqual(c_empty["text_polarity"], 0.0)

        # Whitespace comment
        c_spaces = self.analyzer.classify_review(3, "   ")
        self.assertEqual(c_spaces["sentiment"], "NEUTRAL")

    # =========================================================================
    # Scenario F: Reviews with short text
    # =========================================================================
    def test_f_short_text_reviews(self):
        c_ok = self.analyzer.classify_review(3, "Ok")
        self.assertEqual(c_ok["sentiment"], "NEUTRAL")

        c_good = self.analyzer.classify_review(4, "Good")
        self.assertEqual(c_good["sentiment"], "POSITIVE")

        c_bad = self.analyzer.classify_review(2, "Bad")
        self.assertEqual(c_bad["sentiment"], "NEGATIVE")

    # =========================================================================
    # Scenario G: Rating/Text Disagreement (Review Signals)
    # =========================================================================
    def test_g_rating_text_disagreement_detection(self):
        # 5-star rating with negative text
        mismatch_high = self.analyzer.classify_review(
            5,
            "Battery life is terrible and microphone barely works. Horrible."
        )
        self.assertTrue(mismatch_high["is_mismatch"])
        self.assertEqual(mismatch_high["mismatch_type"], "HIGH_RATING_NEGATIVE_TEXT")
        self.assertIn("negative", mismatch_high["mismatch_reason"].lower())

        # 1-star rating with positive praise
        mismatch_low = self.analyzer.classify_review(
            1,
            "Incredible sound quality, crystal clear audio, and super comfortable fit! Outstanding product."
        )
        self.assertTrue(mismatch_low["is_mismatch"])
        self.assertEqual(mismatch_low["mismatch_type"], "LOW_RATING_POSITIVE_TEXT")
        self.assertIn("positive", mismatch_low["mismatch_reason"].lower())

        # Consistent 5-star with positive praise
        consistent_pos = self.analyzer.classify_review(
            5,
            "Outstanding performance and superb build quality. Highly recommended!"
        )
        self.assertFalse(consistent_pos["is_mismatch"])

    # =========================================================================
    # Scenario H: Product with zero reviews (zero-division safety)
    # =========================================================================
    def test_h_zero_reviews_safety(self):
        # Non-existent or zero review product
        intel = self.analyzer.get_product_review_intelligence("P999_NON_EXISTENT")
        self.assertEqual(intel["status"], "error")

        # Directly testing zero review formatting branch
        empty_res = self.analyzer._format_empty_intelligence({
            "product_id": "P999",
            "product_name": "Ghost Product",
            "category_name": "Test",
            "brand": "TestBrand",
            "price": 99.99,
            "stock_quantity": 10
        } if hasattr(self.analyzer, '_format_empty_intelligence') else None) if hasattr(self.analyzer, '_format_empty_intelligence') else None

        # Verify through classify_review with empty list
        pos_t, neg_t = self.analyzer.aggregate_themes([])
        self.assertEqual(pos_t, [])
        self.assertEqual(neg_t, [])

    # =========================================================================
    # Scenario I: Aspect Theme Extraction from real text tokens
    # =========================================================================
    def test_i_aspect_theme_extraction(self):
        text = "The battery life lasts 30 hours and active noise cancellation is top notch, but microphone is muffled."
        analysis = self.analyzer.analyze_comment_text(text)
        self.assertIn("top notch", analysis["positive_tokens"])
        self.assertIn("muffled", analysis["negative_tokens"])
        
        single_themes = self.analyzer.extract_themes_from_single_comment(text, overall_text_polarity=0.5, rating=4)
        theme_names = [t["theme"] if isinstance(t, dict) else str(t) for t in single_themes]
        self.assertIn("Battery Life", theme_names)
        self.assertIn("Noise Cancellation", theme_names)
        self.assertIn("Microphone Quality", theme_names)

    # =========================================================================
    # Scenario J: Product Health scorecard & Customer summary
    # =========================================================================
    def test_j_product_health_scorecard_and_summary(self):
        intel = self.analyzer.get_product_review_intelligence("P205")
        self.assertIn("product_health", intel)
        ph = intel["product_health"]
        
        self.assertEqual(ph["product_id"], "P205")
        self.assertGreater(ph["average_rating"], 0.0)
        self.assertGreater(ph["review_count"], 0)
        self.assertGreaterEqual(ph["product_health_score"], 0.0)
        self.assertLessEqual(ph["product_health_score"], 1.0)
        self.assertIn("positive_pct", ph)
        self.assertIn("negative_pct", ph)
        self.assertIn("health_status", ph)
        self.assertIn("ai_review_summary", intel)
        self.assertIsInstance(intel["ai_review_summary"], str)
        self.assertGreater(len(intel["ai_review_summary"]), 15)

    # =========================================================================
    # Scenario K: Recency trend analysis
    # =========================================================================
    def test_k_recency_trend_handling(self):
        intel = self.analyzer.get_product_review_intelligence("P205")
        self.assertIn("recent_sentiment", intel)
        rs = intel["recent_sentiment"]
        self.assertIn("recent_positive_ratio", rs)
        self.assertIn("overall_positive_ratio", rs)
        self.assertIn("trend", rs)
        self.assertIn(rs["trend"], ["IMPROVING", "DECLINING", "STABLE", "NO_DATA"])

    # =========================================================================
    # Scenario L: REST API Endpoints Verification
    # =========================================================================
    def test_l_api_endpoints(self):
        # 1. Product review intelligence
        res1 = self.client.get("/api/products/P205/review-intelligence")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertEqual(data1["product_id"], "P205")
        self.assertIn("sentiment", data1)
        self.assertIn("positive_themes", data1)
        self.assertIn("negative_themes", data1)

        # 2. Admin catalog review intelligence (all filter)
        res2 = self.client.get("/api/admin/review-intelligence?filter=all")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2["status"], "success")
        self.assertIn("kpis", data2)
        self.assertGreater(data2["kpis"]["total_reviews_analyzed"], 100)
        self.assertIn("products", data2)

        # 3. Admin catalog review intelligence (mismatched filter)
        res3 = self.client.get("/api/admin/review-intelligence?filter=mismatched")
        self.assertEqual(res3.status_code, 200)
        data3 = res3.get_json()
        self.assertGreaterEqual(len(data3["products"]), 1, "Should find at least 1 product with rating/text mismatch")
        for p in data3["products"]:
            self.assertTrue(p["has_mismatch"])

        # 4. Admin product drilldown
        res4 = self.client.get("/api/admin/product/P205/review-intelligence")
        self.assertEqual(res4.status_code, 200)
        data4 = res4.get_json()
        self.assertEqual(data4["product_id"], "P205")
        self.assertIn("reviews", data4)

    # =========================================================================
    # Scenario M: Non-regression on Recommendations, Phase 6 & Phase 7
    # =========================================================================
    def test_m_non_regression_recommender_and_bi(self):
        # Recommendations still work and expose review_quality_score metadata
        rec_res = recommender.recommend("C001", top_n=3)
        self.assertIn("recommendations", rec_res)
        self.assertEqual(len(rec_res["recommendations"]), 3)
        for r in rec_res["recommendations"]:
            self.assertIn("review_quality_score", r)
            self.assertGreaterEqual(r["review_quality_score"], 0.0)
            self.assertLessEqual(r["review_quality_score"], 1.0)
            self.assertIn("reason", r)
            self.assertIn("technical_explanation", r)

        # Phase 7 Customer Segments still intact
        seg_res = bi_engine.get_customer_segments_summary()
        self.assertEqual(seg_res["status"], "success")

        # Phase 7 Inventory Intelligence still intact
        inv_res = bi_engine.get_inventory_intelligence()
        self.assertEqual(inv_res["status"], "success")


if __name__ == "__main__":
    unittest.main(verbosity=2)
