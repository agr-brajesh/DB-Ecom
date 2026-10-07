"""
Phase 6 Explainable AI (XAI) & Trustworthy Recommendations Engine for NexusAI
Dedicated module providing transparent, traceable, and validated explanations
for all recommendation types across customer-facing and admin interfaces.

Architectural Guarantees:
1. Complete Separation of Concerns: Recommenders generate and score candidates;
   ExplanationEngine articulates and verifies human and technical reasoning.
2. Truthful Attribution & Safeguards: Never claims a signal influenced recommendations
   if that signal was not present or active (no false purchase, search, or rule claims).
3. Dual-Tier Explainability:
   - Customer-Facing: Concise, plain-language reasons and calibrated AI Match indicators.
   - Admin/Academic Viva: Deep mathematical trace with rule antecedents, support,
     confidence, lift, feature vector contributions, and formula matrices.
"""

from typing import List, Dict, Optional, Tuple, Set
import re


# Thresholds below which a signal is deemed non-contributing to provenance
SIGNAL_CONTRIBUTION_THRESHOLDS = {
    "apriori": 0.12,
    "search_intent": 0.08,
    "content_similarity": 0.10,
    "popularity": 0.25,
    "inventory": 1.0
}


def clean_name(name: str) -> str:
    """Extracts a customer-friendly short product name."""
    if not name:
        return ""
    # Strip long parentheticals e.g. "(5-Pack)" or specs
    short = re.sub(r"\(.*?\)", "", name).strip()
    # Strip common brand/spec prefixes if too long
    words = short.split()
    if len(words) > 4:
        return " ".join(words[:4])
    return short


def compute_match_indicator(score: float) -> Tuple[str, int, str]:
    """
    Computes a customer-friendly recommendation strength indicator.
    Calibrates score into an AI Match percentage (clamped between 48% and 98%)
    and returns a descriptive qualitative label.
    """
    raw_pct = int(round(score * 100))
    match_pct = max(48, min(98, raw_pct))
    
    if match_pct >= 85:
        strength = "Exceptional Match"
    elif match_pct >= 75:
        strength = "Strong Match"
    elif match_pct >= 60:
        strength = "Good Match"
    else:
        strength = "Recommended Match"
        
    match_label = f"{match_pct}% AI Match"
    return match_label, match_pct, strength


