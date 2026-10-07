"""
Phase 5 Context-Aware Multi-Signal Hybrid Ranking Engine for NexusAI
Dynamically tunes recommendation scoring weights based on active customer shopping context:
  - Standard Browsing (Long-term purchase preferences)
  - Active Search Session (Short-term intent dominance)
  - Product Detail View (Contextual association & compatibility)
  - Active Cart / Checkout (Basket completion & complementary accessories)
  - Out-of-Stock Alternatives (Price proximity, similarity, community ratings)
  - Cold-Start Fallback (Popularity & community trust)
"""

from typing import List, Dict, Optional, Tuple

# Centralized Contextual Weight Profiles (Configurable in one place)
CONTEXT_WEIGHT_PROFILES = {
    "default": {  # General browsing / home
        "apriori": 0.40,
        "search": 0.25,
        "similarity": 0.20,
        "popularity": 0.15
    },
    "search_dominant": {  # Customer actively searching
        "apriori": 0.15,
        "search": 0.55,
        "similarity": 0.15,
        "popularity": 0.15
    },
    "product_view": {  # Customer viewing specific product
        "apriori": 0.45,
        "search": 0.05,
        "similarity": 0.40,
        "popularity": 0.10
    },
    "cart": {  # Populated cart / checkout basket completion
        "apriori": 0.55,
        "search": 0.05,
        "similarity": 0.30,
        "popularity": 0.10
    },
    "alternatives": {  # Out-of-stock product alternative comparison
        "apriori": 0.05,
        "search": 0.05,
        "similarity": 0.60,
        "popularity": 0.30
    },
    "cold_start": {  # Brand new customer with zero context
        "apriori": 0.00,
        "search": 0.00,
        "similarity": 0.00,
        "popularity": 1.00
    }
}

DEFAULT_WEIGHTS = CONTEXT_WEIGHT_PROFILES["default"]


