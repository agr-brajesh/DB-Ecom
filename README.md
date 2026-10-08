# NexusAI: An Explainable, Context-Aware E-Commerce Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/DBMS-SQLite%203NF%2FBCNF-success.svg)](https://www.sqlite.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Database--First%20Hybrid%20AI-indigo.svg)](#architecture)
[![Tests](https://img.shields.io/badge/Tests-62%2F62%20Passing-brightgreen.svg)](#testing)

> **Academic Positioning**: NexusAI demonstrates the end-to-end integration of a normalized relational database (3NF/BCNF), ACID transactional integrity, active database automation (triggers & indexes), and deterministic, explainable artificial intelligence (market basket association mining, TF-IDF content similarity, session context awareness, RFM segmentation, and NLP sentiment analysis) within a unified enterprise e-commerce platform.
>
> Rather than relying on black-box external LLMs or vector databases, NexusAI highlights **system-level relational integration**: all analytical metrics, AI recommendations, customer cohorts, and inventory warnings are calculated directly from live relational transactions.

---

## 🏛️ System Architecture

```
                                  NEXUSAI
                                     │
                        ┌────────────┴────────────┐
                        ↓                         ↓
                  CUSTOMER PORTAL           ADMIN PORTAL
                  (Storefront, Cart,        (Executive BI, Inventory,
                   XAI Recommendations)      Reviews, Database Lab)
                        │                         │
                        └────────────┬────────────┘
                                     ↓
                               FLASK REST API
                                     ↓
                           ┌─────────┴─────────┐
                           ↓                   ↓
                     RELATIONAL DBMS      AI & ANALYTICS
                     (SQLite Engine)      (Deterministic Engines)
                           │                   │
                     11 3NF Tables        Apriori Association Mining
                     Foreign Keys         TF-IDF Cosine Similarity
                     CHECK Constraints    Multi-Signal Ranker
                     4 Analytical Views   Explainable AI Engine (XAI)
                     2 Automated Triggers RFM Customer Segmentation
                     11 B-Tree Indexes    Inventory Run-Rate Engine
                     ACID Transactions    NLP Review Sentiment
                           └─────────┬─────────┘
                                     ↓
                          LIVE PERSISTENCE & UI
```

---

## 🌟 Key Features Across 10 Phases

### 1. Database-First Relational Architecture (3NF/BCNF)
- **11 Normalized Tables**: `categories`, `products`, `customers`, `orders`, `order_items`, `payments`, `shopping_cart`, `reviews`, `search_history`, `wishlist`, `session_events`.
- **Primary & Foreign Keys**: Explicit PKs across all entities with relational actions (`ON DELETE CASCADE` on transactional child rows, `ON DELETE RESTRICT` on categories).
- **Domain CHECK Constraints**: Non-negative prices (`price >= 0`), non-negative stock (`stock_quantity >= 0`), ratings bounded to `1..5`, order states strictly restricted to `('PENDING', 'PROCESSING', 'COMPLETED', 'CANCELLED')`.
- **M:N Relationship Decomposition**: Associative bridge tables (`order_items`, `shopping_cart`, `wishlist`, `reviews`) eliminate multi-valued dependencies.

### 2. ACID Transactions & Database Automation
- **Atomic Checkout Workflow**: Explicit `BEGIN TRANSACTION` $\to$ cart validation $\to$ order insertion $\to$ item insertion $\to$ trigger execution $\to$ payment insertion $\to$ cart clearing $\to$ `COMMIT`.
- **Automated Triggers**:
  - `trg_decrement_product_stock`: Automatically decreases product inventory after an order item is created.
  - `trg_validate_stock_before_order`: Engine-level guard raising `RAISE(ABORT, 'Insufficient stock available')` if quantity exceeds available stock.
- **Auditable Rollback**: Simulated failure testing cleanly issues `ROLLBACK`, guaranteeing zero partial record persistence and complete inventory restoration.
- **11 B-Tree Indexes**: Query plan optimization on foreign keys, composites (`orders(order_status, order_date)`, `reviews(product_id, rating)`), and session timelines.
- **4 Analytical SQL Views**:
  - `v_market_basket`: Formats multi-product orders into comma-separated baskets for association mining.
  - `v_customer_purchase_summary`: Aggregates customer order frequency, items bought, and lifetime spend.
  - `v_product_performance`: Aggregates gross revenue, units sold, and review score metrics.
  - `v_frequent_product_pairs`: Pure SQL self-join finding frequent 2-item co-occurrence pairs.

### 3. Context-Aware Hybrid Recommendation Engine
- **Multi-Signal Calibrated Scoring**:
  $$\text{Score} = w_{\text{apriori}} S_{\text{apriori}} + w_{\text{content}} S_{\text{content}} + w_{\text{search}} S_{\text{search}} + w_{\text{pop}} S_{\text{pop}} + w_{\text{inv}} S_{\text{inv}}$$
  - **Apriori Association Mining (40%)**: Mines statistically significant co-purchase rules ($X \to Y$) calculating Support, Confidence, and Lift.
  - **TF-IDF Content Similarity (25%)**: Matches product specifications, titles, and tags using Cosine Similarity.
  - **Search Intent Matcher (20%)**: Leverages customer search queries to prioritize intention-aligned SKUs.
  - **Popularity & Rating Prior (10%)**: Bayesian-smoothed review ratings and unit volume.
  - **Inventory Availability (5%)**: Dynamic stock gate penalizing low-stock and excluding stock-out items.
- **Real-Time Contextual Adaptation**:
  - **Product View**: Excludes the item viewed and ranks complementary accessories.
  - **Active Cart**: Analyzes cart basket contents to recommend co-purchase additions and complete-your-setup bundles with 10% bundle discounts.
  - **Cold-Start Fallback**: Transparently provides high-rated, high-velocity catalog items without fabricating historical purchase affinity.

### 4. Explainable AI (XAI) & Algorithmic Transparency
- Transparent **"Why this recommendation?"** provenance modal for every recommendation.
- Maps algorithm signals into plain human English (e.g., *"Frequently bought with items in your cart"*, *"Matches your recent search for 'ergonomic keyboard'"*).
- Calibrated match indicator: `AI Match: 95% (Strong Affinity)`.

### 5. Business Intelligence & Operations Console
- **Executive Overview**: Real Total Revenue ($233,944.44), Orders (321), Active Customers (25), and Average Order Value ($728.80) dynamically filtered by `7d`, `30d`, `90d`, or `all`.
- **Truthful Historical Trends**: Computes genuine period-over-period $\uparrow / \downarrow$ percentages against matching historical windows; displays neutral baseline flags where prior data is non-comparable.
- **Sales Analytics**: Native SVG revenue timelines, category revenue shares summing to 100%, and payment method distributions.
- **Consolidated Product Intelligence**: Unified commercial velocity and stock cover days with NLP review sentiment, including 5-way sorting (`best_selling`, `highest_revenue`, `highest_rated`, `low_stock`, `poorly_reviewed`).
- **RFM Customer Segmentation**: Deterministic clustering into 6 cohorts (`HIGH VALUE`, `FREQUENT SHOPPER`, `ACTIVE SHOPPER`, `OCCASIONAL SHOPPER`, `NEW CUSTOMER`, `AT-RISK / INACTIVE`).
- **Operational Inventory Intelligence**: Run-rate velocity per day, stock coverage days, and actionable reorder queue.
- **Review Sentiment Intelligence**: Lexicon-based NLP sentiment scoring, positive/negative aspect themes, and rating-review mismatch alerts.
- **Grounded AI Insights**: Deterministic SQL alerts highlighting category volume leaders, low-stock high-velocity SKUs, hidden merchandising gems, and VIP customer churn risks.

### 6. Interactive Database Lab & Viva Demonstration
- **10-Step Viva Guided Tour**: One-click interactive walkthrough for evaluators demonstrating every capability from catalog browsing to ACID rollback.
- **Relational Schema & Normalization Matrix**: Visual inspector of 11 tables, constraints, triggers, and 3NF/BCNF proofs.
- **Live Read-Only SQL Console**: Sandboxed SQL executor with engine-level read-only protection (`file:...mode=ro`) and presets for `EXPLAIN QUERY PLAN` and `PRAGMA`.
- **ACID State Audit Grid**: Live Before vs After state comparison table proving stock decrements, cart clearing, and order logging on `COMMIT`, or complete restoration on `ROLLBACK`.

---

## 📦 Database Schema & Normalization

| Table Name | Primary Key | Foreign Keys & Relationships | Normal Form | Purpose |
|---|---|---|---|---|
| `categories` | `category_id` | - | BCNF | 8 product domains |
| `products` | `product_id` | `category_id` $\to$ `categories` | BCNF | 45 catalog SKUs with price and stock |
| `customers` | `customer_id` | - | BCNF | 25 registered customer profiles |
| `orders` | `order_id` | `customer_id` $\to$ `customers` | BCNF | Master transaction records |
| `order_items` | `order_item_id` | `order_id` $\to$ `orders`, `product_id` $\to$ `products` | BCNF | Resolves Order $\leftrightarrow$ Product M:N relationship |
| `payments` | `payment_id` | `order_id` $\to$ `orders` | BCNF | Payment method, status, and transaction settlement |
| `shopping_cart` | `cart_id` | `customer_id` $\to$ `customers`, `product_id` $\to$ `products` | BCNF | Persistent active shopping cart |
| `reviews` | `review_id` | `customer_id` $\to$ `customers`, `product_id` $\to$ `products` | BCNF | Customer ratings (1..5) and textual feedback |
| `search_history`| `search_id` | `customer_id` $\to$ `customers` | BCNF | Search queries powering search intent matching |
| `wishlist` | `wishlist_id` | `customer_id` $\to$ `customers`, `product_id` $\to$ `products` | BCNF | Customer saved items |
| `session_events`| `event_id` | `customer_id` $\to$ `customers`, `product_id` $\to$ `products` | BCNF | Real-time session event stream for contextual AI |

---

## 🚀 Setup & Execution Guide

### Prerequisites
- Python 3.10, 3.11, or 3.12
- SQLite 3 (built into standard Python)
- Web browser (Chrome, Edge, Firefox, Safari)

### 1. Installation
Clone the repository and install the minimal dependencies:
```bash
git clone https://github.com/agr-brajesh/DB-Ecom.git
cd "DB Project"
pip install -r requirements.txt
```

### 2. Database Initialization (Seed 45 SKUs & 320+ Transactions)
```bash
python database/seed_data.py
```

### 3. Start Application Server
```bash
python backend/app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## 🧪 Master Test Suite & Verification

Run the master automated regression test suite:
```bash
python tests/run_all_tests.py
```

### Test Coverage Summary (62 / 62 Tests Passing)
- **Database Consistency Audit** (`tests/test_data_consistency.py`): 9 tests verifying PRAGMA foreign keys, zero orphan records, payment amount matches, and rating/stock bounds.
- **ACID Transactions & Rollback** (`tests/test_acid_transactions.py`): 2 tests verifying atomicity, triggers, and full state restoration on failure.
- **Security & Input Validation** (`tests/test_security_audit.py`): 10 tests verifying SQL injection blocking, DDL write guards, read-only engine locks, and ID validations.
- **Core AI Recommender Engine** (`test_ai_verification.py`): 4 tests verifying Apriori math, TF-IDF cosine similarity, multi-signal ranking, diversity, and cold-start fallback.
- **Phase 6: Explainable AI** (`test_phase6_explainability.py`): 10 scenarios verifying transparent explanations across all customer contexts.
- **Phase 7: Business Intelligence** (`test_phase7_bi.py`): 11 tests verifying RFM segmentation, sales velocity, and stock coverage calculations.
- **Phase 8: NLP Review Intelligence** (`test_phase8_reviews.py`): 13 tests verifying sentiment scoring, aspect extraction, and rating mismatch detection.
- **Phase 9: Admin Analytics** (`test_phase9_admin.py`): 11 tests verifying real executive KPIs, period-over-period comparisons, and sales timelines.
- **End-to-End Customer Lifecycle** (`test_customer_journey.py`): Complete 12-step customer lifecycle test from catalog browsing to cart, checkout, stock decrements, and order history.

---

## 🎓 Evaluator Viva Walkthrough (10 Demonstration Steps)

When presenting to an evaluator, follow this 10-step sequence:

1. **Catalog Browsing**: Switch customer persona (`C101` $\to$ `C108`), explore the 8 product domains and live catalog.
2. **Contextual AI Recommendations**: View personalized recommendations; observe how viewing a laptop changes suggestions to USB-C hubs and sleeves.
3. **Transparent Explainability (XAI)**: Click *"Why this recommendation?"* on any product card to inspect mathematical signal breakdown and provenance proofs.
4. **Smart Cart & Market Basket**: Add a product to cart; open the Cart Drawer to inspect the Apriori co-purchase bundle with 10% savings.
5. **Executive Sales Analytics**: Open the Admin Portal $\to$ *Sales Analytics* to view real daily SVG revenue charts and category revenue shares.
6. **Operational Inventory Intelligence**: Inspect *Inventory Intelligence* for daily run-rate velocities, cover days, and the restock queue.
7. **NLP Review Sentiment**: Open *Review Intelligence* to inspect storewide health, aspect themes (Build Quality, Battery Life, Performance), and rating-text mismatch detection.
8. **Analytical SQL Views**: Open *Database Lab* $\to$ *Analytical Database Views* and query `v_market_basket` and `v_customer_purchase_summary` live.
9. **EXPLAIN QUERY PLAN**: Click *EXPLAIN: Order Items Index* in the SQL Console to demonstrate SQLite B-tree index scans.
10. **ACID Transaction & Rollback Demonstration**:
    - Select Mode: *Simulate Payment Gateway Failure (ROLLBACK)* $\to$ Click *Execute ACID Transaction*.
    - Inspect the Before vs After table proving that stock is preserved, cart is kept intact, and zero partial records are inserted.
    - Switch to *Normal Transaction (COMMIT)* $\to$ Click *Execute ACID Transaction* to observe atomic order insertion and trigger-driven stock decrement.

---

## 📖 Detailed Technical Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) &mdash; Complete system architecture, component boundaries, and request lifecycle.
- [`docs/AI_ARCHITECTURE.md`](docs/AI_ARCHITECTURE.md) &mdash; Mathematical formulation of Apriori mining, TF-IDF cosine similarity, multi-signal ranking, and XAI.
- [`docs/DBMS_FEATURES.md`](docs/DBMS_FEATURES.md) &mdash; 3NF/BCNF proofs, ER diagram data dictionary, triggers, indexes, and views.
- [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) &mdash; Complete OpenAPI specification of all 26+ REST endpoints.
- [`docs/FINAL_PROJECT_REPORT.md`](docs/FINAL_PROJECT_REPORT.md) &mdash; Executive final report, performance benchmarks, and academic defense.

---

## 📜 License & Academic Integrity

Developed for advanced DBMS and Artificial Intelligence coursework. Built strictly using open-source, deterministic algorithms without proprietary external APIs.
