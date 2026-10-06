import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "ecommerce.db")

from ai.utils import CatalogMetadata, tokenize, cosine_similarity, min_max_scale
from ai.ranking import MultiSignalRanker, DEFAULT_WEIGHTS
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
        assert r["lift"] > 0
    
    # Test affinity score helper
    affinity = miner.compute_affinity(confidence=0.8, lift=10.0)
    assert 0.0 <= affinity <= 1.0, f"Affinity out of bounds: {affinity}"
    print(f"[PASS] Apriori mathematical & affinity verification succeeded (sample affinity: {affinity}).")

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

    # Test pairwise product similarity
    p2 = cb.products[1]["product_id"]
    pair_sim = cb.compute_product_similarity(p1, p2)
    assert 0.0 <= pair_sim <= 1.0
    print(f"[PASS] Content-based verification succeeded (Pairwise sim {p1} <-> {p2}: {pair_sim:.4f}).")

def test_multi_signal_ranker():
    print("\n--- 3. TESTING MULTI-SIGNAL HYBRID RANKER ---")
    ranker = MultiSignalRanker()
    assert abs(sum(ranker.weights.values()) - 1.0) < 0.001

    # Candidate with strong Apriori signal
    cand_apriori = {
        "product_id": "P101",
        "product_name": "Test Laptop",
        "stock_quantity": 50,
        "apriori_score": 0.90,
        "search_score": 0.10,
        "similarity_score": 0.20,
        "popularity_score": 0.80,
        "matched_antecedents": ["Laptop Case"]
    }
    scored = ranker.compute_candidate_score(cand_apriori)
    assert 0.0 <= scored["score"] <= 1.0
    assert "apriori_score" in scored and scored["apriori_score"] == 0.90
    assert "Apriori" in scored["algorithm"]
    print(f"Apriori candidate scored: {scored['score']} [{scored['algorithm']}]")

    # Candidate with strong Search Intent signal
    cand_search = {
        "product_id": "P102",
        "product_name": "Wireless Mouse",
        "stock_quantity": 30,
        "apriori_score": 0.0,
        "search_score": 0.85,
        "similarity_score": 0.10,
        "popularity_score": 0.70,
        "matched_search_query": "ergonomic mouse"
    }
    scored_s = ranker.compute_candidate_score(cand_search)
    assert 0.0 <= scored_s["score"] <= 1.0
    assert "Search" in scored_s["algorithm"]
    print(f"Search candidate scored: {scored_s['score']} [{scored_s['algorithm']}]")
    print("[PASS] Multi-Signal Ranker math and attribution verified.")

def test_hybrid_recommender():
    print("\n--- 4. TESTING HYBRID RECOMMENDER PIPELINE & CUSTOMER DIVERSITY ---")
    recommender = ProductRecommender(DB_PATH)

    test_customers = ["C101", "C102", "C103", "C104", "C107", "C108"]
    all_recs = {}

    for cid in test_customers:
        res = recommender.recommend(cid, top_n=4)
        assert "error" not in res, f"Error for customer {cid}: {res.get('error')}"
        recs = res["recommendations"]
        assert len(recs) == 4, f"Expected 4 recommendations for {cid}, got {len(recs)}"
        all_recs[cid] = [r["product_id"] for r in recs]

        # Verify all metadata fields present
        for r in recs:
            assert "product_id" in r
            assert "score" in r and 0.0 <= r["score"] <= 1.0
            assert "algorithm" in r and len(r["algorithm"]) > 0
            assert "reason" in r and len(r["reason"]) > 0
            assert "apriori_score" in r
            assert "search_score" in r
            assert "similarity_score" in r
            assert "popularity_score" in r

        # Verify exclusion of already purchased items
        hist_pids = set()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT oi.product_id FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.customer_id = ? AND o.order_status = 'COMPLETED';
        """, (cid,))
        hist_pids = {row[0] for row in cur.fetchall()}
        conn.close()

        for r in recs:
            assert r["product_id"] not in hist_pids, f"Customer {cid} was recommended already-purchased product {r['product_id']}!"

    # Verify recommendations differ across customers (diversity check)
    rec_c101 = all_recs["C101"]
    rec_c103 = all_recs["C103"]
    rec_c107 = all_recs["C107"]
    assert rec_c101 != rec_c103, "C101 and C103 received identical recommendations!"
    assert rec_c103 != rec_c107, "C103 and C107 received identical recommendations!"
    print(f"Customer recommendation diversity verified across {len(test_customers)} personas.")

    # Test non-existent customer
    bad_cust = recommender.recommend("NON_EXISTENT_ID")
    assert "error" in bad_cust
    print("Non-existent customer error handling verified:", bad_cust["error"])

    # Test cold-start fallback
    fallbacks = recommender.get_top_rated_fallback(exclude_ids={"P101", "P102"}, limit=3)
    assert len(fallbacks) == 3
    for fb in fallbacks:
        assert fb["product_id"] not in {"P101", "P102"}
        assert "Hybrid" in fb["algorithm"]
        assert fb["popularity_score"] > 0

    print("[PASS] Full hybrid recommendation pipeline, metadata, and fallback verification succeeded.")

if __name__ == "__main__":
    test_apriori_math()
    test_content_based_engine()
    test_multi_signal_ranker()
    test_hybrid_recommender()
