"""
Phase 8: AI Review Intelligence & Sentiment Analysis Engine
Provides a lightweight, local, explainable NLP pipeline for e-commerce reviews.
Analyzes:
1. Review sentiment classification (POSITIVE, NEUTRAL, NEGATIVE) combining text and rating
2. Normalized product-level sentiment scores (0.0 to 1.0)
3. Aspect/Theme keyword extraction (positive themes vs. negative complaints)
4. Product Health Scorecards
5. Concise customer-facing AI review summaries
6. Rating/Text mismatch detection (Review Signals)
7. Temporal review trend tracking (recent sentiment vs. historical baseline)
"""

import os
import re
import math
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


class ReviewSentimentAnalyzer:
    """
    Pure Python & SQLite Review Intelligence and Sentiment Engine.
    Employs a domain-adapted sentiment lexicon, negation-aware token weighting,
    clause-level aspect/theme extraction, and rating-text fusion.
    """

    # Domain-adapted sentiment lexicon (valence weights: -2.5 to +2.5)
    SENTIMENT_LEXICON: Dict[str, float] = {
        # Strong Positives (+1.5 to +2.5)
        "exceeded": 2.2, "expectations": 1.2, "flawless": 2.5, "perfection": 2.5,
        "perfect": 2.2, "fantastic": 2.2, "superb": 2.2, "outstanding": 2.4,
        "exceptional": 2.4, "brilliant": 2.0, "amazing": 2.2, "love": 2.0,
        "loved": 2.0, "best": 2.3, "top": 1.5, "recommend": 1.8, "highly": 1.5,
        "satisfied": 1.8, "favorite": 1.8, "unbeatable": 2.0, "impressed": 1.9,
        "delighted": 2.0, "premium": 1.7, "seamless": 1.8, "durable": 1.7,
        "top notch": 2.2, "top-notch": 2.2, "top tier": 2.2,

        # Moderate Positives (+0.8 to +1.4)
        "good": 1.0, "great": 1.5, "solid": 1.3, "sturdy": 1.3, "clean": 1.0,
        "responsive": 1.3, "fast": 1.2, "smooth": 1.3, "crisp": 1.3, "punchy": 1.2,
        "comfortable": 1.5, "ergonomic": 1.4, "reliable": 1.4, "worth": 1.3,
        "helpful": 1.0, "convenient": 1.1, "clear": 1.1, "intuitive": 1.2,
        "efficient": 1.2, "well": 0.9, "nice": 1.0, "decent": 0.6,

        # Strong Negatives (-1.5 to -2.5)
        "terrible": -2.4, "horrible": -2.5, "awful": -2.4, "worst": -2.5,
        "defective": -2.4, "useless": -2.3, "broken": -2.2, "broke": -2.0,
        "garbage": -2.3, "junk": -2.2, "waste": -2.2, "ruined": -2.0,
        "unusable": -2.2, "uncomfortable": -1.8, "disaster": -2.4, "failed": -2.0,

        # Moderate Negatives (-0.8 to -1.4)
        "bad": -1.5, "poor": -1.6, "flimsy": -1.5, "cheap": -1.3,
        "overpriced": -1.6, "expensive": -1.1, "disappointed": -1.8,
        "disappointing": -1.8, "sluggish": -1.4, "slow": -1.2, "lag": -1.3,
        "latency": -1.2, "glitch": -1.4, "glitches": -1.5, "muffled": -1.6,
        "scratches": -1.2, "scratched": -1.2, "fragile": -1.4, "annoying": -1.3,
        "noisy": -1.2, "clunky": -1.3, "drain": -1.3, "drains": -1.4,
        "disconnects": -1.5, "disconnect": -1.4, "issue": -1.1, "issues": -1.2,
        "problem": -1.2, "problems": -1.3, "subpar": -1.4, "mediocre": -1.0,
        "learning curve": -0.8, "inconsistent": -1.2, "faulty": -1.8
    }

    # Negation words that invert the valence of subsequent sentiment tokens
    NEGATION_WORDS = {
        "not", "no", "never", "hardly", "scarcely", "neither",
        "nor", "cannot", "cant", "can't", "wont", "won't", "dont", "don't",
        "didnt", "didn't", "isnt", "isn't", "wasnt", "wasn't", "without", "lacks"
    }

    # Intensifiers & Dampeners
    INTENSIFIERS = {
        "very": 1.5, "extremely": 1.8, "highly": 1.5, "really": 1.4,
        "super": 1.5, "incredibly": 1.7, "absolutely": 1.6, "exceptionally": 1.7,
        "totally": 1.4, "completely": 1.4
    }
    DAMPENERS = {
        "slightly": 0.6, "somewhat": 0.7, "a bit": 0.7, "barely": 0.5,
        "kind of": 0.7, "sort of": 0.7
    }

    # Domain aspect keywords mapped to standardized product themes
    ASPECT_THEMES: Dict[str, List[str]] = {
        "Battery Life": [
            "battery", "battery life", "battery runtime", "charging", "charger",
            "charge", "runtime", "power consumption", "battery drain"
        ],
        "Sound Quality": [
            "sound", "audio", "sound quality", "bass", "treble", "volume",
            "acoustics", "clarity", "soundstage", "listening"
        ],
        "Build Quality": [
            "build quality", "build", "durability", "durable", "sturdy",
            "materials", "solid build", "robust", "flimsy", "cheap plastic", "materials"
        ],
        "Comfort & Fit": [
            "comfort", "comfortable", "fit", "ergonomic", "ergonomics",
            "lightweight", "cushion", "cushions", "uncomfortable", "in-ear"
        ],
        "Noise Cancellation": [
            "anc", "noise cancellation", "noise cancelling", "ambient mode",
            "isolation", "noise cancel", "active noise"
        ],
        "Microphone Quality": [
            "microphone", "mic", "call quality", "voice calls", "voice quality",
            "muffled", "voice"
        ],
        "Performance": [
            "performance", "speed", "fast", "responsive", "smooth", "lag",
            "latency", "glitches", "powerful", "performs"
        ],
        "Price & Value": [
            "value", "price", "overpriced", "expensive", "affordable", "cost",
            "value for money", "worth it", "budget"
        ],
        "Display & Screen": [
            "display", "screen", "resolution", "colors", "brightness", "4k",
            "oled", "sharpness", "hdr", "viewing"
        ],
        "Connectivity": [
            "bluetooth", "connectivity", "connection", "pairing", "wireless",
            "sync", "disconnects", "signal", "glitches"
        ],
        "Ease of Use": [
            "instructions", "learning curve", "setup", "easy to use", "manual",
            "intuitive", "user friendly", "controls"
        ],
        "Camera & Video": [
            "camera", "video", "autofocus", "sensor", "lens", "image quality",
            "photo", "photos", "shooting", "4k video"
        ]
    }

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # 1. TEXT NLP & SENTIMENT POLARITY
    # =========================================================================

    def analyze_comment_text(self, text: Optional[str]) -> Dict[str, Any]:
        """
        Calculates sentiment polarity score for a raw text comment.
        Incorporates negation windows and intensifiers.
        Returns:
            - text_polarity: float in [-1.0, 1.0]
            - sentiment_label: "POSITIVE", "NEUTRAL", "NEGATIVE"
            - positive_tokens: list of matched positive words
            - negative_tokens: list of matched negative words
            - confidence: float in [0.0, 1.0]
        """
        if not text or len(text.strip()) == 0:
            return {
                "text_polarity": 0.0,
                "sentiment_label": "NEUTRAL",
                "positive_tokens": [],
                "negative_tokens": [],
                "confidence": 0.0,
                "is_empty": True
            }

        cleaned = text.lower()
        # Tokenize by alphanumeric words and apostrophes
        words = re.findall(r"\b[a-z']+\b", cleaned)
        if not words:
            return {
                "text_polarity": 0.0,
                "sentiment_label": "NEUTRAL",
                "positive_tokens": [],
                "negative_tokens": [],
                "confidence": 0.0,
                "is_empty": True
            }

        positive_matches = []
        negative_matches = []
        total_score = 0.0
        active_tokens_count = 0

        # Check multi-word lexicon entries first (e.g., "top tier", "learning curve")
        working_text = cleaned
        for phrase, weight in self.SENTIMENT_LEXICON.items():
            if " " in phrase and phrase in working_text:
                total_score += weight
                active_tokens_count += 1
                if weight > 0:
                    positive_matches.append(phrase)
                else:
                    negative_matches.append(phrase)
                # Replace matched multi-word phrase with space to prevent substring double counting
                working_text = working_text.replace(phrase, " ")

        # Split text into discrete clauses using punctuation and line breaks
        clauses = re.split(r"[,.;!?\n]+", working_text)

        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue

            words = re.findall(r"\b[a-z']+\b", clause)
            if not words:
                continue

            # Reset negation and modifier state at every clause boundary
            negation_active = False
            negation_ttl = 0
            current_multiplier = 1.0

            for word in words:
                if word in self.NEGATION_WORDS:
                    negation_active = True
                    negation_ttl = 3  # negate up to next 3 words in this clause
                    continue

                if word in self.INTENSIFIERS:
                    current_multiplier = self.INTENSIFIERS[word]
                    continue

                if word in self.DAMPENERS:
                    current_multiplier = self.DAMPENERS[word]
                    continue

                # Check single word in lexicon
                if word in self.SENTIMENT_LEXICON:
                    base_weight = self.SENTIMENT_LEXICON[word]
                    # Apply negation
                    if negation_active and negation_ttl > 0:
                        effective_weight = -1.0 * base_weight * 0.85
                        negation_ttl -= 1
                        if negation_ttl <= 0:
                            negation_active = False
                    else:
                        effective_weight = base_weight * current_multiplier

                    total_score += effective_weight
                    active_tokens_count += 1

                    if effective_weight > 0:
                        positive_matches.append(word)
                    else:
                        negative_matches.append(word)

                    current_multiplier = 1.0
                else:
                    if negation_active:
                        negation_ttl -= 1
                        if negation_ttl <= 0:
                            negation_active = False

        # Exclamation mark bonus for polarity
        if "!" in text:
            excl_count = min(text.count("!"), 3)
            if total_score > 0:
                total_score += 0.25 * excl_count
            elif total_score < 0:
                total_score -= 0.25 * excl_count

        # Normalize score to [-1.0, 1.0] using hyperbolic tangent scaling
        if active_tokens_count > 0:
            norm_score = math.tanh(total_score / math.sqrt(active_tokens_count + 1))
        else:
            norm_score = 0.0

        norm_score = max(-1.0, min(1.0, round(norm_score, 2)))

        if norm_score >= 0.15:
            label = "POSITIVE"
        elif norm_score <= -0.15:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"

        confidence = min(1.0, round(math.sqrt(active_tokens_count) * 0.45, 2)) if active_tokens_count > 0 else 0.3

        return {
            "text_polarity": norm_score,
            "sentiment_label": label,
            "positive_tokens": list(set(positive_matches)),
            "negative_tokens": list(set(negative_matches)),
            "confidence": confidence,
            "is_empty": False
        }

    # =========================================================================
    # 2. REVIEW CLASSIFICATION (RATING + TEXT FUSION & MISMATCH DETECTION)
    # =========================================================================

    def classify_review(self, rating: int, comment: Optional[str]) -> Dict[str, Any]:
        """
        Combines star rating (1-5) and comment text to classify a review.
        Detects rating/text disagreements (Review Signals).
        """
        text_analysis = self.analyze_comment_text(comment)
        text_polarity = text_analysis["text_polarity"]
        is_empty = text_analysis.get("is_empty", False) or not comment or len(comment.strip()) <= 3

        # Rating score mapped to [-1.0, 1.0]
        # 5 -> +1.0, 4 -> +0.5, 3 -> 0.0, 2 -> -0.5, 1 -> -1.0
        rating_score = round((rating - 3.0) / 2.0, 2)

        # Disagreement / Mismatch Detection
        is_mismatch = False
        mismatch_type = None
        mismatch_reason = None

        if not is_empty:
            # High rating (4-5) but negative text polarity (<= -0.25)
            if rating >= 4 and text_polarity <= -0.25:
                is_mismatch = True
                mismatch_type = "HIGH_RATING_NEGATIVE_TEXT"
                mismatch_reason = f"Customer assigned ★{rating} but written comment expresses negative sentiment ({text_polarity})."

            # Low rating (1-2) but positive text polarity (>= +0.25)
            elif rating <= 2 and text_polarity >= 0.25:
                is_mismatch = True
                mismatch_type = "LOW_RATING_POSITIVE_TEXT"
                mismatch_reason = f"Customer assigned ★{rating} but written comment expresses positive praise (+{text_polarity})."

        # Final Sentiment Classification
        if is_empty:
            # Reliance on rating alone when comment is absent or very short
            if rating >= 4:
                final_sentiment = "POSITIVE"
                composite_score = 0.85 if rating == 5 else 0.65
            elif rating == 3:
                final_sentiment = "NEUTRAL"
                composite_score = 0.50
            else:
                final_sentiment = "NEGATIVE"
                composite_score = 0.15 if rating == 1 else 0.35
        else:
            # Weighted blend: 55% text polarity, 45% star rating
            # Normalized composite to [0.0, 1.0] scale
            raw_composite = (0.55 * text_polarity) + (0.45 * rating_score)
            composite_score = round(max(0.0, min(1.0, (raw_composite + 1.0) / 2.0)), 2)

            if rating == 3:
                # 3-star reviews are neutral baseline; text must be distinctly polarized to shift
                if text_polarity >= 0.45:
                    final_sentiment = "POSITIVE"
                elif text_polarity <= -0.45:
                    final_sentiment = "NEGATIVE"
                else:
                    final_sentiment = "NEUTRAL"
            else:
                if raw_composite >= 0.15:
                    final_sentiment = "POSITIVE"
                elif raw_composite <= -0.15:
                    final_sentiment = "NEGATIVE"
                else:
                    final_sentiment = "NEUTRAL"

        # Extract aspect themes mentioned in this review
        detected_themes = self.extract_themes_from_single_comment(comment, text_polarity, rating)

        return {
            "rating": rating,
            "comment": comment or "",
            "sentiment": final_sentiment,
            "sentiment_score": composite_score,
            "text_polarity": text_polarity,
            "rating_score": rating_score,
            "is_mismatch": is_mismatch,
            "mismatch_type": mismatch_type,
            "mismatch_reason": mismatch_reason,
            "positive_tokens": text_analysis["positive_tokens"],
            "negative_tokens": text_analysis["negative_tokens"],
            "themes": detected_themes,
            "aspect_themes": detected_themes
        }

    # =========================================================================
    # 3. ASPECT & THEME EXTRACTION (CLAUSE-LEVEL ATTRIBUTION)
    # =========================================================================

    def extract_themes_from_single_comment(
        self,
        comment: Optional[str],
        overall_text_polarity: float,
        rating: int
    ) -> List[Dict[str, str]]:
        """
        Extracts themes and assigns them a positive or negative polarity based on the
        surrounding clause sentiment.
        """
        if not comment or len(comment.strip()) <= 3:
            return []

        # Split into clauses by punctuation and contrasting conjunctions
        clauses = re.split(r"[,.;!?]|\b(?:but|however|although|though|yet|while)\b", comment.lower())
        results = []
        seen_themes = set()

        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue

            clause_analysis = self.analyze_comment_text(clause)
            clause_polarity = clause_analysis["text_polarity"]

            # If clause is neutral, fallback to overall text polarity or rating
            effective_clause_polarity = clause_polarity if abs(clause_polarity) >= 0.10 else overall_text_polarity
            theme_valence = "POSITIVE" if (effective_clause_polarity > 0.05 or (effective_clause_polarity == 0.0 and rating >= 4)) else "NEGATIVE"

            for theme_name, keywords in self.ASPECT_THEMES.items():
                if theme_name in seen_themes:
                    continue

                for kw in keywords:
                    # Look for exact word boundary match
                    pattern = r"\b" + re.escape(kw) + r"\b"
                    if re.search(pattern, clause):
                        results.append({
                            "theme": theme_name,
                            "matched_keyword": kw,
                            "sentiment": theme_valence,
                            "clause": clause
                        })
                        seen_themes.add(theme_name)
                        break

        return results

    def aggregate_themes(self, classified_reviews: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Aggregates aspect themes across all reviews for a product.
        Returns: (positive_themes, negative_themes) ranked by frequency.
        """
        pos_counts: Dict[str, int] = {}
        neg_counts: Dict[str, int] = {}
        sample_phrases_pos: Dict[str, str] = {}
        sample_phrases_neg: Dict[str, str] = {}

        for rev in classified_reviews:
            for t in rev.get("themes", []):
                theme_name = t["theme"]
                sentiment = t["sentiment"]
                clause = t.get("clause", "")

                if sentiment == "POSITIVE":
                    pos_counts[theme_name] = pos_counts.get(theme_name, 0) + 1
                    if theme_name not in sample_phrases_pos and clause:
                        sample_phrases_pos[theme_name] = clause
                else:
                    neg_counts[theme_name] = neg_counts.get(theme_name, 0) + 1
                    if theme_name not in sample_phrases_neg and clause:
                        sample_phrases_neg[theme_name] = clause

        # Convert to sorted list of objects
        pos_list = [
            {"theme": k, "count": v, "sample": sample_phrases_pos.get(k, "")}
            for k, v in sorted(pos_counts.items(), key=lambda x: -x[1])
        ]
        neg_list = [
            {"theme": k, "count": v, "sample": sample_phrases_neg.get(k, "")}
            for k, v in sorted(neg_counts.items(), key=lambda x: -x[1])
        ]

        return pos_list, neg_list

    # =========================================================================
    # 4. CUSTOMER-FACING AI REVIEW SUMMARY GENERATOR
    # =========================================================================

    def generate_review_summary_text(
        self,
        product_name: str,
        total_reviews: int,
        avg_rating: float,
        pos_pct: int,
        pos_themes: List[Dict[str, Any]],
        neg_themes: List[Dict[str, Any]]
    ) -> str:
        """
        Synthesizes an explainable, concise customer-facing summary narrative
        derived directly from sentiment distribution and extracted themes.
        """
        if total_reviews == 0:
            return f"No customer reviews submitted yet for {product_name}. Be the first to share your experience!"

        pos_theme_names = [t["theme"] for t in pos_themes[:3]]
        neg_theme_names = [t["theme"] for t in neg_themes[:2]]

        # Build praise clause
        if pos_theme_names:
            if len(pos_theme_names) == 1:
                praise_str = f"highlight {pos_theme_names[0]}"
            elif len(pos_theme_names) == 2:
                praise_str = f"praise {pos_theme_names[0]} and {pos_theme_names[1]}"
            else:
                praise_str = f"praise {pos_theme_names[0]}, {pos_theme_names[1]}, and {pos_theme_names[2]}"
            opening = f"Most verified buyers ({pos_pct}% positive feedback) {praise_str}."
        else:
            opening = f"Overall customer reception is favorable ({pos_pct}% positive) with an average rating of {avg_rating:.1f}/5.0."

        # Build critique clause
        if neg_theme_names:
            if len(neg_theme_names) == 1:
                critique_str = f"A smaller number of customer notes mention {neg_theme_names[0]}."
            else:
                critique_str = f"A few customer notes mention {neg_theme_names[0]} or {neg_theme_names[1]}."
        else:
            critique_str = "Customer satisfaction remains consistently high with virtually no recurring complaints."

        return f"{opening} {critique_str}"

    # =========================================================================
    # 5. PRODUCT HEALTH SCORECARD & PRODUCT INTELLIGENCE
    # =========================================================================

    def get_product_review_intelligence(self, product_id: str) -> Dict[str, Any]:
        """
        Retrieves, classifies, and summarizes all reviews for a specific product.
        Generates Product Health Scorecard, themes, recency momentum, and review signals.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Product metadata
        cursor.execute("""
            SELECT p.product_id, p.product_name, p.brand, p.price, p.stock_quantity, cat.category_name
            FROM products p
            JOIN categories cat ON p.category_id = cat.category_id
            WHERE p.product_id = ?;
        """, (product_id,))
        prod = cursor.fetchone()

        if not prod:
            conn.close()
            return {"status": "error", "message": f"Product '{product_id}' not found."}

        # Fetch all reviews for this product
        cursor.execute("""
            SELECT r.review_id, r.customer_id, c.name as customer_name,
                   r.rating, r.comment, r.review_date
            FROM reviews r
            JOIN customers c ON r.customer_id = c.customer_id
            WHERE r.product_id = ?
            ORDER BY r.review_date DESC;
        """, (product_id,))
        review_rows = cursor.fetchall()
        conn.close()

        total_reviews = len(review_rows)

        # Handle 0-review product edge case gracefully
        if total_reviews == 0:
            return {
                "status": "success",
                "product_id": prod["product_id"],
                "product_name": prod["product_name"],
                "category_name": prod["category_name"],
                "average_rating": 0.0,
                "review_count": 0,
                "sentiment": {
                    "positive": 0.0,
                    "neutral": 0.0,
                    "negative": 0.0
                },
                "sentiment_distribution_counts": {
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0
                },
                "sentiment_score": 0.50,
                "product_health": {
                    "product_id": prod["product_id"],
                    "product_name": prod["product_name"],
                    "average_rating": 0.0,
                    "review_count": 0,
                    "product_health_score": 0.50,
                    "positive_pct": 0,
                    "neutral_pct": 0,
                    "negative_pct": 0,
                    "top_positive_themes": [],
                    "top_negative_themes": [],
                    "health_status": "NO_REVIEWS",
                    "recent_trend": "No Data (0 reviews)"
                },
                "positive_themes": [],
                "negative_themes": [],
                "recent_sentiment": {
                    "recent_positive_ratio": 0.0,
                    "overall_positive_ratio": 0.0,
                    "trend": "NO_DATA",
                    "trend_label": "No Data (0 reviews)"
                },
                "ai_review_summary": f"No customer reviews submitted yet for {prod['product_name']}.",
                "mismatches": [],
                "review_signals": [],
                "has_mismatch": False,
                "reviews": []
            }

        # Classify each review
        classified_reviews = []
        pos_cnt = 0
        neu_cnt = 0
        neg_cnt = 0
        mismatches = []
        total_rating_sum = 0

        for r in review_rows:
            classification = self.classify_review(r["rating"], r["comment"])
            classification["review_id"] = r["review_id"]
            classification["customer_id"] = r["customer_id"]
            classification["customer_name"] = r["customer_name"]
            classification["review_date"] = r["review_date"]

            classified_reviews.append(classification)
            total_rating_sum += r["rating"]

            if classification["sentiment"] == "POSITIVE":
                pos_cnt += 1
            elif classification["sentiment"] == "NEGATIVE":
                neg_cnt += 1
            else:
                neu_cnt += 1

            if classification["is_mismatch"]:
                mismatches.append({
                    "review_id": r["review_id"],
                    "customer_name": r["customer_name"],
                    "rating": r["rating"],
                    "comment": r["comment"],
                    "mismatch_type": classification["mismatch_type"],
                    "reason": classification["mismatch_reason"]
                })

        avg_rating = round(total_rating_sum / total_reviews, 2)
        pos_ratio = round(pos_cnt / total_reviews, 2)
        neu_ratio = round(neu_cnt / total_reviews, 2)
        neg_ratio = round(neg_cnt / total_reviews, 2)

        # Normalized product sentiment score [0.0, 1.0]
        # (Positive reviews weighted 1.0, Neutral weighted 0.5, Negative weighted 0.0)
        sentiment_score = round((pos_cnt + (0.5 * neu_cnt)) / total_reviews, 2)

        # Aspect Theme Extraction
        pos_themes, neg_themes = self.aggregate_themes(classified_reviews)

        # Recency Analysis: Evaluate recent half vs historical baseline
        recent_cutoff_idx = max(1, math.ceil(total_reviews / 2))
        recent_half = classified_reviews[:recent_cutoff_idx]
        recent_pos_cnt = sum(1 for r in recent_half if r["sentiment"] == "POSITIVE")
        recent_pos_ratio = round(recent_pos_cnt / len(recent_half), 2)

        delta = recent_pos_ratio - pos_ratio
        if delta >= 0.05:
            trend = "IMPROVING"
            trend_label = f"📈 Improving (+{int(delta * 100)}% recent surge)"
        elif delta <= -0.05:
            trend = "DECLINING"
            trend_label = f"📉 Declining ({int(delta * 100)}% recent dip)"
        else:
            trend = "STABLE"
            trend_label = "⚖ Stable Sentiment"

        # Generate Customer-Facing Summary
        summary_text = self.generate_review_summary_text(
            product_name=prod["product_name"],
            total_reviews=total_reviews,
            avg_rating=avg_rating,
            pos_pct=int(pos_ratio * 100),
            pos_themes=pos_themes,
            neg_themes=neg_themes
        )

        # Product Health Scorecard
        product_health = {
            "product_id": prod["product_id"],
            "product_name": prod["product_name"],
            "average_rating": avg_rating,
            "review_count": total_reviews,
            "product_health_score": sentiment_score,
            "positive_pct": int(pos_ratio * 100),
            "neutral_pct": int(neu_ratio * 100),
            "negative_pct": int(neg_ratio * 100),
            "top_positive_themes": [t["theme"] for t in pos_themes[:3]],
            "top_negative_themes": [t["theme"] for t in neg_themes[:3]],
            "health_status": "EXCELLENT" if sentiment_score >= 0.8 else ("GOOD" if sentiment_score >= 0.65 else ("FAIR" if sentiment_score >= 0.45 else "NEEDS_ATTENTION")),
            "recent_trend": trend_label
        }

        return {
            "status": "success",
            "product_id": prod["product_id"],
            "product_name": prod["product_name"],
            "category_name": prod["category_name"],
            "brand": prod["brand"],
            "price": float(prod["price"]),
            "stock_quantity": int(prod["stock_quantity"]),
            "average_rating": avg_rating,
            "review_count": total_reviews,
            "product_health": product_health,
            "sentiment": {
                "positive": pos_ratio,
                "neutral": neu_ratio,
                "negative": neg_ratio
            },
            "sentiment_distribution_counts": {
                "positive": pos_cnt,
                "neutral": neu_cnt,
                "negative": neg_cnt
            },
            "sentiment_score": sentiment_score,
            "positive_themes": [t["theme"] for t in pos_themes],
            "negative_themes": [t["theme"] for t in neg_themes],
            "positive_theme_details": pos_themes,
            "negative_theme_details": neg_themes,
            "recent_sentiment": {
                "recent_positive_ratio": recent_pos_ratio,
                "overall_positive_ratio": pos_ratio,
                "delta": round(delta, 2),
                "trend": trend,
                "trend_label": trend_label
            },
            "ai_review_summary": summary_text,
            "mismatches": mismatches,
            "review_signals": mismatches,
            "has_mismatch": len(mismatches) > 0,
            "reviews": classified_reviews
        }

    # =========================================================================
    # 6. CATALOG-WIDE REVIEW INTELLIGENCE (ADMIN VIEW)
    # =========================================================================

    def get_catalog_review_intelligence(self, filter_type: str = "all") -> Dict[str, Any]:
        """
        Evaluates review intelligence across all products in the catalog.
        Supports admin filtering: all, most_positive, most_negative, most_reviewed, mismatched.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT product_id FROM products ORDER BY product_id ASC;")
        product_ids = [r["product_id"] for r in cursor.fetchall()]
        conn.close()

        product_cards = []
        total_catalog_reviews = 0
        total_positive_reviews = 0
        total_neutral_reviews = 0
        total_negative_reviews = 0
        total_mismatches = 0
        sentiment_scores_sum = 0.0

        for pid in product_ids:
            intel = self.get_product_review_intelligence(pid)
            if intel.get("status") == "success":
                rev_count = intel["review_count"]
                total_catalog_reviews += rev_count
                total_positive_reviews += intel["sentiment_distribution_counts"]["positive"]
                total_neutral_reviews += intel["sentiment_distribution_counts"]["neutral"]
                total_negative_reviews += intel["sentiment_distribution_counts"]["negative"]
                total_mismatches += len(intel["mismatches"])
                sentiment_scores_sum += intel["sentiment_score"]

                product_cards.append({
                    "product_id": intel["product_id"],
                    "product_name": intel["product_name"],
                    "category_name": intel["category_name"],
                    "price": intel["price"],
                    "average_rating": intel["average_rating"],
                    "review_count": rev_count,
                    "sentiment": intel["sentiment"],
                    "sentiment_score": intel["sentiment_score"],
                    "positive_themes": intel["positive_themes"][:3],
                    "negative_themes": intel["negative_themes"][:2],
                    "trend": intel["recent_sentiment"]["trend"],
                    "trend_label": intel["recent_sentiment"]["trend_label"],
                    "has_mismatch": intel["has_mismatch"],
                    "mismatch_count": len(intel["mismatches"]),
                    "ai_review_summary": intel["ai_review_summary"]
                })

        # Apply filtering
        filter_type = filter_type.lower()
        if filter_type == "most_positive":
            product_cards.sort(key=lambda x: (x["sentiment"]["positive"], x["review_count"]), reverse=True)
        elif filter_type == "most_negative":
            product_cards.sort(key=lambda x: (x["sentiment"]["negative"], x["review_count"]), reverse=True)
        elif filter_type == "most_reviewed":
            product_cards.sort(key=lambda x: x["review_count"], reverse=True)
        elif filter_type == "mismatched":
            product_cards = [p for p in product_cards if p["has_mismatch"]]
            product_cards.sort(key=lambda x: x["mismatch_count"], reverse=True)
        else:
            # Default: sort by review count desc, then sentiment score desc
            product_cards.sort(key=lambda x: (x["review_count"], x["sentiment_score"]), reverse=True)

        catalog_count = len(product_ids)
        avg_sentiment = round(sentiment_scores_sum / catalog_count, 2) if catalog_count > 0 else 0.50
        pos_share = round(total_positive_reviews / total_catalog_reviews * 100, 1) if total_catalog_reviews > 0 else 0.0

        return {
            "status": "success",
            "kpis": {
                "total_products": catalog_count,
                "total_reviews_analyzed": total_catalog_reviews,
                "catalog_avg_sentiment_score": avg_sentiment,
                "positive_reviews_share": pos_share,
                "total_mismatches_detected": total_mismatches
            },
            "filter_applied": filter_type,
            "product_count": len(product_cards),
            "products": product_cards
        }
