"""
Hybrid AI Recommendation Engine
Combines Apriori Association Rules, Content-Based Cosine Similarity,
and DBMS Views to generate personalized product recommendations.

Workflow:
Customer DB -> Purchase History & Cart -> AI Rules / Content Similarity -> Recommended Products
"""

import sqlite3
import os
from typing import List, Dict, Set
from .apriori import AprioriMiner
from .content_based import ContentBasedRecommender

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "ecommerce.db")


class ProductRecommender:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        # Initialize AI components
        self.miner = AprioriMiner(db_path)
        self.rules = self.miner.generate_rules(min_confidence=0.5, min_lift=1.2)
        self.content_engine = ContentBasedRecommender(db_path)

    def _get_customer_context(self, customer_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get customer details
        cursor.execute("SELECT name, email, city FROM customers WHERE customer_id = ?;", (customer_id,))
        cust_row = cursor.fetchone()
        if not cust_row:
            conn.close()
            return None

        customer_name, email, city = cust_row

        # Get historical purchases from completed orders
        cursor.execute("""
            SELECT DISTINCT oi.product_id, p.product_name, cat.category_name, p.price
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            WHERE o.customer_id = ? AND o.order_status = 'COMPLETED';
        """, (customer_id,))
        purchased_rows = cursor.fetchall()

        # Get current shopping cart items
        cursor.execute("""
            SELECT DISTINCT sc.product_id, p.product_name, cat.category_name, p.price
            FROM shopping_cart sc
            JOIN products p ON sc.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            WHERE sc.customer_id = ?;
        """, (customer_id,))
        cart_rows = cursor.fetchall()

        # Get recent search queries
        cursor.execute("""
            SELECT search_query FROM search_history 
            WHERE customer_id = ? 
            ORDER BY searched_at DESC LIMIT 3;
        """, (customer_id,))
        searches = [r[0] for r in cursor.fetchall()]

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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.product_id, p.product_name, p.brand, p.price, cat.category_name, p.description,
                   ROUND(AVG(r.rating), 1) as avg_rating, COUNT(r.review_id) as review_count
            FROM products p
            JOIN categories cat ON p.category_id = cat.category_id
            LEFT JOIN reviews r ON p.product_id = r.product_id
            WHERE p.product_id = ?
            GROUP BY p.product_id;
        """, (product_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "product_id": row[0],
                "product_name": row[1],
                "brand": row[2],
                "price": row[3],
                "category_name": row[4],
                "description": row[5],
                "avg_rating": row[6] or 4.5,
                "review_count": row[7] or 0
            }
        return {}

    def get_top_rated_fallback(self, exclude_ids: Set[str], limit: int = 3) -> List[Dict]:
        """Cold-start fallback: Top rated products from DBMS analytical view."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product_id, product_name, category_name, price, avg_rating, review_count
            FROM v_product_performance
            WHERE avg_rating IS NOT NULL
            ORDER BY avg_rating DESC, review_count DESC;
        """)
        rows = cursor.fetchall()
        conn.close()

        fallback = []
        for r in rows:
            pid = r[0]
            if pid not in exclude_ids:
                fallback.append({
                    "product_id": pid,
                    "product_name": r[1],
                    "category_name": r[2],
                    "price": r[3],
                    "avg_rating": r[4],
                    "review_count": r[5],
                    "reason": "Top Rated Community Choice across all categories",
                    "algorithm": "DBMS Analytics (Aggregated Ratings)",
                    "score": round(float(r[4]), 2)
                })
                if len(fallback) >= limit:
                    break
        return fallback

    def recommend(self, customer_id: str, top_n: int = 3) -> Dict:
        """
        Generates top_n personalized recommendations for a customer.
        Workflow:
        1. Query customer purchase history + active cart
        2. Mine Apriori rules matching known items
        3. Exclude products already owned or in cart
        4. If insufficient items, query Content-Based / Search Intent
        5. Return clean structured output
        """
        context = self._get_customer_context(customer_id)
        if not context:
            return {"error": f"Customer {customer_id} not found."}

        purchased_pids = set(context["purchased"].keys())
        cart_pids = set(context["cart"].keys())
        known_pids = purchased_pids | cart_pids

        recommended_items: List[Dict] = []
        seen_pids: Set[str] = set(known_pids)

        # -----------------------------------------------------
        # 1. AI STEP: APRIORI ASSOCIATION RULE MINING
        # -----------------------------------------------------
        candidate_scores: Dict[str, Dict] = {}

        for rule in self.rules:
            ant = set(rule["antecedent"])
            # If the antecedent is a subset of items customer bought or has in cart
            if ant.issubset(known_pids):
                consequents = rule["consequent"]
                for con_pid in consequents:
                    if con_pid not in seen_pids:
                        score = rule["confidence"] * rule["lift"]
                        ant_names = [self.miner.product_name_map.get(p, p) for p in ant]
                        ant_str = " + ".join(ant_names)
                        
                        # Keep the highest scoring rule for this product
                        if con_pid not in candidate_scores or score > candidate_scores[con_pid]["score"]:
                            candidate_scores[con_pid] = {
                                "score": score,
                                "confidence": rule["confidence"],
                                "lift": rule["lift"],
                                "reason": f"Frequently bought with {ant_str} (Confidence: {rule['confidence']*100:.1f}%, Lift: {rule['lift']:.2f}x)",
                                "algorithm": "Apriori Association Rule Mining"
                            }

        # Sort candidate products by composite score (Lift * Confidence)
        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1]["score"], reverse=True)

        for pid, rule_meta in sorted_candidates[:top_n]:
            details = self._get_product_details(pid)
            if details:
                details.update({
                    "reason": rule_meta["reason"],
                    "algorithm": rule_meta["algorithm"],
                    "confidence": rule_meta["confidence"],
                    "lift": rule_meta["lift"],
                    "score": round(rule_meta["score"], 2)
                })
                recommended_items.append(details)
                seen_pids.add(pid)

        # -----------------------------------------------------
        # 2. AI STEP: CONTENT-BASED / SEARCH INTENT FALLBACK
        # -----------------------------------------------------
        if len(recommended_items) < top_n and context["searches"]:
            latest_search = context["searches"][0]
            cb_recs = self.content_engine.search_similar(latest_search, top_n=5)
            for item in cb_recs:
                pid = item["product_id"]
                if pid not in seen_pids:
                    details = self._get_product_details(pid)
                    if details:
                        details.update({
                            "reason": f"Matches recent search query: '{latest_search}'",
                            "algorithm": "Content-Based Filtering (Cosine Similarity)",
                            "score": item["similarity_score"]
                        })
                        recommended_items.append(details)
                        seen_pids.add(pid)
                        if len(recommended_items) >= top_n:
                            break

        # -----------------------------------------------------
        # 3. DBMS STEP: TOP RATED CATALOG FALLBACK
        # -----------------------------------------------------
        if len(recommended_items) < top_n:
            needed = top_n - len(recommended_items)
            fallbacks = self.get_top_rated_fallback(exclude_ids=seen_pids, limit=needed)
            recommended_items.extend(fallbacks)

        return {
            "customer": {
                "customer_id": context["customer_id"],
                "name": context["name"],
                "city": context["city"],
                "email": context["email"]
            },
            "history": list(context["purchased"].values()),
            "active_cart": list(context["cart"].values()),
            "recommendations": recommended_items[:top_n]
        }


def test_recommender():
    recommender = ProductRecommender()

    # Test Showcase Customer Profiles across multiple domains
    test_customers = ["C101", "C102", "C103", "C104", "C107", "C108"]

    print("\n" + "="*70)
    print(" AI RECOMMENDATION ENGINE EVALUATION ACROSS DOMAINS")
    print("="*70)

    for cid in test_customers:
        res = recommender.recommend(cid, top_n=3)
        cust = res["customer"]
        print(f"\nCustomer: {cust['customer_id']} ({cust['name']}, {cust['city']})")
        
        hist_names = [h['name'] for h in res['history']]
        cart_names = [c['name'] for c in res['active_cart']]
        print(f"  - Prior Purchases : {', '.join(hist_names) if hist_names else 'None'}")
        print(f"  - Active Cart     : {', '.join(cart_names) if cart_names else 'Empty'}")
        print("  Recommended Products:")
        for idx, rec in enumerate(res["recommendations"], 1):
            print(f"    {idx}. {rec['product_name']} (${rec['price']})")
            print(f"       [{rec['algorithm']}] -> {rec['reason']}")


if __name__ == "__main__":
    test_recommender()
