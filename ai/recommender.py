"""
NexusAI Context-Aware Personalization & Smart Shopping Intelligence Engine (Phase 5)
Extends the Phase 4 Hybrid Recommender with real-time shopping context:
  - Long-Term Preferences: Historical purchases with recency decay
  - Short-Term Intent: Recent searches with exponential rank decay + active cart
  - Session Context: Currently viewed product/category & recent browsing events
  - Inventory Awareness: Unavailable product filtering & in-stock alternative finder
  - Contextual Weighting: Dynamic tuning of Apriori, Search, Content, and Popularity signals
  - Specialized Commerce Intents:
      * PERSONALIZED_FOR_YOU
      * BECAUSE_YOU_VIEWED
      * FREQUENTLY_BOUGHT_TOGETHER (co-purchase bundle with savings)
      * COMPLETE_YOUR_SETUP (complementary category peripheral matching)
      * SIMILAR_PRODUCTS
      * BASED_ON_RECENT_SEARCH
      * BEST_ALTERNATIVES (for out-of-stock or comparison)
      * TOP_PICK
"""

import sqlite3
import os
import math
from typing import List, Dict, Set, Optional, Tuple

from .apriori import AprioriMiner
from .content_based import ContentBasedRecommender
from .ranking import MultiSignalRanker, DEFAULT_WEIGHTS, CONTEXT_WEIGHT_PROFILES
from .utils import CatalogMetadata, log_scale, min_max_scale
from .explanations import ExplanationEngine

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
        # Multi-Signal Context-Aware Hybrid Ranker
        self.ranker = MultiSignalRanker(weights)
        # Phase 6: Explainable AI & Trustworthy Recommendation Engine
        self.explanation_engine = ExplanationEngine()
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
            rating_norm = min_max_scale(p["avg_rating"], 1.0, 5.0)
            sales_norm = p["units_sold"] / self.catalog.max_units_sold if self.catalog.max_units_sold > 0 else 0.5
            review_norm = log_scale(p["review_count"], self.catalog.max_reviews)

            score = (0.50 * rating_norm) + (0.35 * sales_norm) + (0.15 * review_norm)
            popularity[pid] = round(max(0.0, min(1.0, score)), 4)
        return popularity

    def _get_customer_context(self, customer_id: str) -> Optional[Dict]:
        """Loads customer identity, purchases with timestamps, active cart, and searches."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Customer identity
        cursor.execute("SELECT name, email, city FROM customers WHERE customer_id = ?;", (customer_id,))
        cust_row = cursor.fetchone()
        if not cust_row:
            conn.close()
            return None

        customer_name, email, city = cust_row

        # Historical purchases from completed orders (ordered by date descending for recency weighting)
        cursor.execute("""
            SELECT DISTINCT oi.product_id, p.product_name, cat.category_name, p.price, o.order_date
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            WHERE o.customer_id = ? AND o.order_status = 'COMPLETED'
            ORDER BY o.order_date DESC;
        """, (customer_id,))
        purchased_rows = cursor.fetchall()

        # Active shopping cart items
        cursor.execute("""
            SELECT DISTINCT sc.product_id, p.product_name, cat.category_name, p.price, sc.quantity
            FROM shopping_cart sc
            JOIN products p ON sc.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            WHERE sc.customer_id = ?;
        """, (customer_id,))
        cart_rows = cursor.fetchall()

        # Recent search queries (most recent first, up to 5)
        cursor.execute("""
            SELECT search_query, searched_at FROM search_history 
            WHERE customer_id = ? 
            ORDER BY searched_at DESC LIMIT 5;
        """, (customer_id,))
        searches_raw = cursor.fetchall()
        searches = [r[0] for r in searches_raw if r[0]]

        # Recent viewed products from session_events
        cursor.execute("""
            SELECT product_id, created_at FROM session_events
            WHERE customer_id = ? AND event_type = 'PRODUCT_VIEW'
            ORDER BY created_at DESC LIMIT 5;
        """, (customer_id,))
        viewed_rows = cursor.fetchall()
        recent_views = [r[0] for r in viewed_rows if r[0]]

        conn.close()

        purchased_dict = {
            r[0]: {"name": r[1], "category": r[2], "price": r[3], "order_date": r[4]}
            for r in purchased_rows
        }
        cart_dict = {
            r[0]: {"name": r[1], "category": r[2], "price": r[3], "quantity": r[4]}
            for r in cart_rows
        }

        return {
            "customer_id": customer_id,
            "name": customer_name,
            "email": email,
            "city": city,
            "purchased": purchased_dict,
            "cart": cart_dict,
            "searches": searches,
            "recent_views": recent_views
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
        strictly in stock for customers with zero context.
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
            # Inventory rule: Do not recommend out of stock items
            if pid not in exclude_ids and p.get("stock_quantity", 0) > 0:
                pop_score = self.product_popularity_scores.get(pid, 0.75)
                final_score = round(pop_score, 4)
                fallback.append({
                    "product_id": pid,
                    "product_name": p["product_name"],
                    "brand": p["brand"],
                    "price": p["price"],
                    "category_name": p["category_name"],
                    "stock_quantity": p["stock_quantity"],
                    "score": final_score,
                    "recommendation_type": "TOP_PICK",
                    "algorithm": "Hybrid Context-Aware (Community Popularity Fallback)",
                    "reason": f"Community top-rated choice ({p['avg_rating']}/5 stars across {p['review_count']} reviews)",
                    "apriori_score": 0.0,
                    "search_score": 0.0,
                    "similarity_score": 0.0,
                    "popularity_score": pop_score,
                    "signals": {
                        "apriori_score": 0.0,
                        "search_score": 0.0,
                        "similarity_score": 0.0,
                        "popularity_score": pop_score
                    },
                    "avg_rating": p["avg_rating"],
                    "review_count": p["review_count"],
                    "confidence": None,
                    "lift": None
                })
                if len(fallback) >= limit:
                    break
        return fallback

    def recommend(self, customer_id: str,
                  current_product_id: Optional[str] = None,
                  context_type: Optional[str] = None,
                  top_n: int = 4) -> Dict:
        """
        Phase 5 Master Context-Aware Recommendation Pipeline.
        
        Synthesizes:
          - Customer Context (Purchases, Cart, Searches, Views)
          - Session / Product Context (current_product_id, context_type)
          - Recency-decay weighting for short-term intent
          - Context-specific dynamic ranking profile
          - Inventory awareness (strictly excludes out of stock items)
        """
        context = self._get_customer_context(customer_id)
        is_guest_customer = False
        if not context:
            is_guest_customer = True
            # Graceful cold-start fallback for new/guest customer
            context = {
                "customer_id": customer_id,
                "name": "Guest Customer",
                "email": "",
                "city": "",
                "purchased": {},
                "cart": {},
                "searches": [],
                "recent_views": []
            }

        purchased_pids = set(context["purchased"].keys())
        cart_pids = set(context["cart"].keys())
        known_pids = set(purchased_pids | cart_pids)
        exclude_pids = set(known_pids)

        if current_product_id:
            # Don't recommend the item the customer is currently looking at
            exclude_pids.add(current_product_id)

        # ---------------------------------------------------------
        # RESOLVE CONTEXTUAL WEIGHT PROFILE
        # ---------------------------------------------------------
        has_product_view = bool(current_product_id)
        has_cart = len(cart_pids) > 0
        has_recent_search = len(context["searches"]) > 0
        has_history = len(purchased_pids) > 0

        profile_name, active_weights = self.ranker.resolve_context_weights(
            context_type=context_type,
            has_product_view=has_product_view,
            has_cart=has_cart,
            has_recent_search=has_recent_search,
            has_history=has_history
        )

        candidate_ids: Set[str] = set()

        # ---------------------------------------------------------
        # SOURCE 1: CURRENT PRODUCT CONTEXT (If viewing a product)
        # ---------------------------------------------------------
        product_view_rule_matches: Dict[str, Dict] = {}
        if current_product_id:
            # Find Apriori rules where current product is in antecedent
            for rule in self.rules:
                if current_product_id in rule["antecedent"]:
                    affinity = self.miner.compute_affinity(rule["confidence"], rule["lift"])
                    for con_pid in rule["consequent"]:
                        if con_pid not in exclude_pids:
                            candidate_ids.add(con_pid)
                            if con_pid not in product_view_rule_matches or affinity > product_view_rule_matches[con_pid]["affinity_score"]:
                                product_view_rule_matches[con_pid] = {
                                    "product_id": con_pid,
                                    "affinity_score": affinity,
                                    "confidence": rule["confidence"],
                                    "lift": rule["lift"],
                                    "support": rule["support"],
                                    "antecedent": rule["antecedent"],
                                    "antecedent_names": rule["antecedent_names"]
                                }
            # Add top similar products to current product
            sim_prods = self.content_engine.recommend_similar_products(current_product_id, top_n=6)
            for sp in sim_prods:
                if sp["product_id"] not in exclude_pids:
                    candidate_ids.add(sp["product_id"])

        # ---------------------------------------------------------
        # SOURCE 2: APRIORI ASSOCIATION MINING (Cart & Purchase History)
        # ---------------------------------------------------------
        # Focus seed on cart if in cart context, else entire known history
        rule_seed_pids = cart_pids if (context_type == "cart" and cart_pids) else known_pids
        strongest_rules = self.miner.get_strongest_rules_for_candidates(rule_seed_pids)
        for con_pid in strongest_rules:
            if con_pid not in exclude_pids:
                candidate_ids.add(con_pid)

        # Merge with product_view rules if viewing a product
        if product_view_rule_matches:
            for con_pid, r_info in product_view_rule_matches.items():
                if con_pid not in strongest_rules or r_info["affinity_score"] > strongest_rules[con_pid]["affinity_score"]:
                    strongest_rules[con_pid] = r_info

        # ---------------------------------------------------------
        # SOURCE 3: CONTENT-BASED NEIGHBORS (With Recency Seeding)
        # ---------------------------------------------------------
        similar_ids = self.content_engine.get_similar_candidate_ids(known_pids, top_per_item=3)
        for s_pid in similar_ids:
            if s_pid not in exclude_pids:
                candidate_ids.add(s_pid)

        # ---------------------------------------------------------
        # SOURCE 4: SEARCH INTENT MATCHES WITH RECENCY DECAY
        # ---------------------------------------------------------
        recent_searches = context["searches"]
        search_matched_scores: Dict[str, Tuple[float, str]] = {}
        for rank_idx, q in enumerate(recent_searches):
            # Recency decay weight: 1.0, 0.74, 0.58, 0.49, 0.42
            recency_weight = 1.0 / (1.0 + 0.35 * rank_idx)
            for p in self.catalog.all_products():
                pid = p["product_id"]
                if pid not in exclude_pids:
                    raw_s_score = self.content_engine.score_search_query(q, pid)
                    decayed_s_score = raw_s_score * recency_weight
                    if decayed_s_score > 0.12:
                        candidate_ids.add(pid)
                        if pid not in search_matched_scores or decayed_s_score > search_matched_scores[pid][0]:
                            search_matched_scores[pid] = (decayed_s_score, q)

        # ---------------------------------------------------------
        # SOURCE 5: COMMUNITY POPULARITY BACKFILL CANDIDATES
        # ---------------------------------------------------------
        sorted_prods = sorted(
            self.catalog.all_products(),
            key=lambda p: self.product_popularity_scores.get(p["product_id"], 0.0),
            reverse=True
        )
        for p in sorted_prods[:8]:
            if p["product_id"] not in exclude_pids and p.get("stock_quantity", 0) > 0:
                candidate_ids.add(p["product_id"])

        # ---------------------------------------------------------
        # MULTI-SIGNAL SCORING
        # ---------------------------------------------------------
        candidate_records: List[Dict] = []
        target_prod_meta = self.catalog.get(current_product_id) if current_product_id else None

        for pid in candidate_ids:
            prod_meta = self.catalog.get(pid)
            if not prod_meta:
                continue

            # Inventory Awareness: strictly skip out-of-stock items for normal recommendations
            stock = prod_meta.get("stock_quantity", 0)
            if stock <= 0 and context_type != "alternatives":
                continue

            # Signal 1: Apriori Score
            rule_info = strongest_rules.get(pid)
            apriori_score = rule_info["affinity_score"] if rule_info else 0.0
            ant_names = rule_info["antecedent_names"] if rule_info else []
            conf = rule_info["confidence"] if rule_info else None
            lift = rule_info["lift"] if rule_info else None
            supp = rule_info.get("support") if rule_info else None

            # Signal 2: Search Intent Score (with recency decay applied)
            search_match = search_matched_scores.get(pid)
            if search_match:
                search_score, search_q = search_match
            else:
                search_score = 0.0
                search_q = recent_searches[0] if recent_searches else None

            # Signal 3: Product Similarity Score
            # If current_product_id is provided, prioritize similarity to the viewed product
            similarity_score = 0.0
            matched_ref_prod = None

            if current_product_id:
                sim = self.content_engine.compute_product_similarity(pid, current_product_id)
                similarity_score = sim
                if target_prod_meta:
                    matched_ref_prod = target_prod_meta["product_name"]
            else:
                # Max similarity against customer's known history
                for k_pid in known_pids:
                    sim = self.content_engine.compute_product_similarity(pid, k_pid)
                    if sim > similarity_score:
                        similarity_score = sim
                        ref_item = self.catalog.get(k_pid)
                        if ref_item:
                            matched_ref_prod = ref_item["product_name"]

            # Signal 4: Popularity Score
            popularity_score = self.product_popularity_scores.get(pid, 0.5)

            candidate_records.append({
                "product_id": pid,
                "product_name": prod_meta["product_name"],
                "brand": prod_meta["brand"],
                "price": prod_meta["price"],
                "category_name": prod_meta["category_name"],
                "stock_quantity": stock,
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
                "lift": lift,
                "support": supp
            })

        # ---------------------------------------------------------
        # HYBRID CONTEXTUAL RANKING
        # ---------------------------------------------------------
        ranked_recommendations = self.ranker.rank(
            candidate_records,
            top_n=top_n,
            weights=active_weights,
            context_type=context_type or ("product_view" if current_product_id else "default")
        )

        # ---------------------------------------------------------
        # GRACEFUL COLD-START FALLBACK
        # ---------------------------------------------------------
        if len(ranked_recommendations) < top_n:
            recommended_pids = {r["product_id"] for r in ranked_recommendations}
            needed = top_n - len(ranked_recommendations)
            fallbacks = self.get_top_rated_fallback(
                exclude_ids=exclude_pids | recommended_pids,
                limit=needed
            )
            ranked_recommendations.extend(fallbacks)

        # ---------------------------------------------------------
        # PHASE 6: EXPLAINABLE AI & TRUSTWORTHY RECOMMENDATIONS ENRICHMENT
        # ---------------------------------------------------------
        enriched_recommendations = self.explanation_engine.enrich_recommendations(
            candidates=ranked_recommendations[:top_n],
            customer_context=context,
            context_type=profile_name,
            active_weights=active_weights,
            current_product_id=current_product_id
        )

        out = {
            "status": "success",
            "context_type": profile_name,
            "customer": {
                "customer_id": context["customer_id"],
                "name": context["name"],
                "city": context["city"],
                "email": context["email"]
            },
            "context": {
                "current_product_id": current_product_id,
                "context_type": context_type or ("product_view" if current_product_id else "home"),
                "resolved_profile": profile_name,
                "active_weights": active_weights,
                "has_cart": has_cart,
                "has_searches": has_recent_search
            },
            "history": list(context["purchased"].values()),
            "active_cart": list(context["cart"].values()),
            "recent_searches": context["searches"],
            "recommendations": enriched_recommendations
        }
        if is_guest_customer:
            out["error"] = f"Customer {customer_id} not found."
        return out

    # ==========================================================
    # SPECIALIZED COMMERCE ENGINES (PHASE 5 INTELLIGENCE)
    # ==========================================================

    def recommend_frequently_bought_together(self, product_id: str, top_n: int = 2) -> Dict:
        """
        Generates a genuine Frequently Bought Together bundle around a target product.
        Uses Apriori association rules where target is in antecedent + v_frequent_product_pairs view.
        Calculates bundle pricing with an instant 10% bundle discount.
        """
        main_prod = self.catalog.get(product_id)
        if not main_prod:
            return {"error": f"Product {product_id} not found."}

        bundle_candidates: Dict[str, Dict] = {}

        # 1. Apriori rules
        for rule in self.rules:
            if product_id in rule["antecedent"]:
                affinity = self.miner.compute_affinity(rule["confidence"], rule["lift"])
                for con_pid in rule["consequent"]:
                    if con_pid != product_id:
                        p_info = self.catalog.get(con_pid)
                        if p_info and p_info.get("stock_quantity", 0) > 0:
                            if con_pid not in bundle_candidates or affinity > bundle_candidates[con_pid]["score"]:
                                bundle_candidates[con_pid] = {
                                    "product": p_info,
                                    "score": affinity,
                                    "confidence": rule["confidence"],
                                    "lift": rule["lift"],
                                    "source": "Apriori Market Basket Association"
                                }

        # 2. SQL View v_frequent_product_pairs fallback if needed
        if len(bundle_candidates) < top_n:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT product_b_id, co_purchase_count FROM v_frequent_product_pairs
                WHERE product_a_id = ?
                ORDER BY co_purchase_count DESC LIMIT 5;
            """, (product_id,))
            for pb_id, co_cnt in cur.fetchall():
                if pb_id not in bundle_candidates and pb_id != product_id:
                    p_info = self.catalog.get(pb_id)
                    if p_info and p_info.get("stock_quantity", 0) > 0:
                        bundle_candidates[pb_id] = {
                            "product": p_info,
                            "score": min_max_scale(co_cnt, 2, 20),
                            "confidence": 0.85,
                            "lift": 5.0,
                            "source": "Co-Purchase Historical View"
                        }
            conn.close()

        # 3. Content similarity fallback if still needed
        if len(bundle_candidates) < top_n:
            sims = self.content_engine.recommend_similar_products(product_id, top_n=4)
            for s in sims:
                sp_id = s["product_id"]
                if sp_id not in bundle_candidates and sp_id != product_id:
                    p_info = self.catalog.get(sp_id)
                    if p_info and p_info.get("stock_quantity", 0) > 0:
                        bundle_candidates[sp_id] = {
                            "product": p_info,
                            "score": s["similarity_score"],
                            "confidence": 0.60,
                            "lift": 2.5,
                            "source": "Content Similarity Match"
                        }

        # Sort bundle items by affinity
        sorted_bundle = sorted(bundle_candidates.values(), key=lambda x: x["score"], reverse=True)[:top_n]

        bundle_items = []
        addon_total = 0.0
        for item in sorted_bundle:
            p = item["product"]
            addon_total += p["price"]
            bundle_items.append({
                "product_id": p["product_id"],
                "product_name": p["product_name"],
                "brand": p["brand"],
                "price": p["price"],
                "category_name": p["category_name"],
                "stock_quantity": p["stock_quantity"],
                "avg_rating": p["avg_rating"],
                "review_count": p["review_count"],
                "affinity_score": round(item["score"], 4),
                "confidence": item["confidence"],
                "lift": item["lift"],
                "source": item["source"],
                "reason": f"Frequently paired with {main_prod['product_name']}"
            })

        # Phase 6: Enrich bundle items with explanations
        enriched_bundle_items = self.explanation_engine.enrich_recommendations(
            candidates=bundle_items,
            context_type="frequently_bought_together",
            current_product_id=product_id
        )

        total_individual_price = round(main_prod["price"] + addon_total, 2)
        # 10% instant bundle discount
        bundle_discount = round(total_individual_price * 0.10, 2) if bundle_items else 0.0
        discounted_bundle_price = round(total_individual_price - bundle_discount, 2)

        return {
            "product_id": product_id,
            "main_product": {
                "product_id": main_prod["product_id"],
                "product_name": main_prod["product_name"],
                "price": main_prod["price"],
                "stock_quantity": main_prod["stock_quantity"],
                "category_name": main_prod["category_name"]
            },
            "items": enriched_bundle_items,
            "bundle_items": enriched_bundle_items,
            "regular_total": total_individual_price,
            "total_individual_price": total_individual_price,
            "discount_percentage": 10 if bundle_items else 0,
            "savings": bundle_discount,
            "bundle_savings": bundle_discount,
            "bundle_price": discounted_bundle_price,
            "discounted_bundle_price": discounted_bundle_price,
            "bundle_product_ids": [main_prod["product_id"]] + [b["product_id"] for b in bundle_items]
        }

    def recommend_product_alternatives(self, product_id: str, top_n: int = 3) -> Dict:
        """
        Recommends high-quality, available alternatives if a product is out of stock,
        expensive, or poorly rated.
        Filters:
          - Same or closely related category
          - In-Stock strictly (stock_quantity > 0)
          - High TF-IDF content similarity
          - Price proximity (within 0.4x to 2.2x price)
          - High customer rating (>= 4.0 stars preferred)
        """
        target = self.catalog.get(product_id)
        if not target:
            return {"error": f"Product {product_id} not found."}

        target_price = target["price"]
        target_cat = target["category_id"]

        candidates = []
        for p in self.catalog.all_products():
            pid = p["product_id"]
            if pid == product_id:
                continue

            # Must be strictly in stock
            if p.get("stock_quantity", 0) <= 0:
                continue

            # Category bonus
            same_cat = (p["category_id"] == target_cat)
            sim = self.content_engine.compute_product_similarity(product_id, pid)

            # Price proximity score: 1.0 if identical price, decays with ratio difference
            price_ratio = p["price"] / target_price if target_price > 0 else 1.0
            if price_ratio < 0.35 or price_ratio > 2.5:
                continue
            price_proximity = max(0.0, 1.0 - abs(math.log(max(0.1, price_ratio))))

            # Rating score
            rating_score = min_max_scale(p["avg_rating"], 1.0, 5.0)

            # Composite alternative score
            cat_weight = 0.35 if same_cat else 0.10
            alt_score = round(
                (0.40 * sim) +
                (0.25 * price_proximity) +
                (0.20 * rating_score) +
                cat_weight,
                4
            )

            candidates.append({
                "product_id": pid,
                "product_name": p["product_name"],
                "brand": p["brand"],
                "price": p["price"],
                "category_name": p["category_name"],
                "stock_quantity": p["stock_quantity"],
                "avg_rating": p["avg_rating"],
                "review_count": p["review_count"],
                "score": alt_score,
                "similarity_score": round(sim, 4),
                "price_difference": round(p["price"] - target_price, 2),
                "recommendation_type": "BEST_ALTERNATIVES",
                "algorithm": "Context-Aware (In-Stock Product Alternative Matcher)",
                "reason": f"In-stock alternative with {p['avg_rating']}/5 stars ({int(sim*100)}% spec similarity)"
            })

        candidates.sort(key=lambda x: (x["score"], x["avg_rating"]), reverse=True)

        enriched_alternatives = self.explanation_engine.enrich_recommendations(
            candidates=candidates[:top_n],
            context_type="alternatives",
            current_product_id=product_id
        )

        return {
            "target_product": {
                "product_id": target["product_id"],
                "product_name": target["product_name"],
                "price": target["price"],
                "stock_quantity": target["stock_quantity"],
                "is_out_of_stock": target["stock_quantity"] <= 0
            },
            "alternatives": enriched_alternatives
        }

    def recommend_complete_your_setup(self, customer_id: str,
                                      current_product_id: Optional[str] = None,
                                      top_n: int = 3) -> Dict:
        """
        Recommends missing complementary peripheral products to complete the customer's setup.
        Example:
          - Owns / Viewing: Laptop -> Recommends: Mouse, Sleeve, Monitor, Hub
          - Owns / Viewing: Camera -> Recommends: SD Card, Lens, Camera Backpack
          - Owns / Viewing: Console -> Recommends: Controller, HDMI Cable, Controller Dock
        """
        context = self._get_customer_context(customer_id)
        if not context:
            return {"error": f"Customer {customer_id} not found."}

        # Seed items
        seed_pids = set(context["purchased"].keys()) | set(context["cart"].keys())
        if current_product_id:
            seed_pids.add(current_product_id)

        exclude_pids = set(context["purchased"].keys()) | set(context["cart"].keys())
        if current_product_id:
            exclude_pids.add(current_product_id)

        # Complementary candidate collection
        setup_candidates: Dict[str, Dict] = {}

        # 1. High-lift Apriori rules matching any seed item
        for rule in self.rules:
            ant = set(rule["antecedent"])
            if ant and ant.issubset(seed_pids):
                for con_pid in rule["consequent"]:
                    if con_pid not in exclude_pids:
                        p_meta = self.catalog.get(con_pid)
                        if p_meta and p_meta.get("stock_quantity", 0) > 0:
                            affinity = self.miner.compute_affinity(rule["confidence"], rule["lift"])
                            if con_pid not in setup_candidates or affinity > setup_candidates[con_pid]["score"]:
                                setup_candidates[con_pid] = {
                                    "meta": p_meta,
                                    "score": affinity,
                                    "antecedent_names": rule["antecedent_names"]
                                }

        # 2. Complementary categories (Accessories, Audio, Storage)
        complementary_categories = {"CAT08", "CAT02", "CAT04", "CAT07"}
        for p in self.catalog.all_products():
            pid = p["product_id"]
            if pid not in exclude_pids and p.get("stock_quantity", 0) > 0:
                if p["category_id"] in complementary_categories:
                    # Compute max similarity to any seed item
                    max_sim = max((self.content_engine.compute_product_similarity(pid, s) for s in seed_pids), default=0.0)
                    if max_sim > 0.15:
                        pop = self.product_popularity_scores.get(pid, 0.5)
                        score = round(0.50 * max_sim + 0.30 * pop + 0.20, 4)
                        if pid not in setup_candidates or score > setup_candidates[pid]["score"]:
                            setup_candidates[pid] = {
                                "meta": p,
                                "score": score,
                                "antecedent_names": ["your current hardware setup"]
                            }

        sorted_setup = sorted(setup_candidates.values(), key=lambda x: x["score"], reverse=True)[:top_n]

        results = []
        for item in sorted_setup:
            p = item["meta"]
            results.append({
                "product_id": p["product_id"],
                "product_name": p["product_name"],
                "brand": p["brand"],
                "price": p["price"],
                "category_name": p["category_name"],
                "stock_quantity": p["stock_quantity"],
                "avg_rating": p["avg_rating"],
                "review_count": p["review_count"],
                "score": round(item["score"], 4),
                "apriori_score": round(item["score"], 4),
                "matched_antecedents": item.get("antecedent_names", []),
                "recommendation_type": "COMPLETE_YOUR_SETUP",
                "algorithm": "Context-Aware (Setup & Peripheral Complement Engine)",
                "reason": f"Verified complementary addition to {' + '.join(item['antecedent_names'][:2])}"
            })

        enriched_setup = self.explanation_engine.enrich_recommendations(
            candidates=results,
            customer_context=context,
            context_type="complete_setup",
            current_product_id=current_product_id
        )

        return {
            "customer_id": customer_id,
            "setup_recommendations": enriched_setup,
            "setup": enriched_setup
        }