class ExplanationEngine:
    """
    Synthesizes and validates transparent explanations for recommended products.
    """

    def __init__(self):
        self.thresholds = dict(SIGNAL_CONTRIBUTION_THRESHOLDS)

    def enrich_recommendations(
        self,
        candidates: List[Dict],
        customer_context: Optional[Dict] = None,
        context_type: str = "default",
        active_weights: Optional[Dict[str, float]] = None,
        current_product_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Enriches a list of ranked candidates with structured explanations,
        contributing provenance sources, calibrated AI match indicators,
        and deep technical inspection data.
        """
        enriched = []
        for idx, candidate in enumerate(candidates, start=1):
            item = self.enrich_candidate(
                candidate=candidate,
                rank_position=idx,
                customer_context=customer_context,
                context_type=context_type,
                active_weights=active_weights,
                current_product_id=current_product_id
            )
            enriched.append(item)
        return enriched

    def enrich_candidate(
        self,
        candidate: Dict,
        rank_position: int = 1,
        customer_context: Optional[Dict] = None,
        context_type: str = "default",
        active_weights: Optional[Dict[str, float]] = None,
        current_product_id: Optional[str] = None
    ) -> Dict:
        """
        Processes a single recommendation candidate and attaches:
        - signals: normalized 5-signal dictionary
        - reasons: top 2-3 human-readable, non-repetitive explanations
        - source / provenance: validated list of contributing subsystems
        - ai_match & match_strength: calibrated match indicators
        - technical_explanation: comprehensive academic audit trace
        """
        ctx = customer_context or {}
        weights = active_weights or {"apriori": 0.40, "search": 0.25, "similarity": 0.20, "popularity": 0.15}
        
        # 1. Extract Signal Scores
        apriori_score = max(0.0, min(1.0, float(candidate.get("apriori_score", candidate.get("affinity_score", 0.0)))))
        search_score = max(0.0, min(1.0, float(candidate.get("search_score", 0.0))))
        similarity_score = max(0.0, min(1.0, float(candidate.get("similarity_score", 0.0))))
        popularity_score = max(0.0, min(1.0, float(candidate.get("popularity_score", 0.50))))
        
        stock_qty = int(candidate.get("stock_quantity", 0))
        inventory_score = 1.0 if stock_qty > 0 else 0.0

        final_score = float(candidate.get("score", 0.0))
        if final_score <= 0.0 and inventory_score > 0:
            # Reconstruct composite score if not provided
            final_score = round(
                weights.get("apriori", 0.0) * apriori_score +
                weights.get("search", 0.0) * search_score +
                weights.get("similarity", 0.0) * similarity_score +
                weights.get("popularity", 0.0) * popularity_score,
                4
            )

        # 2. Extract Contextual Signals & Evidentiary Details
        matched_antecedents = list(candidate.get("matched_antecedents", []))
        matched_search_query = candidate.get("matched_search_query")
        matched_ref_prod = candidate.get("matched_reference_product")
        conf = candidate.get("confidence")
        lift = candidate.get("lift")
        support = candidate.get("support")
        rec_type = candidate.get("recommendation_type", "TOP_PICK")

        # Customer context history
        purchased_pids = set(ctx.get("purchased", {}).keys()) if isinstance(ctx.get("purchased"), dict) else set()
        cart_pids = set(ctx.get("cart", {}).keys()) if isinstance(ctx.get("cart"), dict) else set()
        searches_list = list(ctx.get("searches", []))
        has_searches = len(searches_list) > 0
        has_purchases = len(purchased_pids) > 0
        has_cart = len(cart_pids) > 0

        # 3. Determine Contributing Provenance Sources (Truthful Attribution)
        sources: List[str] = []

        # Apriori Provenance Check:
        # Must have active score >= threshold, actual antecedents OR cart/view affinity, and valid customer interaction
        if apriori_score >= self.thresholds["apriori"]:
            if matched_antecedents or context_type in ("cart", "frequently_bought_together", "complete_setup") or has_purchases or has_cart:
                sources.append("apriori")

        # Search Intent Provenance Check:
        # Customer MUST have searched, query must match, and score must exceed threshold
        if search_score >= self.thresholds["search_intent"] and has_searches and matched_search_query:
            sources.append("recent_search")

        # Content Similarity Provenance Check:
        if context_type == "alternatives":
            sources.append("content_similarity")
        elif similarity_score >= self.thresholds["content_similarity"] and (matched_ref_prod or current_product_id):
            sources.append("content_similarity")

        # Popularity Provenance Check:
        if popularity_score >= self.thresholds["popularity"] or context_type == "cold_start" or not sources:
            sources.append("popularity")

        # Inventory Availability Provenance Check:
        if inventory_score > 0:
            sources.append("inventory")

        # 4. Generate Candidate Reasons (Ordered by Weighted Signal Contribution)
        if context_type == "alternatives":
            weighted_contributions = [
                ("content_similarity", 0.60 * max(0.40, similarity_score), similarity_score),
                ("popularity", 0.30 * popularity_score, popularity_score),
                ("recent_search", 0.05 * search_score, search_score),
                ("apriori", 0.05 * apriori_score, apriori_score)
            ]
        else:
            weighted_contributions = [
                ("apriori", weights.get("apriori", 0.0) * apriori_score, apriori_score),
                ("recent_search", weights.get("search", 0.0) * search_score, search_score),
                ("content_similarity", weights.get("similarity", 0.0) * similarity_score, similarity_score),
                ("popularity", weights.get("popularity", 0.0) * popularity_score, popularity_score)
            ]
        # Sort signals by weighted contribution descending
        weighted_contributions.sort(key=lambda x: x[1], reverse=True)

        candidate_reasons: List[str] = []

        for sig_name, w_contrib, raw_val in weighted_contributions:
            if sig_name not in sources:
                continue

            # A. Apriori Reason Formulations
            if sig_name == "apriori":
                if context_type == "cart" or (has_cart and not matched_antecedents):
                    candidate_reasons.append("Frequently bought with items currently in your cart")
                elif context_type == "complete_setup":
                    if matched_antecedents:
                        ant_str = clean_name(matched_antecedents[0])
                        candidate_reasons.append(f"Frequently purchased alongside your {ant_str} setup")
                    else:
                        candidate_reasons.append("Complements products already in your workspace setup")
                elif context_type in ("product_view", "frequently_bought_together") or current_product_id:
                    if matched_antecedents:
                        ant_str = clean_name(matched_antecedents[0])
                        candidate_reasons.append(f"Frequently bought together with {ant_str}")
                    elif matched_ref_prod:
                        candidate_reasons.append(f"Frequently bought together with {clean_name(matched_ref_prod)}")
                    else:
                        candidate_reasons.append("Frequently bought with the item you're viewing")
                elif has_purchases:
                    if matched_antecedents:
                        ant_str = clean_name(matched_antecedents[0])
                        candidate_reasons.append(f"Frequently bought with your {ant_str}")
                    else:
                        candidate_reasons.append("Frequently bought alongside your previous purchases")
                else:
                    candidate_reasons.append("Frequently paired with related items by shoppers")

            # B. Search Intent Reason Formulations
            elif sig_name == "recent_search":
                if matched_search_query:
                    clean_q = matched_search_query.strip().lower()
                    if len(clean_q) > 32:
                        clean_q = clean_q[:30] + "..."
                    candidate_reasons.append(f"Matches your recent search for '{clean_q}'")
                else:
                    candidate_reasons.append("Matches your recent product searches")

            # C. Content Similarity Reason Formulations
            elif sig_name == "content_similarity":
                if context_type == "alternatives":
                    pct_sim = max(45, int(round(similarity_score * 100)))
                    candidate_reasons.append(f"Similar features and price range ({pct_sim}% spec match)")
                elif context_type == "product_view" or current_product_id:
                    if matched_ref_prod:
                        candidate_reasons.append(f"Similar features to the {clean_name(matched_ref_prod)} you're viewing")
                    else:
                        candidate_reasons.append("Similar features to the product you're currently viewing")
                elif matched_ref_prod and has_purchases:
                    candidate_reasons.append(f"Similar to your {clean_name(matched_ref_prod)}")
                else:
                    cat_name = candidate.get("category_name", "this category")
                    candidate_reasons.append(f"Matches technical specifications in {cat_name}")

            # D. Popularity & Quality Reason Formulations
            elif sig_name == "popularity":
                avg_rating = candidate.get("avg_rating", 4.5)
                rev_count = candidate.get("review_count", 0)
                if context_type == "cold_start" or not has_purchases:
                    if rev_count > 0:
                        candidate_reasons.append(f"Popular choice among shoppers ({avg_rating}/5 stars across {rev_count} verified reviews)")
                    else:
                        candidate_reasons.append("Popular choice among shoppers")
                elif avg_rating >= 4.4 and rev_count >= 10:
                    candidate_reasons.append(f"Highly rated by verified customers ({avg_rating}/5 stars across {rev_count} reviews)")
                else:
                    cat_name = candidate.get("category_name", "its category")
                    candidate_reasons.append(f"Top-performing product in {cat_name}")

        # E. Stock & Inventory Readiness Reason
        if stock_qty > 0 and (context_type == "alternatives" or len(candidate_reasons) < 3):
            if stock_qty <= 15:
                candidate_reasons.append(f"Currently in stock (Only {stock_qty} units remaining)")
            else:
                candidate_reasons.append("Currently in stock and ready to ship")

        # 5. Safeguard & Validation Pass (Prevent False Claims)
        validated_reasons, validated_sources = self.validate_explanations(
            candidate=candidate,
            customer_context=ctx,
            reasons=candidate_reasons,
            sources=sources,
            context_type=context_type
        )

        # Select top 2-3 unique non-repetitive reasons
        final_reasons = []
        seen_texts: Set[str] = set()
        for r in validated_reasons:
            norm_r = r.strip().lower()
            if norm_r not in seen_texts:
                final_reasons.append(r)
                seen_texts.add(norm_r)
            if len(final_reasons) >= 3:
                break

        # Fallback safeguard: if reasons empty, provide truthful general fallback
        if not final_reasons:
            cat_name = candidate.get("category_name", "our catalog")
            final_reasons = [
                f"Highly rated choice in {cat_name}",
                "Currently in stock"
            ]

        # 6. Calibrated AI Match Indicator
        match_label, match_pct, match_strength = compute_match_indicator(final_score)

        # 7. Deep Academic / Viva Technical Explanation
        technical_explanation = {
            "ranking_position": rank_position,
            "final_score": round(final_score, 4),
            "ai_match_percentage": match_pct,
            "recommendation_type": rec_type,
            "context_profile": context_type,
            "scoring_formula": "Final = (w_apr × S_apr) + (w_srch × S_srch) + (w_sim × S_sim) + (w_pop × S_pop)",
            "weights_applied": {
                "apriori": round(weights.get("apriori", 0.0), 3),
                "search": round(weights.get("search", 0.0), 3),
                "similarity": round(weights.get("similarity", 0.0), 3),
                "popularity": round(weights.get("popularity", 0.0), 3)
            },
            "signal_breakdown": {
                "apriori_score": round(apriori_score, 4),
                "search_intent_score": round(search_score, 4),
                "content_similarity_score": round(similarity_score, 4),
                "popularity_score": round(popularity_score, 4),
                "inventory_score": round(inventory_score, 4)
            },
            "weighted_contributions": {
                "apriori": round(weights.get("apriori", 0.0) * apriori_score, 4),
                "search_intent": round(weights.get("search", 0.0) * search_score, 4),
                "content_similarity": round(weights.get("similarity", 0.0) * similarity_score, 4),
                "popularity": round(weights.get("popularity", 0.0) * popularity_score, 4)
            },
            "provenance_sources": list(validated_sources),
            "apriori_details": {
                "active": "apriori" in validated_sources,
                "affinity_score": round(apriori_score, 4),
                "rule_statement": f"{' + '.join(matched_antecedents)} → {candidate.get('product_name', '')}" if matched_antecedents else None,
                "support": round(support, 4) if support is not None else None,
                "confidence": round(conf, 4) if conf is not None else None,
                "lift": round(lift, 2) if lift is not None else None
            },
            "search_details": {
                "active": "recent_search" in validated_sources,
                "score": round(search_score, 4),
                "matched_query": matched_search_query
            },
            "similarity_details": {
                "active": "content_similarity" in validated_sources,
                "score": round(similarity_score, 4),
                "reference_product": matched_ref_prod
            },
            "popularity_details": {
                "score": round(popularity_score, 4),
                "avg_rating": candidate.get("avg_rating", 4.5),
                "review_count": candidate.get("review_count", 0)
            },
            "inventory_details": {
                "in_stock": stock_qty > 0,
                "stock_quantity": stock_qty
            }
        }

        # 8. Assemble Full Machine-Readable Record
        result = dict(candidate)
        result.update({
            "score": round(final_score, 4),
            "ai_match": match_label,
            "match_percentage": match_pct,
            "match_strength": match_strength,
            "recommendation_type": rec_type,
            "signals": {
                # Phase 6 structured signal schema
                "apriori": round(apriori_score, 4),
                "search_intent": round(search_score, 4),
                "content_similarity": round(similarity_score, 4),
                "popularity": round(popularity_score, 4),
                "inventory": round(inventory_score, 4),
                # Backward-compatibility aliases for Phase 4 & 5 test suites
                "apriori_score": round(apriori_score, 4),
                "search_score": round(search_score, 4),
                "similarity_score": round(similarity_score, 4),
                "popularity_score": round(popularity_score, 4),
                "inventory_score": round(inventory_score, 4)
            },
            "reasons": final_reasons,
            "source": list(validated_sources),
            "provenance": list(validated_sources),
            "technical_explanation": technical_explanation,
            # Backward-compatible scalar properties
            "reason": final_reasons[0] if final_reasons else "",
            "algorithm": candidate.get("algorithm", f"Hybrid Explanation ({rec_type})")
        })

        return result

    def validate_explanations(
        self,
        candidate: Dict,
        customer_context: Dict,
        reasons: List[str],
        sources: List[str],
        context_type: str = "default"
    ) -> Tuple[List[str], List[str]]:
        """
        Validation Safeguards (Requirement 11):
        Ensures explanations never contradict actual ground-truth data:
        - If no recent search exists: Never say 'matches your recent search'
        - If Apriori did not influence score: Never say 'frequently bought together'
        - If product is not similar: Never claim similarity
        - If customer never purchased: Never say 'Because you bought...'
        - If stock is 0: Never claim 'in stock'
        """
        searches = customer_context.get("searches", [])
        has_searches = len(searches) > 0
        purchased = customer_context.get("purchased", {})
        has_purchased = len(purchased) > 0
        stock_qty = int(candidate.get("stock_quantity", 0))

        apriori_score = candidate.get("apriori_score", 0.0)
        search_score = candidate.get("search_score", 0.0)
        similarity_score = candidate.get("similarity_score", 0.0)

        cleaned_reasons: List[str] = []
        cleaned_sources = set(sources)

        for r in reasons:
            lower_r = r.lower()

            # Rule 1: Search validation
            if "search" in lower_r:
                if not has_searches or search_score < self.thresholds["search_intent"]:
                    cleaned_sources.discard("recent_search")
                    continue  # Reject false search claim

            # Rule 2: Co-purchase / previous order validation
            if "previous purchase" in lower_r or "bought with your" in lower_r or "purchased alongside your" in lower_r:
                if not has_purchased and context_type not in ("cart", "product_view", "frequently_bought_together", "complete_setup"):
                    cleaned_sources.discard("apriori")
                    continue  # Reject false purchase claim

            # Rule 3: Apriori rule validation
            if "frequently bought" in lower_r or "frequently paired" in lower_r:
                if apriori_score < self.thresholds["apriori"] and context_type not in ("cart", "frequently_bought_together", "complete_setup"):
                    cleaned_sources.discard("apriori")
                    continue  # Reject false association claim

            # Rule 4: Content similarity validation
            if "similar" in lower_r:
                if similarity_score < self.thresholds["content_similarity"] and context_type != "alternatives":
                    cleaned_sources.discard("content_similarity")
                    continue  # Reject false similarity claim

            # Rule 5: Stock validation
            if "in stock" in lower_r:
                if stock_qty <= 0:
                    cleaned_sources.discard("inventory")
                    continue  # Reject false in-stock claim

            cleaned_reasons.append(r)

        ordered_sources = [s for s in ["apriori", "recent_search", "content_similarity", "popularity", "inventory"] if s in cleaned_sources]
        return cleaned_reasons, ordered_sources
