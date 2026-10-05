import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "ecommerce.db")

from ai.apriori import AprioriMiner
from ai.content_based import ContentBasedRecommender
from ai.recommender import ProductRecommender

def test_apriori_math():
    print("--- 1. TESTING APRIORI MATH & RULE MINING ---")
    miner = AprioriMiner(DB_PATH)
    assert miner.total_transactions > 0, "No transactions loaded!"
    print(f"Total transactions: {miner.total_transactions}")

    itemsets = miner.find_frequent_itemsets(min_support=0.03)
    assert 1 in itemsets and len(itemsets[1]) > 0, "No 1-itemsets found!"
    assert 2 in itemsets and len(itemsets[2]) > 0, "No 2-itemsets found!"

    # Verify support math for an itemset
    sample_itemset, count = next(iter(itemsets[2].items()))
    calc_support = count / miner.total_transactions
    assert 0.0 < calc_support <= 1.0

    rules = miner.generate_rules(min_confidence=0.5, min_lift=1.2)
    assert len(rules) > 0, "No rules generated!"
    print(f"Generated {len(rules)} association rules.")

    for r in rules[:10]:
        assert "antecedent" in r and "consequent" in r
        assert r["confidence"] >= 0.5
        assert r["lift"] >= 1.2
        assert r["support"] > 0
        # verify lift formula: lift = confidence / P(consequent)
        # lift should be positive
        assert r["lift"] > 0
    print("[PASS] Apriori mathematical verification succeeded.")

def test_content_based_engine():
    print("\n--- 2. TESTING CONTENT-BASED SIMILARITY ---")
    cb = ContentBasedRecommender(DB_PATH)
    assert len(cb.products) > 0, "No products loaded in content engine!"
    assert len(cb.vocabulary) > 0, "Empty vocabulary in TF-IDF index!"
    assert len(cb.doc_vectors) == len(cb.products)

    # Test product similarity
    p1 = cb.products[0]["product_id"]
    sims = cb.recommend_similar_products(p1, top_n=3)
    assert len(sims) > 0
    for s in sims:
        assert s["product_id"] != p1, "Product recommended to itself!"
        assert 0.0 <= s["similarity_score"] <= 1.0001

    # Test search similarity
    search_recs = cb.search_similar("wireless keyboard ergonomic", top_n=3)
    assert len(search_recs) > 0
    print(f"Search query 'wireless keyboard ergonomic' top match: {search_recs[0]['product_name']} ({search_recs[0]['similarity_score']})")
    print("[PASS] Content-based verification succeeded.")

def test_hybrid_recommender():
    print("\n--- 3. TESTING HYBRID RECOMMENDER WORKFLOW & FALLBACKS ---")
    recommender = ProductRecommender(DB_PATH)

    # Test existing customer C101
    rec_c101 = recommender.recommend("C101", top_n=4)
    assert "error" not in rec_c101
    recs = rec_c101["recommendations"]
    assert len(recs) == 4
    # Ensure no recommended item is in customer's purchase or cart history
    history_ids = set(p["product_id"] if isinstance(p, dict) and "product_id" in p else k for k, p in rec_c101.get("purchased", {}).items()) if "purchased" in rec_c101 else set()
    # Or from the returned recommendations
    for r in recs:
        assert r["product_id"] not in [h.get("product_id") for h in rec_c101["history"] if "product_id" in h]
        assert "algorithm" in r and "reason" in r

    # Test non-existent customer
    bad_cust = recommender.recommend("NON_EXISTENT_ID")
    assert "error" in bad_cust
    print("Non-existent customer handled correctly:", bad_cust["error"])

    # Test cold-start customer (create a dummy customer in a test connection or check fallback directly)
    seen_ids = {"P101", "P102"}
    fallbacks = recommender.get_top_rated_fallback(exclude_ids=seen_ids, limit=3)
    assert len(fallbacks) == 3
    for fb in fallbacks:
        assert fb["product_id"] not in seen_ids
        assert fb["algorithm"] == "DBMS Analytics (Aggregated Ratings)"

    print("[PASS] Hybrid recommendation workflow and fallback verification succeeded.")

if __name__ == "__main__":
    test_apriori_math()
    test_content_based_engine()
    test_hybrid_recommender()
