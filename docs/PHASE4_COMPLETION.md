# Phase 4 Completion Report — Hybrid AI Recommendation System
**Project**: NexusAI / DB-Ecom  
**Phase**: Phase 4  
**Status**: COMPLETE (100% Verified)  
**Architecture**: Modular Multi-Signal Hybrid Recommender  
**Directory**: `ai/`

---

## 1. New AI Architecture

Phase 4 transforms NexusAI from a sequential fallback script into a **modular, multi-signal hybrid recommendation pipeline**. Rather than relying primarily on a single algorithm, the engine synthesizes four independent signals representing distinct dimensions of user intent and catalog behavior:

```
Customer Context
   │
   ├─► Purchase History (orders + order_items)
   ├─► Current Shopping Cart (shopping_cart)
   ├─► Recent Search Intent (search_history)
   └─► Product Catalog Metadata & Performance (v_product_performance)
   │
   ▼
Multi-Source Candidate Generation
   │
   ├─► [Source 1] Apriori Association Rules (consequents of known items)
   ├─► [Source 2] Content-Based Nearest Neighbors (TF-IDF cosine similarity)
   ├─► [Source 3] Search Intent Matches (TF-IDF query vector matching)
   └─► [Source 4] Community Popularity & Quality (rating, sales, reviews)
   │
   ▼
Candidate Filtering & Deduplication
   │  - Exclude already purchased products
   │  - Exclude items currently in active cart
   │  - Deduplicate candidate set
   │  - Apply inventory availability preference
   │
   ▼
Multi-Signal Feature Scoring
   │  - apriori_score       ∈ [0.0, 1.0] (confidence + logarithmic lift)
   │  - search_score        ∈ [0.0, 1.0] (query-document cosine similarity)
   │  - similarity_score    ∈ [0.0, 1.0] (catalog item cosine similarity)
   │  - popularity_score    ∈ [0.0, 1.0] (rating + sales + review volume)
   │
   ▼
Hybrid Ranking & Explainability Engine
   │  - Weighted Linear Combination:
   │    Final Score = 0.40 * Apriori + 0.25 * Search + 0.20 * Similarity + 0.15 * Popularity
   │  - Dominant signal attribution & human-readable reasoning
   │
   ▼
Top-N Ranked Recommendations
```

---

## 2. Files Created and Modified

