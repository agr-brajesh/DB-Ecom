# NEXUSAI — FINAL PROJECT HEALTH & ARCHITECTURAL REPORT

## 1. Project Identity & Academic Contribution

**NexusAI: An Explainable, Context-Aware E-Commerce Intelligence Platform**

The central contribution of NexusAI is **system-level relational integration**: bringing together normalized relational database design, ACID transactional integrity, database automation (triggers and views), and explainable, deterministic artificial intelligence into a production-grade e-commerce application.

Rather than treating AI as an isolated, external black box, NexusAI ensures every recommendation, customer segment, inventory velocity, and business insight is mathematically grounded in live database rows.

```
                                  NEXUSAI
                                     │
                        ┌────────────┴────────────┐
                        ↓                         ↓
                  CUSTOMER PORTAL           ADMIN PORTAL
                        │                         │
                        └────────────┬────────────┘
                                     ↓
                              FLASK API LAYER
                                     ↓
                           ┌─────────┴─────────┐
                           ↓                   ↓
                     RELATIONAL DB        AI / ANALYTICS
                           │                   │
                     Tables / Views       Recommendation
                     Triggers / Indexes   Customer Intelligence
                     Transactions         Inventory Intelligence
                                          Review Intelligence
                           └─────────┬─────────┘
                                     ↓
                                INSIGHTS / UI
```

---

## 2. Chronological Milestones & Features Implemented (Phases 1–10)

| Phase | Milestone Name | Key Technical Deliverables |
|---|---|---|
| **Phase 1** | Relational Database Baseline | 3NF/BCNF Schema (11 tables), Foreign Keys, Constraints, Sample Seeding |
| **Phase 2** | UI Architecture & Storefront | Dark-mode glassmorphic storefront, customer switcher, product catalog |
| **Phase 3** | Core E-Commerce Transactions | Shopping cart, wishlist, checkout transaction procedure, order history |
| **Phase 4** | Hybrid Recommendation Engine | Apriori association mining, TF-IDF cosine similarity, Multi-Signal ranker |
| **Phase 5** | Context-Aware Recommendations | Session event stream, real-time product view adaptation, dynamic cart boosts |
| **Phase 6** | Explainable AI (XAI) | Provenance tracing, human-readable reason translation, calibrated match % |
| **Phase 7** | Business Intelligence (RFM & Inventory)| 6-cohort RFM customer segmentation, run-rate velocity, stock cover days |
| **Phase 8** | NLP Review Intelligence | Lexicon sentiment polarity, aspect theme extraction, rating mismatch detection |
| **Phase 9** | Professional Admin BI Console | Executive KPIs, truthful period comparisons, SVG sales charts, consolidated matrix |
| **Phase 10**| Final Integration & DBMS Showcase | 10-step Viva tour, ACID Before/After state audit grid, 62 master tests |

---

## 3. Database Management System (DBMS) Concepts Demonstrated

1. **Entity-Relationship Modeling**: Real-world modeling of 11 entities with cardinality mappings ($1:1$, $1:N$, $M:N$).
2. **Third Normal Form (3NF) & Boyce-Codd Normal Form (BCNF)**: Complete elimination of insertion, deletion, and update anomalies.
3. **Primary & Foreign Key Referential Integrity**: Enforced with engine-level `PRAGMA foreign_keys = ON` and cascading deletes.
4. **Domain & Integrity Constraints**: `CHECK` constraints on monetary prices, stock counts, rating bounds, and status enumerations.
5. **M:N Associative Bridge Decomposition**: Multi-valued relationships decomposed via `order_items`, `shopping_cart`, `wishlist`, and `reviews`.
6. **Active Database Triggers**:
   - `trg_decrement_product_stock`: Automatic inventory decrement on order creation.
   - `trg_validate_stock_before_order`: Engine-level overdraft prevention guard.
7. **Analytical Database Views**: Decoupling complex reporting queries from core transactional tables (`v_market_basket`, `v_customer_purchase_summary`, `v_product_performance`, `v_frequent_product_pairs`).
8. **Performance B-Tree Indexes**: 11 indexes optimizing join paths and compound lookups.
9. **Query Execution Optimization**: Verified through live `EXPLAIN QUERY PLAN` inspection.
10. **ACID Transactional Integrity**: Atomic checkout with verified state comparison between `COMMIT` and simulated failure `ROLLBACK`.

---

## 4. Artificial Intelligence & Analytics Capabilities

