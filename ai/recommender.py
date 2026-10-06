"""
NexusAI Hybrid AI Recommendation Engine (Phase 4 Modular Architecture)
Combines:
  1. Apriori Association Rule Mining (Market basket co-purchase patterns)
  2. TF-IDF Search Intent Matching (Customer recent keyword queries)
  3. Content-Based Cosine Similarity (Product attribute and catalog similarity)
  4. DBMS Community Popularity & Quality (Normalized ratings, reviews, and units sold)

Pipeline Flow:
Customer Context -> Multi-Source Candidate Generation -> Multi-Signal Scoring -> Hybrid Ranking -> Top-N Recommendations
"""

import sqlite3
import os
import math
from typing import List, Dict, Set, Optional

from .apriori import AprioriMiner
from .content_based import ContentBasedRecommender
from .ranking import MultiSignalRanker, DEFAULT_WEIGHTS
from .utils import CatalogMetadata, log_scale, min_max_scale

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "ecommerce.db")


class ProductRecommender:
    def __init__(self, db_path: str = DB_PATH, weights: Optional[Dict[str, float]] = None):
        self.db_path = db_path
        # In-memory shared catalog cache
        self.catalog = CatalogMetadata(db_path)
        # Apriori Association Rule Miner
        self.miner = AprioriMiner(db_path)
        self.rules = self.miner.generate_rules(min_confidence=0.5, min_lift=1.2)
        # Content-Based TF-IDF Engine
        self.content_engine = ContentBasedRecommender(db_path)
        # Multi-Signal Hybrid Ranker
        self.ranker = MultiSignalRanker(weights)
        # Precompute normalized popularity scores for all products
        self.product_popularity_scores: Dict[str, float] = self._precompute_popularity()

    def _precompute_popularity(self) -> Dict[str, float]:
        """
        Precomputes a normalized community popularity/quality score in [0.0, 1.0]
        for every product in the catalog based on aggregated rating, sales, and reviews.
        """
        popularity: Dict[str, float] = {}
        for p in self.catalog.all_products():
            pid = p["product_id"]
            # Rating factor: 1.0 - 5.0 -> 0.0 - 1.0
            rating_norm = min_max_scale(p["avg_rating"], 1.0, 5.0)
            # Sales volume factor
            sales_norm = p["units_sold"] / self.catalog.max_units_sold if self.catalog.max_units_sold > 0 else 0.5
            # Review count factor (logarithmic to handle variance)
            review_norm = log_scale(p["review_count"], self.catalog.max_reviews)

            # Combined popularity score
            score = (0.50 * rating_norm) + (0.35 * sales_norm) + (0.15 * review_norm)
            popularity[pid] = round(max(0.0, min(1.0, score)), 4)
        return popularity

    def _get_customer_context(self, customer_id: str) -> Optional[Dict]:
        """Loads complete customer context in a single database connection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Customer identity
        cursor.execute("SELECT name, email, city FROM customers WHERE customer_id = ?;", (customer_id,))
        cust_row = cursor.fetchone()
        if not cust_row:
            conn.close()
            return None

        customer_name, email, city = cust_row

        # Historical purchases from completed orders
        cursor.execute("""
            SELECT DISTINCT oi.product_id, p.product_name, cat.category_name, p.price
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            WHERE o.customer_id = ? AND o.order_status = 'COMPLETED';
        """, (customer_id,))
        purchased_rows = cursor.fetchall()

        # Active shopping cart items
        cursor.execute("""
            SELECT DISTINCT sc.product_id, p.product_name, cat.category_name, p.price
            FROM shopping_cart sc
            JOIN products p ON sc.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            WHERE sc.customer_id = ?;
        """, (customer_id,))
        cart_rows = cursor.fetchall()

        # Recent search queries (up to 5)
        cursor.execute("""
            SELECT search_query FROM search_history 
            WHERE customer_id = ? 
            ORDER BY searched_at DESC LIMIT 5;
        """, (customer_id,))
        searches = [r[0] for r in cursor.fetchall() if r[0]]

        conn.close()

        purchased_dict = {r[0]: {"name": r[1], "category": r[2], "price": r[3]} for r in purchased_rows}
        cart_dict = {r[0]: {"name": r[1], "category": r[2], "price": r[3]} for r in cart_rows}

        return {
            "customer_id": customer_id,
            "name": customer_name,
            "email": email,
            "city": city,
            "purchased": purchased_dict,
            "cart": cart_dict,
            "searches": searches
        }

    def _get_product_details(self, product_id: str) -> Dict:
        """Cached product detail lookup preserving backward compatibility."""
        p = self.catalog.get(product_id)
        if p:
            return dict(p)
        return {}

    def get_top_rated_fallback(self, exclude_ids: Set[str], limit: int = 4) -> List[Dict]:
        """
        Graceful cold-start fallback returning highest popularity products
        for customers with zero history or zero rule activations.
        """
        sorted_prods = sorted(
            self.catalog.all_products(),
            key=lambda p: (
                self.product_popularity_scores.get(p["product_id"], 0.0),
                p["avg_rating"],
                p["units_sold"]
            ),
            reverse=True
        )

        fallback = []
        for p in sorted_prods:
            pid = p["product_id"]
            if pid not in exclude_ids:
                pop_score = self.product_popularity_scores.get(pid, 0.75)
                # Raw final score based strictly on popularity weight
                final_score = round(self.ranker.weights["popularity"] * pop_score, 4)
                fallback.append({
                    "product_id": pid,
                    "product_name": p["product_name"],
                    "brand": p["brand"],
                    "price": p["price"],
                    "category_name": p["category_name"],
                    "stock_quantity": p["stock_quantity"],
                    "score": final_score,
                    "algorithm": "Hybrid (Community Popularity Fallback)",
                    "reason": f"Community top-rated choice ({p['avg_rating']}/5 stars across {p['review_count']} reviews)",
                    "apriori_score": 0.0,
                    "search_score": 0.0,
                    "similarity_score": 0.0,
                    "popularity_score": pop_score,
                    "avg_rating": p["avg_rating"],
                    "review_count": p["review_count"],
                    "confidence": None,
                    "lift": None
                })
                if len(fallback) >= limit:
                    break
        return fallback

    def recommend(self, customer_id: str, top_n: int = 4) -> Dict:
        """
        Executes the full Phase 4 Hybrid Recommendation Pipeline.
        
        Steps:
        1. Retrieve Customer Context (Purchases, Cart, Search Intent).
        2. Candidate Generation across 4 distinct sources.
        3. Exclude already purchased and cart items.
        4. Multi-Signal Scoring (Apriori, Search, Content, Popularity).
        5. Deterministic Hybrid Ranking with explainability.
        6. Graceful fallback if candidate pool is insufficient.
        """
        context = self._get_customer_context(customer_id)
        if not context:
            return {"error": f"Customer {customer_id} not found."}

        purchased_pids = set(context["purchased"].keys())
        cart_pids = set(context["cart"].keys())
        known_pids = purchased_pids | cart_pids
        exclude_pids = set(known_pids)

        candidate_ids: Set[str] = set()

        # ---------------------------------------------------------
        # SOURCE 1: APRIORI ASSOCIATION MINING
        # ---------------------------------------------------------
        strongest_rules = self.miner.get_strongest_rules_for_candidates(known_pids)
        for con_pid in strongest_rules:
            if con_pid not in exclude_pids:
                candidate_ids.add(con_pid)

        # ---------------------------------------------------------
        # SOURCE 2: CONTENT-BASED NEAREST NEIGHBORS
        # ---------------------------------------------------------
        similar_ids = self.content_engine.get_similar_candidate_ids(known_pids, top_per_item=3)
        for s_pid in similar_ids:
            if s_pid not in exclude_pids:
                candidate_ids.add(s_pid)

        # ---------------------------------------------------------
        # SOURCE 3: RECENT SEARCH INTENT MATCHES
        # ---------------------------------------------------------
        recent_searches = context["searches"]
        search_matched_scores: Dict[str, Tuple[float, str]] = {}
        for q in recent_searches:
            for p in self.catalog.all_products():
                pid = p["product_id"]
                if pid not in exclude_pids:
                    s_score = self.content_engine.score_search_query(q, pid)
                    if s_score > 0.15:
                        candidate_ids.add(pid)
                        if pid not in search_matched_scores or s_score > search_matched_scores[pid][0]:
                            search_matched_scores[pid] = (s_score, q)

        # ---------------------------------------------------------
        # SOURCE 4: POPULAR / TOP-RATED BACKFILL CANDIDATES
        # ---------------------------------------------------------
        sorted_prods = sorted(
            self.catalog.all_products(),
            key=lambda p: self.product_popularity_scores.get(p["product_id"], 0.0),
            reverse=True
        )
        for p in sorted_prods[:8]:
            if p["product_id"] not in exclude_pids:
                candidate_ids.add(p["product_id"])

        # ---------------------------------------------------------
        # MULTI-SIGNAL SCORING
        # ---------------------------------------------------------
        candidate_records: List[Dict] = []

        for pid in candidate_ids:
            prod_meta = self.catalog.get(pid)
            if not prod_meta:
                continue

            # Signal 1: Apriori Score
            rule_info = strongest_rules.get(pid)
            apriori_score = rule_info["affinity_score"] if rule_info else 0.0
            ant_names = rule_info["antecedent_names"] if rule_info else []
            conf = rule_info["confidence"] if rule_info else None
            lift = rule_info["lift"] if rule_info else None

            # Signal 2: Search Intent Score
            search_match = search_matched_scores.get(pid)
            if search_match:
                search_score, search_q = search_match
            else:
                search_score = 0.0
                search_q = recent_searches[0] if recent_searches else None

            # Signal 3: Product Similarity Score (Max similarity to any known product)
            similarity_score = 0.0
            matched_ref_prod = None
            for k_pid in known_pids:
                sim = self.content_engine.compute_product_similarity(pid, k_pid)
                if sim > similarity_score:
                    similarity_score = sim
                    ref_item = self.catalog.get(k_pid)
                    if ref_item:
                        matched_ref_prod = ref_item["product_name"]

            # Signal 4: Popularity / Quality Score
            popularity_score = self.product_popularity_scores.get(pid, 0.5)

            candidate_records.append({
                "product_id": pid,
                "product_name": prod_meta["product_name"],
                "brand": prod_meta["brand"],
                "price": prod_meta["price"],
                "category_name": prod_meta["category_name"],
                "stock_quantity": prod_meta["stock_quantity"],
                "avg_rating": prod_meta["avg_rating"],
                "review_count": prod_meta["review_count"],
                "apriori_score": apriori_score,
                "search_score": search_score,
                "similarity_score": similarity_score,
                "popularity_score": popularity_score,
                "matched_antecedents": ant_names,
                "matched_search_query": search_q,
                "matched_reference_product": matched_ref_prod,
                "confidence": conf,
                "lift": lift
            })

        # ---------------------------------------------------------
        # HYBRID RANKING
        # ---------------------------------------------------------
        ranked_recommendations = self.ranker.rank(candidate_records, top_n=top_n)

        # ---------------------------------------------------------
        # COLD-START / INSUFFICIENT CANDIDATE FALLBACK
        # ---------------------------------------------------------
        if len(ranked_recommendations) < top_n:
            recommended_pids = {r["product_id"] for r in ranked_recommendations}
            needed = top_n - len(ranked_recommendations)
            fallbacks = self.get_top_rated_fallback(
                exclude_ids=exclude_pids | recommended_pids,
                limit=needed
            )
            ranked_recommendations.extend(fallbacks)

        return {
            "customer": {
                "customer_id": context["customer_id"],
                "name": context["name"],
                "city": context["city"],
                "email": context["email"]
            },
            "history": list(context["purchased"].values()),
            "active_cart": list(context["cart"].values()),
            "recent_searches": context["searches"],
            "scoring_weights": self.ranker.weights,
            "recommendations": ranked_recommendations[:top_n]
        }


def test_recommender():
    recommender = ProductRecommender()
    test_customers = ["C101", "C102", "C103", "C104", "C107", "C108"]

    print("\n" + "="*80)
    print(" NEXUSAI PHASE 4 HYBRID AI RECOMMENDATION PIPELINE EVALUATION")
    print("="*80)
    print(f"Active Weights: {recommender.ranker.weights}\n")

    for cid in test_customers:
        res = recommender.recommend(cid, top_n=3)
        cust = res["customer"]
        print(f"Customer: {cust['customer_id']} ({cust['name']}, {cust['city']})")
        print(f"  - Prior Purchases : {len(res['history'])} item(s)")
        print(f"  - Active Cart     : {len(res['active_cart'])} item(s)")
        print(f"  - Recent Searches : {res.get('recent_searches', [])}")
        print("  Top Recommendations:")
        for idx, rec in enumerate(res["recommendations"], 1):
            print(f"    {idx}. {rec['product_name']} (${rec['price']}) - Final Score: {rec['score']}")
            print(f"       Signals -> Apriori: {rec['apriori_score']:.2f} | Search: {rec['search_score']:.2f} | Similarity: {rec['similarity_score']:.2f} | Pop: {rec['popularity_score']:.2f}")
            print(f"       [{rec['algorithm']}] -> {rec['reason']}\n")


if __name__ == "__main__":
    test_recommender()
