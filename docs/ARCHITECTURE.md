# NexusAI System Architecture

## 1. Architectural Overview

NexusAI is designed with a **Database-First, Deterministic Intelligence** architectural pattern. All analytical models, business intelligence metrics, customer segment classifications, and personalized recommendations are derived dynamically from normalized relational state rather than black-box caches or opaque external APIs.

```
                    ┌────────────────────────────────────────────────────────┐
                    │                      WEB CLIENT                        │
                    │   Customer Storefront   │     Admin BI Operations      │
                    │   - Product Catalog     │     - Executive KPIs         │
                    │   - Shopping Cart       │     - Sales Analytics        │
                    │   - XAI Recommendations │     - Inventory Intel        │
                    │   - Customer Profile    │     - Review Intelligence    │
                    │   - Cart Bundles        │     - Database Lab / SQL     │
                    └─────────────────────────┬──────────────────────────────┘
                                              │ HTTP JSON REST
                                              ▼
                    ┌────────────────────────────────────────────────────────┐
                    │                    FLASK API LAYER                     │
                    │  - Routing & Request Validation                        │
                    │  - Session & Identity Context Management               │
                    │  - Error Handling & HTTP Status Serialization          │
                    │  - Read-Only SQL Sandboxed Runner                      │
                    └───────────────┬────────────────────────┬───────────────┘
                                    │                        │
                    ┌───────────────▼────────┐      ┌────────▼───────────────┐
                    │   RELATIONAL DATABASE  │      │ AI & ANALYTICS LAYER   │
                    │   (SQLite Engine 3.x)  │      │                        │
                    │ - 11 Normalized Tables │      │ - Apriori Rule Miner   │
                    │ - B-Tree Indexes       │◄────►│ - Content TF-IDF Eng.  │
                    │ - Automated Triggers   │      │ - Multi-Signal Ranker  │
                    │ - 4 Analytical Views   │      │ - Explainability (XAI) │
                    │ - ACID Transaction Mgr │      │ - RFM Segmentation     │
                    │                        │      │ - Inventory Run-Rate   │
                    │                        │      │ - NLP Review Sentiment │
                    └────────────────────────┘      └────────────────────────┘
```

---

## 2. Core Architectural Layers

### Layer 1: Presentation & User Experience (Frontend)
- **Technology**: Vanilla HTML5, CSS3 with dark-mode glassmorphism, native ES6+ JavaScript.
- **Client Modularity**:
  - `storefront`: Product catalog, filtering by 8 domains, customer switcher, full-text search suggestions, persistent wishlist, cart drawer.
  - `recommendations`: Multi-context carousels (Personalized, Frequently Bought Together, Complete Your Setup, Similar Products, Alternatives).
  - `xai_modal`: Transparent algorithmic provenance and signal breakdown for each recommendation.
  - `admin_bi`: Executive KPI metrics, period-over-period comparisons, SVG timeline charts, consolidated product table, RFM segments, restock queues.
  - `database_lab`: 10-step evaluator guided stepper, schema normalization matrix, live view runner, EXPLAIN QUERY PLAN benchmarks, and ACID transaction simulator.

### Layer 2: API & Gateway Layer (Flask Backend)
- **Location**: `backend/app.py`
- **Responsibilities**:
  - Exposes 26+ structured REST endpoints.
  - Validates query strings and JSON payloads (quantity ceiling bounds, customer ID existence).
  - Sanitizes live SQL queries through token analysis and sets SQLite connection URI to `file:...mode=ro` to enforce read-only safety.
  - Orchestrates transactions by calling `database/transactions.py`.

### Layer 3: Relational Persistence Layer (SQLite Engine)
- **Schema**: 11 tables strictly normalized to 3NF and BCNF.
- **Engine Rules**:
  - `PRAGMA foreign_keys = ON` enforced on every connection.
  - Referential integrity: `ON DELETE CASCADE` on transactional children; `ON DELETE RESTRICT` on categories.
  - Engine-level triggers: `trg_decrement_product_stock` and `trg_validate_stock_before_order`.
  - Analytical Views: Pre-compiled relational queries (`v_market_basket`, `v_customer_purchase_summary`, `v_product_performance`, `v_frequent_product_pairs`).
  - Performance B-Tree Indexes: 11 indexes eliminating table scans on foreign keys and compound lookups.

### Layer 4: AI, Analytics & Business Intelligence Engine
- **Location**: `ai/` package
- **Deterministic Modules**:
  1. `ai.apriori.AprioriMiner`: Association rule mining over `v_market_basket` calculating Support, Confidence, and Lift.
  2. `ai.content_based.ContentBasedRecommender`: Tokenization, stopword removal, and TF-IDF Cosine Similarity over product titles, specifications, and descriptions.
  3. `ai.ranking.MultiSignalRanker`: Calibrated linear combination of association, content, search, popularity, and stock availability signals.
  4. `ai.explanations.ExplanationEngine`: Deterministic translation of candidate mathematical signal provenance into human-readable proofs.
  5. `ai.business_intelligence.BusinessIntelligenceEngine`: RFM customer segmentation and inventory stock cover estimation.
  6. `ai.sentiment.ReviewSentimentAnalyzer`: Domain-specific lexicon NLP scoring and rating-text disagreement detection.
  7. `ai.analytics_engine.AdminAnalyticsEngine`: Executive rollups, true period-over-period comparisons, and verifiable business insights.

---

## 3. End-to-End Data & Execution Lifecycle

### Scenario A: Context-Aware Recommendation Pipeline
1. Client requests `GET /api/recommendations/<customer_id>`.
2. Flask retrieves active customer context (search history from `search_history`, recent views from `session_events`, cart contents from `shopping_cart`, and purchases from `orders`).
3. `ProductRecommender` gathers candidate products:
   - Apriori co-purchase rules matching purchased/carted items.
   - TF-IDF content similarity matching viewed/purchased items.
   - Search intent matching customer's recent queries.
4. `MultiSignalRanker` scores candidates using normalized weights:
   $$S = 0.40 S_{\text{apriori}} + 0.25 S_{\text{content}} + 0.20 S_{\text{search}} + 0.10 S_{\text{pop}} + 0.05 S_{\text{inv}}$$
5. Stock Gate filters out any SKU where `stock_quantity <= 0`.
6. Deduplication excludes already-purchased items and items currently in the cart.
7. `ExplanationEngine` inspects the candidate's active signals and constructs explainability proof metadata.
8. Flask returns structured JSON array to client for rendering.

### Scenario B: Atomic Checkout Transaction Lifecycle
1. Client initiates `POST /api/checkout` with `customer_id` and `payment_method`.
2. `database.transactions.checkout_cart` acquires a database connection and executes `BEGIN TRANSACTION;`.
3. Validates that cart is non-empty and every item's `quantity <= stock_quantity`.
4. Inserts parent record into `orders`.
5. Iterates through cart items and inserts each row into `order_items`.
6. Engine trigger `trg_decrement_product_stock` executes immediately `AFTER INSERT`, reducing `products.stock_quantity`.
7. Inserts payment settlement record into `payments`.
8. Deletes items from `shopping_cart` for that customer.
9. Calls `conn.commit()`. If an exception occurs at any point (or `simulate_fail=True`), `conn.rollback()` executes, reverting all staged writes.
