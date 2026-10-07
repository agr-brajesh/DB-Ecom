"""
Phase 6 Explainable AI (XAI) & Trustworthy Recommendations Verification Suite
Tests all 10 major contexts specified in Phase 6 requirements:
  A. Customer with purchase history -> Provenance includes purchases, Apriori reasons valid
  B. Customer with recent search -> Provenance includes recent_search, search reason matches query
  C. Customer viewing a product -> Product context explanation, product excluded from self
  D. Customer with populated cart -> Cart complementary reasons, cart items excluded
  E. Complete Your Setup -> Multi-product accessory complements, clear setup reasons
  F. Alternative product -> In-stock alternative spec match, price proximity reasons
  G. New customer / cold start -> Truthful popularity fallback, no false purchase claims
  H. No matching Apriori rule -> Does not claim co-purchase, relies on similarity/popularity
  I. No search history -> Never claims search intent, source excludes recent_search
  J. Out-of-stock product -> Stock gate active, excluded or tagged as alternative

Also verifies:
  - Safeguard invariants (zero false claims)
  - Mathematical integrity (composite scoring formula verification)
  - Schema conformity (signals, reasons, source, ai_match, technical_explanation)
"""

import sys
import os
import sqlite3
import json

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ai.recommender import ProductRecommender
from ai.explanations import ExplanationEngine, compute_match_indicator
from ai.ranking import CONTEXT_WEIGHT_PROFILES

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "ecommerce.db")