class MultiSignalRanker:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.profiles = {k: dict(v) for k, v in CONTEXT_WEIGHT_PROFILES.items()}
        self.weights = dict(DEFAULT_WEIGHTS)
        if weights:
            self.weights.update(weights)
        self._normalize_weights(self.weights)

    def _normalize_weights(self, w_dict: Dict[str, float]):
        """Ensures that weights sum to exactly 1.0."""
        total = sum(w_dict.values())
        if total > 0:
            for k in w_dict:
                w_dict[k] = round(w_dict[k] / total, 4)

    def resolve_context_weights(self, context_type: Optional[str] = None,
                                has_product_view: bool = False,
                                has_cart: bool = False,
                                has_recent_search: bool = False,
                                has_history: bool = False) -> Tuple[str, Dict[str, float]]:
        """
        Determines the optimal contextual weighting profile based on active session signals.
        """
        if context_type and context_type in self.profiles:
            profile_name = context_type
        elif context_type == "alternatives":
            profile_name = "alternatives"
        elif has_product_view or context_type == "product_view":
            profile_name = "product_view"
        elif context_type == "cart":
            profile_name = "cart"
        elif has_recent_search:
            profile_name = "search_dominant"
        elif has_cart:
            profile_name = "cart"
        elif not has_history and not has_recent_search and not has_cart:
            profile_name = "cold_start"
        else:
            profile_name = "default"

        return profile_name, dict(self.profiles[profile_name])

    def compute_candidate_score(self, candidate: Dict, weights: Optional[Dict[str, float]] = None,
                                context_type: Optional[str] = None) -> Dict:
        """
        Computes composite final score and assigns structured recommendation type,
        explainability reasoning, and algorithm attribution.
        """
        w = weights or self.weights
        apriori_score = max(0.0, min(1.0, float(candidate.get("apriori_score", 0.0))))
        search_score = max(0.0, min(1.0, float(candidate.get("search_score", 0.0))))
        similarity_score = max(0.0, min(1.0, float(candidate.get("similarity_score", 0.0))))
        popularity_score = max(0.0, min(1.0, float(candidate.get("popularity_score", 0.0))))

        # Weighted Linear Combination using contextual weights
        raw_final = (
            w.get("apriori", 0.0) * apriori_score +
            w.get("search", 0.0) * search_score +
            w.get("similarity", 0.0) * similarity_score +
            w.get("popularity", 0.0) * popularity_score
        )

        stock = candidate.get("stock_quantity", 0)
        # Inventory awareness: If stock is 0, exclude from normal recommendations unless alternatives context
        if stock <= 0 and context_type != "alternatives":
            availability_factor = 0.0
        elif stock <= 0 and context_type == "alternatives":
            availability_factor = 0.0  # Alternatives MUST be in stock!
        else:
            availability_factor = 1.0

        final_score = round(raw_final * availability_factor, 4)

        # Signal Contribution Analysis for Explainability
        contributions = {
            "apriori": w.get("apriori", 0.0) * apriori_score,
            "search": w.get("search", 0.0) * search_score,
            "similarity": w.get("similarity", 0.0) * similarity_score,
            "popularity": w.get("popularity", 0.0) * popularity_score
        }
        dominant_signal = max(contributions, key=contributions.get)

        # Formulate human-friendly reason, recommendation type, and algorithm label
        rec_type, reason, algorithm = self._derive_explanation(
            dominant_signal=dominant_signal,
            apriori_score=apriori_score,
            search_score=search_score,
            similarity_score=similarity_score,
            candidate=candidate,
            context_type=context_type
        )

        return {
            "product_id": candidate["product_id"],
            "product_name": candidate.get("product_name", ""),
            "brand": candidate.get("brand", ""),
            "price": candidate.get("price", 0.0),
            "category_name": candidate.get("category_name", ""),
            "stock_quantity": stock,
            "score": final_score,
            "recommendation_type": rec_type,
            "algorithm": algorithm,
            "reason": reason,
            "apriori_score": round(apriori_score, 4),
            "search_score": round(search_score, 4),
            "similarity_score": round(similarity_score, 4),
            "popularity_score": round(popularity_score, 4),
            "signals": {
                "apriori_score": round(apriori_score, 4),
                "search_score": round(search_score, 4),
                "similarity_score": round(similarity_score, 4),
                "popularity_score": round(popularity_score, 4)
            },
            "avg_rating": candidate.get("avg_rating", 4.5),
            "review_count": candidate.get("review_count", 0),
            "confidence": candidate.get("confidence"),
            "lift": candidate.get("lift"),
            "support": candidate.get("support"),
            "matched_antecedents": candidate.get("matched_antecedents", []),
            "matched_search_query": candidate.get("matched_search_query"),
            "matched_reference_product": candidate.get("matched_reference_product")
        }

    def _derive_explanation(self, dominant_signal: str, apriori_score: float,
                            search_score: float, similarity_score: float,
                            candidate: Dict, context_type: Optional[str]) -> Tuple[str, str, str]:
        """Derives a transparent explainable AI statement and structured recommendation type."""
        ant_names = candidate.get("matched_antecedents", [])
        search_query = candidate.get("matched_search_query")
        ref_prod = candidate.get("matched_reference_product")
        avg_rating = candidate.get("avg_rating", 4.5)
        review_count = candidate.get("review_count", 0)
        conf = candidate.get("confidence")
        lift = candidate.get("lift")

        if context_type == "alternatives":
            rec_type = "BEST_ALTERNATIVES"
            reason = f"Top-rated available alternative ({avg_rating}/5 stars, {similarity_score*100:.0f}% feature similarity)"
            algorithm = "Context-Aware (In-Stock Product Alternative Matcher)"
        elif context_type == "frequently_bought_together" or (context_type == "product_view" and dominant_signal == "apriori" and apriori_score > 0.2):
            rec_type = "FREQUENTLY_BOUGHT_TOGETHER"
            ant_str = " + ".join(ant_names[:2]) if ant_names else (ref_prod or "viewed item")
            conf_str = f"Confidence: {conf*100:.0f}%, Lift: {lift:.1f}x" if conf and lift else f"Affinity: {apriori_score*100:.0f}%"
            reason = f"Frequently bought together with {ant_str} ({conf_str})"
            algorithm = "Context-Aware (Apriori Co-Purchase Affinity)"
        elif context_type == "complete_setup" or (context_type == "cart" and apriori_score > 0.2):
            rec_type = "COMPLETE_YOUR_SETUP"
            ant_str = " + ".join(ant_names[:2]) if ant_names else "items in your cart"
            reason = f"Completes your setup alongside {ant_str} (Verified Complement)"
            algorithm = "Context-Aware (Basket & Setup Completion Engine)"
        elif dominant_signal == "search" and search_score > 0.10 and search_query:
            rec_type = "BASED_ON_RECENT_SEARCH"
            reason = f"Matches your recent search query for '{search_query}' (Relevance: {search_score*100:.0f}%)"
            algorithm = "Context-Aware (Search Intent Matcher)"
        elif dominant_signal == "similarity" and similarity_score > 0.15 and ref_prod:
            if context_type == "product_view":
                rec_type = "BECAUSE_YOU_VIEWED"
                reason = f"Similar specs and category to {ref_prod} (Similarity: {similarity_score*100:.0f}%)"
            else:
                rec_type = "SIMILAR_PRODUCTS"
                reason = f"Complements and shares specs with your {ref_prod} (Similarity: {similarity_score*100:.0f}%)"
            algorithm = "Context-Aware (Content-Based Similarity)"
        elif dominant_signal == "apriori" and apriori_score > 0.15:
            rec_type = "PERSONALIZED_FOR_YOU"
            ant_str = " + ".join(ant_names[:2]) if ant_names else "your previous orders"
            reason = f"Frequently bought with {ant_str} (Affinity: {apriori_score*100:.0f}%)"
            algorithm = "Context-Aware (Apriori Market Basket Affinity)"
        else:
            rec_type = "TOP_PICK"
            reason = f"Community top-rated choice ({avg_rating}/5 stars across {review_count} verified reviews)"
            algorithm = "Context-Aware (Community Popularity & Quality)"

        return rec_type, reason, algorithm

    def rank(self, candidates: List[Dict], top_n: int = 4,
             weights: Optional[Dict[str, float]] = None,
             context_type: Optional[str] = None) -> List[Dict]:
        """Scores, filters, and ranks candidate products with inventory awareness."""
        scored = [
            self.compute_candidate_score(cand, weights=weights, context_type=context_type)
            for cand in candidates
        ]

        # For normal recommendations, exclude items with score == 0 (e.g. out of stock)
        valid = [c for c in scored if c["score"] > 0.0]

        # Sort by final score descending; break ties by rating then review count
        valid.sort(
            key=lambda x: (
                x["score"],
                x.get("avg_rating", 0.0),
                x.get("review_count", 0)
            ),
            reverse=True
        )
        return valid[:top_n]


# Module-level convenience function
resolve_context_weights = MultiSignalRanker.resolve_context_weights
