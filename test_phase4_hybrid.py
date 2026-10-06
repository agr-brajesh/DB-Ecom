"""
Phase 4 Automated Verification Suite: Hybrid Recommendation Pipeline
Tests multi-signal candidate generation, hybrid ranking, explainability metadata,
cold-start fallback, and persona diversity across customer profiles.
"""

import os
import sqlite3
import requests

BASE_URL = "http://127.0.0.1:5000"
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "ecommerce.db")

from ai.recommender import ProductRecommender
from ai.ranking import MultiSignalRanker, DEFAULT_WEIGHTS

def test_phase4_hybrid_pipeline():
    print("=== PHASE 4: HYBRID AI RECOMMENDATION PIPELINE VERIFICATION ===\n")
    
    # 1. Engine Initialization & In-Memory Catalog Cache
    recommender = ProductRecommender(DB_PATH)
    assert len(recommender.catalog.products) == 45, "Catalog cache incomplete"
    assert len(recommender.rules) > 0, "No Apriori rules discovered"
    assert len(recommender.product_popularity_scores) == 45, "Popularity scores not precomputed"
    print(f"[1] Engine initialized: {len(recommender.catalog.products)} products cached, {len(recommender.rules)} Apriori rules active.")

    # 2. Verify Configurable Weights
    assert recommender.ranker.weights["apriori"] == 0.40
    assert recommender.ranker.weights["search"] == 0.25
    assert recommender.ranker.weights["similarity"] == 0.20
    assert recommender.ranker.weights["popularity"] == 0.15
    print(f"[2] Configurable scoring weights verified: {recommender.ranker.weights}")

    # 3. Test Multi-Customer Persona Diversity
    test_customers = ["C101", "C102", "C103", "C104", "C107", "C108"]
    customer_recommendations = {}

    for cid in test_customers:
        res = recommender.recommend(cid, top_n=4)
        assert "error" not in res, f"Failed for customer {cid}"
        recs = res["recommendations"]
        assert len(recs) == 4, f"Expected 4 recs for {cid}, got {len(recs)}"
        customer_recommendations[cid] = [r["product_id"] for r in recs]

        # Verify Metadata Fields on each recommendation item
        for r in recs:
            assert "product_id" in r
            assert "score" in r and 0.0 <= r["score"] <= 1.0
            assert "algorithm" in r and len(r["algorithm"]) > 0
            assert "reason" in r and len(r["reason"]) > 0
            assert "apriori_score" in r and 0.0 <= r["apriori_score"] <= 1.0
            assert "search_score" in r and 0.0 <= r["search_score"] <= 1.0
            assert "similarity_score" in r and 0.0 <= r["similarity_score"] <= 1.0
            assert "popularity_score" in r and 0.0 <= r["popularity_score"] <= 1.0

        # Verify exclusion of already purchased products
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT oi.product_id FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.customer_id = ? AND o.order_status = 'COMPLETED';
        """, (cid,))
        bought = {row[0] for row in c.fetchall()}

        # Verify exclusion of items currently in active cart
        c.execute("SELECT product_id FROM shopping_cart WHERE customer_id = ?;", (cid,))
        in_cart = {row[0] for row in c.fetchall()}
        conn.close()

        for r in recs:
            assert r["product_id"] not in bought, f"Product {r['product_id']} was already purchased by {cid}!"
            assert r["product_id"] not in in_cart, f"Product {r['product_id']} is already in {cid}'s cart!"

    # Verify that different customers receive tailored, distinct recommendations
    assert customer_recommendations["C101"] != customer_recommendations["C103"], "C101 and C103 recommendations should differ"
    assert customer_recommendations["C103"] != customer_recommendations["C107"], "C103 and C107 recommendations should differ"
    assert customer_recommendations["C107"] != customer_recommendations["C108"], "C107 and C108 recommendations should differ"
    print(f"[3] Persona recommendation diversity verified across {len(test_customers)} customers.")

    # 4. Verify Search Intent Signal Activation (Customer C108 has journaling search intent)
    res_c108 = recommender.recommend("C108", top_n=4)
    search_driven = [r for r in res_c108["recommendations"] if r["search_score"] > 0.3]
    assert len(search_driven) > 0, "Expected search intent signal to fire for customer C108"
    print(f"[4] Search Intent signal verified: {search_driven[0]['product_name']} (Search Score: {search_driven[0]['search_score']:.2f})")

    # 5. Verify Apriori Association Signal Activation (Customer C103 gaming console co-purchases)
    res_c103 = recommender.recommend("C103", top_n=4)
    apriori_driven = [r for r in res_c103["recommendations"] if r["apriori_score"] > 0.8]
    assert len(apriori_driven) > 0, "Expected strong Apriori rule activation for customer C103"
    print(f"[5] Apriori signal verified: {apriori_driven[0]['product_name']} (Apriori Score: {apriori_driven[0]['apriori_score']:.2f})")

    # 6. Verify Cold-Start Fallback Behavior
    fallbacks = recommender.get_top_rated_fallback(exclude_ids={"P101"}, limit=3)
    assert len(fallbacks) == 3
    for fb in fallbacks:
        assert fb["product_id"] != "P101"
        assert fb["popularity_score"] > 0.0
        assert "Community" in fb["algorithm"]
    print(f"[6] Cold-start popularity fallback verified: top item '{fallbacks[0]['product_name']}' (Pop Score: {fallbacks[0]['popularity_score']:.2f})")

    # 7. Verify HTTP API Delivery over Flask Server
    r = requests.get(f"{BASE_URL}/api/recommendations/C103?top_n=3")
    assert r.status_code == 200
    json_data = r.json()
    assert json_data["status"] == "success"
    api_recs = json_data["data"]["recommendations"]
    assert len(api_recs) == 3
    assert api_recs[0]["product_id"] == customer_recommendations["C103"][0]
    print(f"[7] Live Flask endpoint /api/recommendations/C103 verified with 100% contract fidelity.")

    print("\n=== ALL PHASE 4 HYBRID AI VERIFICATIONS PASSED 100% ===")

if __name__ == "__main__":
    test_phase4_hybrid_pipeline()