| File | Status | Description |
|---|---|---|
| [`ai/utils.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/utils.py) | **Created** | Text tokenization, stopword removal, vector cosine similarity math, normalization helpers, and `CatalogMetadata` in-memory cache to prevent redundant database queries. |
| [`ai/ranking.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/ranking.py) | **Created** | `MultiSignalRanker` implementing configurable linear scoring, out-of-stock penalty scaling, signal contribution analysis, and transparent explainability statements. |
| [`ai/content_based.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/content_based.py) | **Modified** | Refactored to leverage shared utilities, added `compute_product_similarity`, `score_search_query`, and candidate neighborhood generation. |
| [`ai/apriori.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/apriori.py) | **Modified** | Added normalized `compute_affinity()` and `get_strongest_rules_for_candidates()` to resolve multiple matching rules for the same consequent item. |
| [`ai/recommender.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/recommender.py) | **Modified** | Rebuilt into the master orchestrator executing customer context retrieval, multi-source candidate generation, feature scoring, and fallback handling. |
| [`test_ai_verification.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/test_ai_verification.py) | **Modified** | Comprehensive test suite verifying Apriori math, content similarity, ranker weights, persona diversity, and metadata structure. |
| [`test_phase4_hybrid.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/test_phase4_hybrid.py) | **Created** | Automated integration verification testing multi-signal activations, edge cases, and live Flask API contract fidelity. |

---

## 3. Scoring Formula and Configurable Weights

All candidate product signals are normalized to a strict $[0.0, 1.0]$ interval before linear combination:

$$\text{Final Score} = w_{\text{apriori}} \cdot S_{\text{apriori}} + w_{\text{search}} \cdot S_{\text{search}} + w_{\text{similarity}} \cdot S_{\text{similarity}} + w_{\text{popularity}} \cdot S_{\text{popularity}}$$

### Configured Weights (`ai/ranking.py`):
- **Apriori Association Affinity ($w = 0.40$)**:
  $$S_{\text{apriori}} = 0.60 \cdot \text{Confidence} + 0.40 \cdot \frac{\ln(1 + \text{Lift})}{\ln(1 + \text{MaxLift})}$$
- **Search Intent Relevance ($w = 0.25$)**:
  $$S_{\text{search}} = \max_{q \in \text{Searches}} \cos(\vec{v}_q, \vec{v}_p)$$
- **Catalog Product Similarity ($w = 0.20$)**:
  $$S_{\text{similarity}} = \max_{k \in \text{KnownItems}} \cos(\vec{v}_k, \vec{v}_p)$$
- **Community Quality & Popularity ($w = 0.15$)**:
  $$S_{\text{popularity}} = 0.50 \cdot \frac{\text{Rating} - 1}{4} + 0.35 \cdot \frac{\text{Sales}}{\text{MaxSales}} + 0.15 \cdot \frac{\ln(1 + \text{Reviews})}{\ln(1 + \text{MaxReviews})}$$

### Availability Preference:
If a candidate item has `stock_quantity == 0`, a $0.35\times$ penalty factor is applied to ensure in-stock alternatives are favored for immediate customer purchase.

---

## 4. Candidate-Generation Process

Candidates are generated from four distinct pipelines to balance discovery, relevance, and co-purchase behavior:
1. **Apriori Consequents**: Evaluates all association rules where the antecedent is a subset of the customer's purchase history and active cart. Selects the strongest rule for each unique consequent product.
2. **Content-Based Neighbors**: Retrieves top 3 nearest neighbors via TF-IDF cosine similarity for each product in the customer's known items.
3. **Recent Search Queries**: Matches the customer's recent keywords against product descriptions and brand metadata. Any product achieving cosine similarity $> 0.15$ is added as a candidate.
4. **Community Popularity Backfill**: Adds the top 8 community favorites from analytical view `v_product_performance`.

### Filtering Rules:
- Any item present in `purchased_pids` is **excluded**.
- Any item present in `cart_pids` is **excluded**.
- Candidate IDs are merged and deduplicated into a single evaluation set.

---

## 5. API Response Metadata

The `/api/recommendations/<customer_id>` endpoint maintains 100% backward compatibility while delivering full explainability metadata:

```json
{
  "product_id": "P404",
  "product_name": "128GB High-Speed V30 SD Card",
  "brand": "DataPro",
  "category_name": "Photography & Video",
  "price": 39.99,
  "stock_quantity": 394,
  "score": 0.4587,
  "algorithm": "Hybrid (Apriori Market Basket Association)",
  "reason": "Frequently bought together with Weatherproof Camera Backpack (Confidence: 95%, Lift: 7.1x)",
  "apriori_score": 0.8253,
  "search_score": 0.0,
  "similarity_score": 0.1023,
  "popularity_score": 0.7209,
  "avg_rating": 4.0,
  "review_count": 3,
  "confidence": 0.9524,
  "lift": 7.1429
}
```

---

## 6. Verification and Test Results

### Automated Test Suites:
1. `python test_ai_verification.py` $\implies$ **100% PASS**:
   - Apriori math, frequent itemsets, and logarithmic affinity normalization verified.
   - TF-IDF indexing and vector cosine similarity verified.
   - Multi-signal ranking math and dominant attribution verified.
   - Persona diversity across 6 customers (`C101`, `C102`, `C103`, `C104`, `C107`, `C108`) verified.
   - Purchased item exclusion verified.
2. `python test_phase4_hybrid.py` $\implies$ **100% PASS**:
   - In-memory catalog cache verified (45 products, 466 rules).
   - Search intent signal activation verified for customer C108.
   - Apriori rule activation verified for customer C103.
   - Cold-start fallback verified for new/zero-history customers.
   - Live HTTP API contract over Flask verified.
3. `python test_api_verification.py` $\implies$ **100% PASS** (All 18 API routes functional).
4. `python test_customer_journey.py` $\implies$ **100% PASS** (Full 12-step commerce journey functional).

---

## 7. Known Limitations
1. **Catalog Scale**: The TF-IDF matrix is computed in-memory across the current 45 products. For catalogs with tens of thousands of SKUs, sparse matrix representations (e.g. Scipy CSR) or inverted indexing would be recommended.
2. **Static Category Weighting**: Weights are globally uniform across all categories. In specialized domains, search intent or Apriori affinity may warrant category-specific weight profiles.

---

## 8. Recommendations for Phase 5 (Advanced AI & Machine Learning)
1. **Customer Semantic Embeddings**: Generate low-dimensional dense embeddings for products and customer personas using lightweight sentence transformers.
2. **Aspect-Based Review Sentiment Scoring**: Parse user review text to extract sentiment polarity per product feature (e.g. battery life, build quality) to dynamically modulate the quality score.
3. **Demand Forecasting & Dynamic Replenishment**: Build time-series models on historical `orders` and `order_items` to forecast category demand.
4. **RFM Customer Segmentation**: Segment customers into behavioral tiers (High-Value VIP, Loyal, Cold) to dynamically tune the multi-signal weights.