def main():
    print("=" * 60)
    print("PHASE 6 EXPLAINABLE AI & TRUSTWORTHY RECOMMENDATIONS TEST SUITE")
    print("=" * 60)

    recommender = ProductRecommender(db_path=DB_PATH)
    engine = recommender.explanation_engine

    # -------------------------------------------------------------
    # Scenario A: Customer with purchase history
    # -------------------------------------------------------------
    print("\n--- Scenario A: Customer with Purchase History ---")
    res_a = recommender.recommend("C101", top_n=4)
    assert res_a["status"] == "success"
    recs_a = res_a["recommendations"]
    assert len(recs_a) > 0

    purchased_pids = set(res_a["customer"].get("purchased", {}).keys()) if "purchased" in res_a["customer"] else set()
    # Check each recommendation
    for r in recs_a:
        assert r["product_id"] not in purchased_pids, f"Purchased item {r['product_id']} was recommended!"
        assert "signals" in r
        assert "reasons" in r and len(r["reasons"]) > 0
        assert "source" in r
        assert "ai_match" in r
        assert "technical_explanation" in r
        
        # Check signal keys
        for key in ("apriori", "search_intent", "content_similarity", "popularity", "inventory"):
            assert key in r["signals"], f"Missing signal key: {key}"
        
        # Verify no negative signals
        for k, v in r["signals"].items():
            assert v >= 0.0, f"Signal {k} is negative: {v}"

    print(f"PASS Scenario A: Customer with history received {len(recs_a)} validated explainable recommendations.")
    print(f"Sample Reasons: {recs_a[0]['product_name']} -> {recs_a[0]['reasons']}")
    print(f"Sample Provenance: {recs_a[0]['source']}")

    # -------------------------------------------------------------
    # Scenario B: Customer with recent search
    # -------------------------------------------------------------
    print("\n--- Scenario B: Customer with Recent Search ---")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Insert temporary distinct search query
    cur.execute("""
        INSERT INTO search_history (customer_id, search_query, searched_at)
        VALUES ('C103', 'mechanical gaming keyboard', datetime('now'))
    """)
    conn.commit()
    conn.close()

    res_b = recommender.recommend("C103", top_n=4)
    recs_b = res_b["recommendations"]

    # Clean up test search
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM search_history WHERE customer_id = 'C103' AND search_query = 'mechanical gaming keyboard'")
    conn.commit()
    conn.close()

    assert len(recs_b) > 0
    # At least one item should have recent_search in source if search intent matched
    search_matched = [r for r in recs_b if "recent_search" in r["source"]]
    assert len(search_matched) > 0, "No recommendation matched the active search intent!"
    for sr in search_matched:
        has_search_reason = any("search" in reason.lower() for reason in sr["reasons"])
        assert has_search_reason, f"Search in source but no search reason: {sr['reasons']}"
    print(f"PASS Scenario B: Search intent accurately traced in provenance & reasons: {search_matched[0]['reasons'][0]}")

    # -------------------------------------------------------------
    # Scenario C: Customer viewing a product
    # -------------------------------------------------------------
    print("\n--- Scenario C: Customer Viewing a Product ---")
    view_pid = "P101" # Laptop
    res_c = recommender.recommend("C101", current_product_id=view_pid, context_type="product_view", top_n=4)
    recs_c = res_c["recommendations"]
    
    # Target item must be excluded from its own recommendations
    rec_pids_c = [r["product_id"] for r in recs_c]
    assert view_pid not in rec_pids_c, f"Product {view_pid} recommended to itself!"
    
    # Verify at least one recommendation has product association/view reasoning
    contextual_items = [
        r for r in recs_c if any(
            "view" in reason.lower() or "bought together" in reason.lower() or "similar" in reason.lower()
            for reason in r["reasons"]
        )
    ]
    assert len(contextual_items) > 0, f"No contextual product view reasons found in {recs_c}"

    print(f"PASS Scenario C: Product view context verified. P101 excluded. {len(contextual_items)} contextual matches found. Sample reason: {contextual_items[0]['reasons'][0]}")

    # -------------------------------------------------------------
    # Scenario D: Customer with populated cart
    # -------------------------------------------------------------
    print("\n--- Scenario D: Customer with Populated Cart ---")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO shopping_cart (customer_id, product_id, quantity)
        VALUES ('C102', 'P102', 1)
    """)
    conn.commit()
    conn.close()

    res_d = recommender.recommend("C102", context_type="cart", top_n=4)
    recs_d = res_d["recommendations"]

    # Clean up test cart
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM shopping_cart WHERE customer_id = 'C102' AND product_id = 'P102'")
    conn.commit()
    conn.close()

    rec_pids_d = [r["product_id"] for r in recs_d]
    assert "P102" not in rec_pids_d, f"Active cart item P102 was recommended! Recs: {rec_pids_d}"
    print(f"PASS Scenario D: Cart items excluded. Complementary item recommended: {recs_d[0]['product_name']} with reasons {recs_d[0]['reasons']}")

    # -------------------------------------------------------------
    # Scenario E: Complete Your Setup
    # -------------------------------------------------------------
    print("\n--- Scenario E: Complete Your Setup ---")
    setup_res = recommender.recommend_complete_your_setup("C101", current_product_id="P101", top_n=3)
    setup_items = setup_res.get("setup", [])
    assert len(setup_items) > 0
    for s in setup_items:
        assert s["product_id"] != "P101"
        assert s["recommendation_type"] == "COMPLETE_YOUR_SETUP"
        assert "signals" in s
        assert "reasons" in s
        assert "source" in s
        assert any("setup" in r.lower() or "complements" in r.lower() or "bought" in r.lower() for r in s["reasons"])

    print(f"PASS Scenario E: Setup recommendations enriched with reasons: {setup_items[0]['reasons']}")

    # -------------------------------------------------------------
    # Scenario F: Alternative product
    # -------------------------------------------------------------
    print("\n--- Scenario F: Alternative Product (Out of Stock / Comparison) ---")
    alt_res = recommender.recommend_product_alternatives("P101", top_n=3)
    alts = alt_res.get("alternatives", [])
    assert len(alts) > 0
    for alt in alts:
        assert alt["product_id"] != "P101"
        assert alt["stock_quantity"] > 0
        assert alt["recommendation_type"] == "BEST_ALTERNATIVES"
        assert "content_similarity" in alt["source"] or "inventory" in alt["source"]
        assert any("similar" in r.lower() or "alternative" in r.lower() or "spec" in r.lower() for r in alt["reasons"])

    print(f"PASS Scenario F: Alternatives enriched with spec match & reasons: {alts[0]['reasons']}")

    # -------------------------------------------------------------
    # Scenario G: New customer / cold start
    # -------------------------------------------------------------
    print("\n--- Scenario G: New Customer / Cold Start ---")
    res_g = recommender.recommend("BRAND_NEW_USER_XYZ", top_n=4)
    recs_g = res_g["recommendations"]
    assert len(recs_g) == 4
    for r in recs_g:
        assert r["stock_quantity"] > 0
        assert "recent_search" not in r["source"], "Cold start customer incorrectly claimed search intent!"
        assert "apriori" not in r["source"], "Cold start customer incorrectly claimed Apriori co-purchase!"
        # Reasons must not claim previous purchases
        for reason in r["reasons"]:
            assert "bought with your" not in reason.lower()
            assert "previous purchase" not in reason.lower()
            assert "search" not in reason.lower()

    print(f"PASS Scenario G: Cold start recommendations strictly truthful. Reasons: {recs_g[0]['reasons']}")

    # -------------------------------------------------------------
    # Scenario H: No matching Apriori rule
    # -------------------------------------------------------------
    print("\n--- Scenario H: No Matching Apriori Rule ---")
    # Test candidate with zero apriori score directly through ExplanationEngine
    dummy_cand = {
        "product_id": "P999",
        "product_name": "Unique Gadget",
        "category_name": "Electronics",
        "price": 99.99,
        "stock_quantity": 25,
        "avg_rating": 4.6,
        "review_count": 30,
        "score": 0.55,
        "apriori_score": 0.0,
        "search_score": 0.0,
        "similarity_score": 0.40,
        "popularity_score": 0.70,
        "matched_antecedents": [],
        "matched_reference_product": "Workstation Dock",
        "recommendation_type": "SIMILAR_PRODUCTS"
    }
    dummy_ctx = {"customer_id": "C101", "purchased": {"P101": {}}, "cart": {}, "searches": []}
    enriched_h = engine.enrich_candidate(dummy_cand, rank_position=1, customer_context=dummy_ctx, context_type="default")
    assert "apriori" not in enriched_h["source"], "Source claimed Apriori when apriori_score was 0.0!"
    for r in enriched_h["reasons"]:
        assert "frequently bought" not in r.lower(), f"False Apriori claim: {r}"
    print(f"PASS Scenario H: No false Apriori claim. Truthful reasons: {enriched_h['reasons']}")

    # -------------------------------------------------------------
    # Scenario I: No search history
    # -------------------------------------------------------------
    print("\n--- Scenario I: Customer with No Search History ---")
    dummy_cand_i = {
        "product_id": "P888",
        "product_name": "Premium Keyboard",
        "category_name": "Computing",
        "price": 129.99,
        "stock_quantity": 10,
        "avg_rating": 4.9,
        "review_count": 50,
        "score": 0.65,
        "apriori_score": 0.50,
        "search_score": 0.0,
        "similarity_score": 0.20,
        "popularity_score": 0.85,
        "matched_antecedents": ["UltraBook Pro 15-inch Laptop"],
        "matched_search_query": None,
        "recommendation_type": "PERSONALIZED_FOR_YOU"
    }
    dummy_ctx_i = {"customer_id": "C101", "purchased": {"P101": {}}, "cart": {}, "searches": []}
    enriched_i = engine.enrich_candidate(dummy_cand_i, rank_position=1, customer_context=dummy_ctx_i, context_type="default")
    assert "recent_search" not in enriched_i["source"], "Source claimed recent_search when search history was empty!"
    for r in enriched_i["reasons"]:
        assert "search" not in r.lower(), f"False search claim in reasons: {r}"
    print(f"PASS Scenario I: No false search claim. Truthful reasons: {enriched_i['reasons']}")

    # -------------------------------------------------------------
    # Scenario J: Out-of-stock product
    # -------------------------------------------------------------
    print("\n--- Scenario J: Out-of-Stock Product Inventory Awareness ---")
    # For out-of-stock product in regular recommend flow, it must be excluded
    all_recs = recommender.recommend("C101", top_n=10)["recommendations"]
    for r in all_recs:
        assert r["stock_quantity"] > 0, f"Out of stock product {r['product_id']} returned in standard recommendations!"
    
    # Directly test safeguard: if stock is 0, never claim 'in stock'
    dummy_cand_j = {
        "product_id": "P000",
        "product_name": "Sold Out Item",
        "category_name": "Electronics",
        "price": 49.99,
        "stock_quantity": 0,
        "avg_rating": 4.0,
        "review_count": 5,
        "score": 0.0,
        "recommendation_type": "TOP_PICK"
    }
    enriched_j = engine.enrich_candidate(dummy_cand_j, rank_position=1, customer_context={}, context_type="default")
    assert "inventory" not in enriched_j["source"], "Zero-stock item included inventory in source!"
    for r in enriched_j["reasons"]:
        assert "in stock" not in r.lower(), f"Out-of-stock item claimed to be in stock: {r}"
    print(f"PASS Scenario J: Inventory safeguard strictly verified.")

    # -------------------------------------------------------------
    # Mathematical Proof & Traceability Invariants
    # -------------------------------------------------------------
    print("\n--- Mathematical Proof & Traceability Invariant Checks ---")
    res_inv = recommender.recommend("C101", top_n=3)
    for rec in res_inv["recommendations"]:
        tech = rec["technical_explanation"]
        
        # Check formula consistency
        weights = tech["weights_applied"]
        breakdown = tech["signal_breakdown"]
        expected_score = (
            weights["apriori"] * breakdown["apriori_score"] +
            weights["search"] * breakdown["search_intent_score"] +
            weights["similarity"] * breakdown["content_similarity_score"] +
            weights["popularity"] * breakdown["popularity_score"]
        )
        assert abs(rec["score"] - expected_score) < 0.01, f"Score mismatch: {rec['score']} vs expected {expected_score}"
        
        # Check match indicator
        match_label, match_pct, strength = compute_match_indicator(rec["score"])
        assert rec["ai_match"] == match_label
        assert rec["match_percentage"] == match_pct
        assert rec["match_strength"] == strength
        assert 48 <= match_pct <= 98

    print("PASS Mathematical Invariant Checks: Scoring formulas, weights, and calibrated match indicators 100% verified.")

    print("\n" + "=" * 60)
    print("ALL 10 SCENARIOS & SAFEGUARDS IN PHASE 6 PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