- **Apriori Association Rule Mining**: Discovering co-purchase affinities ($X \to Y$) using Support, Confidence, and Lift.
- **TF-IDF Vector Space Modeling**: Content similarity matching product specifications and user search queries via Cosine Similarity.
- **Multi-Signal Calibrated Ranking**: Linear combination ($w_a=0.40, w_c=0.25, w_s=0.20, w_p=0.10, w_i=0.05$).
- **Context-Aware Dynamic Adaptation**: Session event tracking tailoring suggestions to active browsing state.
- **Explainable AI (XAI)**: Algorithmic transparency with mathematical proofs and zero hallucination.
- **RFM Customer Clustering**: Automated categorization into 6 actionable customer segments.
- **Inventory Run-Rate Forecasting**: Daily velocity estimation and days-of-stock cover calculation.
- **NLP Sentiment Analysis**: Aspect theme extraction and rating-review disagreement detection.

---

## 5. Master Automated Test Suite & Verification Results

All tests executed via the master test runner [`tests/run_all_tests.py`](../tests/run_all_tests.py):

```
======================================================================
 MASTER REGRESSION TEST SUMMARY
======================================================================
Total Tests Run   : 62
Passed            : 62
Failures          : 0
Errors            : 0
Elapsed Time      : 1.88s
======================================================================
[SUCCESS] ALL SYSTEM MODULES & REGRESSION INVARIANTS 100% VERIFIED!
```

### Breakdown of Test Suites:
- `tests/test_data_consistency.py`: **9 / 9 PASS** (Foreign keys, zero orphan records, monetary matching)
- `tests/test_acid_transactions.py`: **2 / 2 PASS** (Atomicity, trigger execution, full rollback restoration)
- `tests/test_security_audit.py`: **10 / 10 PASS** (SQL injection blocking, read-only mode, ID/quantity validation)
- `test_ai_verification.py`: **4 / 4 PASS** (Apriori math, TF-IDF cosine similarity, hybrid ranking, diversity)
- `test_phase6_explainability.py`: **10 / 10 PASS** (10 customer contexts, provenance tracing, mathematical proofs)
- `test_phase7_bi.py`: **11 / 11 PASS** (RFM customer segmentation, daily velocity, stock cover days)
- `test_phase8_reviews.py`: **13 / 13 PASS** (NLP sentiment, aspect extraction, rating mismatch detection)
- `test_phase9_admin.py`: **11 / 11 PASS** (Executive BI KPIs, historical comparisons, SVG timeline charts)
- `test_customer_journey.py`: **1 / 1 PASS** (12-step complete customer lifecycle)

---

## 6. Performance Observations

- **Zero N+1 Query Anti-Patterns**: All multi-entity views leverage SQL `JOIN` clauses and aggregation functions (`GROUP_CONCAT`, `SUM`, `COUNT`) rather than nested per-row queries.
- **Index Optimization**: B-Tree indexes on `order_items(order_id)`, `orders(customer_id)`, `orders(order_status, order_date)`, and `products(category_id)` ensure index scans instead of sequential table scans.
- **Lightweight SVG Visualizations**: Timeline charts and category share progress tracks are rendered with native SVG and CSS, eliminating large frontend chart dependencies.
- **Execution Speed**: The entire 62-test regression suite runs in under 2.0 seconds.

---

## 7. Security & Input Validation Audit

- **Read-Only SQL Engine Lock**: Live SQL Runner queries are executed against a SQLite connection opened strictly with `file:...mode=ro`.
- **Query Keyword Sanitization**: Commands containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`, or semicolons are rejected with HTTP 400.
- **Input Boundaries**: Cart additions and updates validate quantity bounds against available product stock (`quantity > 0` and `quantity <= stock_quantity`).
- **Zero Committed Secrets**: `.env.example` contains only configuration templates with zero live API keys or credentials.

---

## 8. Known Limitations & Future Improvements

1. **Distributed Database Scalability**: SQLite is an embedded single-writer database optimal for local deployments and demonstrations; scaling to enterprise traffic would involve PostgreSQL with connection pooling.
2. **Review Lexicon Scope**: The lexicon-based sentiment engine is tuned for electronics and hardware; multi-lingual sentiment would require expanding vocabulary dictionaries.
3. **Automated Purchase Orders**: In a live ERP system, low-stock triggers could be integrated with external supplier EDI gateways to automatically dispatch reorder shipments.

---

## 9. Recommended Run & Demonstration Instructions

1. Start application:
   ```bash
   python backend/app.py
   ```
2. Open in browser: `http://127.0.0.1:5000`
3. Click **"Admin & Database Lab"** in the top navigation bar.
4. Navigate to **Database Lab** $\to$ click any of the 10 steps in the **Evaluator Guided Demonstration** stepper to inspect the corresponding live functionality.
