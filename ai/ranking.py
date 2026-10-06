"""
Multi-Signal Hybrid Ranking Engine for NexusAI
Combines normalized signals from Apriori Association Mining, Search Intent TF-IDF,
Content-Based Similarity, and Community Popularity into a single deterministic score.

Formula:
Final Score = 0.40 * Apriori Affinity
            + 0.25 * Search Intent
            + 0.20 * Product Similarity
            + 0.15 * Popularity / Quality
"""

from typing import List, Dict, Optional

# Configurable Weights for the Hybrid Scoring Model
DEFAULT_WEIGHTS = {
    "apriori": 0.40,
    "search": 0.25,
    "similarity": 0.20,
    "popularity": 0.15
}


class MultiSignalRanker:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = dict(DEFAULT_WEIGHTS)
        if weights:
            self.weights.update(weights)
        self._normalize_weights()

    def _normalize_weights(self):
        """Ensures that weights sum to exactly 1.0."""
        total = sum(self.weights.values())
        if total > 0:
            for k in self.weights:
                self.weights[k] = round(self.weights[k] / total, 4)

    def set_weights(self, new_weights: Dict[str, float]):
        """Allows dynamic adjustment of scoring weights for A/B testing or lab simulation."""
        self.weights.update(new_weights)
        self._normalize_weights()

    def compute_candidate_score(self, candidate: Dict) -> Dict:
        """
        Computes composite final score and generates human-readable explainability
        metadata for a candidate product based on its constituent signal strengths.
        """
        apriori_score = max(0.0, min(1.0, float(candidate.get("apriori_score", 0.0))))
        search_score = max(0.0, min(1.0, float(candidate.get("search_score", 0.0))))
        similarity_score = max(0.0, min(1.0, float(candidate.get("similarity_score", 0.0))))
        popularity_score = max(0.0, min(1.0, float(candidate.get("popularity_score", 0.0))))

        # Weighted Linear Combination
        raw_final = (
            self.weights["apriori"] * apriori_score +
            self.weights["search"] * search_score +
            self.weights["similarity"] * similarity_score +
            self.weights["popularity"] * popularity_score
        )

        # Inventory Availability Preference: penalize out-of-stock items
        stock = candidate.get("stock_quantity", 0)
        availability_factor = 1.0 if stock > 0 else 0.35
        final_score = round(raw_final * availability_factor, 4)

        # Signal Contribution Analysis for Explainability
        contributions = {
            "apriori": self.weights["apriori"] * apriori_score,
            "search": self.weights["search"] * search_score,
            "similarity": self.weights["similarity"] * similarity_score,
            "popularity": self.weights["popularity"] * popularity_score
        }
        dominant_signal = max(contributions, key=contributions.get)

        # Formulate human-friendly reason and algorithm label
        reason, algorithm = self._derive_explanation(
            dominant_signal=dominant_signal,
            apriori_score=apriori_score,
            search_score=search_score,
            similarity_score=similarity_score,
            candidate=candidate
        )

        return {
            "product_id": candidate["product_id"],
            "product_name": candidate.get("product_name", ""),
            "brand": candidate.get("brand", ""),
            "price": candidate.get("price", 0.0),
            "category_name": candidate.get("category_name", ""),
            "stock_quantity": stock,
            "score": final_score,
            "algorithm": algorithm,
            "reason": reason,
            "apriori_score": round(apriori_score, 4),
            "search_score": round(search_score, 4),
            "similarity_score": round(similarity_score, 4),
            "popularity_score": round(popularity_score, 4),
            "avg_rating": candidate.get("avg_rating", 4.5),
            "review_count": candidate.get("review_count", 0),
            "confidence": candidate.get("confidence"),
            "lift": candidate.get("lift")
        }

    def _derive_explanation(self, dominant_signal: str, apriori_score: float,
                            search_score: float, similarity_score: float,
                            candidate: Dict) -> tuple:
        """Derives a transparent explainable AI statement based on the dominant signal."""
        ant_names = candidate.get("matched_antecedents", [])
        search_query = candidate.get("matched_search_query")
        ref_prod = candidate.get("matched_reference_product")
        avg_rating = candidate.get("avg_rating", 4.5)
        review_count = candidate.get("review_count", 0)
        conf = candidate.get("confidence")
        lift = candidate.get("lift")

        if dominant_signal == "apriori" and apriori_score > 0.15:
            ant_str = " + ".join(ant_names[:2]) if ant_names else "items in your cart/history"
            conf_str = f"Confidence: {conf*100:.0f}%, Lift: {lift:.1f}x" if conf and lift else f"Affinity: {apriori_score*100:.0f}%"
            reason = f"Frequently bought together with {ant_str} ({conf_str})"
            algorithm = "Hybrid (Apriori Market Basket Association)"
        elif dominant_signal == "search" and search_score > 0.10 and search_query:
            reason = f"Matches your recent search query for '{search_query}' (Relevance: {search_score*100:.0f}%)"
            algorithm = "Hybrid (Search Intent Matching)"
        elif dominant_signal == "similarity" and similarity_score > 0.15 and ref_prod:
            reason = f"Complements and shares specs with your {ref_prod} (Similarity: {similarity_score*100:.0f}%)"
            algorithm = "Hybrid (Content-Based Similarity)"
        else:
            reason = f"Community top-rated choice ({avg_rating}/5 stars across {review_count} verified reviews)"
            algorithm = "Hybrid (Community Popularity & Ratings)"

        return reason, algorithm

    def rank(self, candidates: List[Dict], top_n: int = 4) -> List[Dict]:
        """Scores and ranks a list of candidate products in descending order."""
        scored = [self.compute_candidate_score(cand) for cand in candidates]
        # Sort by final score descending; break ties by rating then review count
        scored.sort(
            key=lambda x: (
                x["score"],
                x.get("avg_rating", 0.0),
                x.get("review_count", 0)
            ),
            reverse=True
        )
        return scored[:top_n]
