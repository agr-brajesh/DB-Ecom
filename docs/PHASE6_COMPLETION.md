# Phase 6 Completion Report: Explainable AI (XAI) & Trustworthy Recommendations

**Project**: NexusAI / DB-Ecom  
**Phase**: Phase 6 — Explainable AI & Trustworthy Recommendations  
**Status**: COMPLETE (100% Verified)  
**Architecture**: Modular Explanation Pipeline with Ground-Truth Safeguards  
**Modules**: [`ai/explanations.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/explanations.py), [`ai/recommender.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/recommender.py), [`ai/ranking.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/ranking.py)

---

## 1. Explanation Architecture

Phase 6 implements a **Dual-Tier Explainable AI (XAI) Pipeline** that guarantees full transparency, traceability, and trustworthiness without modifying the underlying database schema or introducing external machine learning dependencies.

### Target Pipeline Flow
```
Customer Context (Purchases, Active Cart, Recent Searches, Live View)
      │
      ▼
Hybrid / Context-Aware Recommendation Engine (MultiSignalRanker)
      │
      ▼
Composite Ranking Score (0.0 to 1.0)
      │
      ▼
Explanation Generator (ExplanationEngine in ai/explanations.py)
      │
      ├─► Signal Quantification & Active Weight Evaluation
      ├─► Provenance Attribution Pass (Determines true contributing sources)
      ├─► Safeguard Validation Filter (Rejects false claims: purchases, searches, rules)
      ├─► Human Reason Prioritizer (Sorts top 2–3 reasons by weighted contribution)
      ├─► AI Match Indicator Calibration (e.g., "86% AI Match • Strong Match")
      └─► Academic Viva Proof Assembler (Antecedent → Consequent, Lift, Cosine, TF-IDF)
      │
      ▼
Enriched Recommendation Output (Machine-Readable Schema + UI Renderers)
```

---

## 2. Files Created and Modified

| File | Status | Description |
|---|---|---|
| [`ai/explanations.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/explanations.py) | **Created** | Dedicated Explainable AI module implementing `ExplanationEngine`, signal threshold validation, provenance derivation, plain-language reason generator, and mathematical viva proof builder. |
| [`test_phase6_explainability.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/test_phase6_explainability.py) | **Created** | Comprehensive test suite validating all 10 recommendation contexts (A through J), safeguard invariants, and mathematical formulas. |
| [`docs/PHASE6_COMPLETION.md`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/docs/PHASE6_COMPLETION.md) | **Created** | Full Phase 6 documentation, technical specifications, and viva examination guide. |
| [`ai/recommender.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/recommender.py) | **Modified** | Imported and instantiated `ExplanationEngine`; integrated enrichment into `recommend`, `recommend_frequently_bought_together`, `recommend_product_alternatives`, and `recommend_complete_your_setup`. |
| [`ai/ranking.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/ranking.py) | **Modified** | Preserved candidate evidentiary metadata (`matched_antecedents`, `matched_search_query`, `matched_reference_product`, `support`) across ranking outputs. |
| [`backend/app.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/backend/app.py) | **Modified** | Added dedicated `/api/recommendations/audit/<customer_id>` endpoint for live admin/viva auditing. |
| [`frontend/index.html`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/frontend/index.html) | **Modified** | Embedded Explainable AI (XAI) & Recommendation Auditor into Admin AI Intelligence portal. |
| [`frontend/style.css`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/frontend/style.css) | **Modified** | Added CSS rules for `.ai-explanation-card`, `.ai-match-badge`, reason checkmarks, and the interactive XAI Auditor dashboard. |
| [`frontend/app.js`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/frontend/app.js) | **Modified** | Updated card rendering with subtle checkmark reasons and match badges; implemented `runXaiAudit()`, `initXaiAuditorControls()`, and `handleXaiContextChange()`. |
| [`test_phase5_context.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/test_phase5_context.py) | **Modified** | Added `app.test_client()` fallback to verify HTTP endpoints in isolated testing without external server dependency. |

---

## 3. Machine-Readable API Response Schema

Every recommendation object returned across all endpoints now provides the following structured fields:

```json
{
  "product_id": "P104",
  "product_name": "Multi-Port USB-C Hub",
  "brand": "ConnectPro",
  "price": 49.99,
  "category_name": "Computing & Laptops",
  "stock_quantity": 80,
  "score": 0.8642,
  "ai_match": "86% AI Match",
  "match_percentage": 86,
  "match_strength": "Exceptional Match",
  "recommendation_type": "COMPLETE_YOUR_SETUP",

  "signals": {
    "apriori": 0.9125,
    "search_intent": 0.7200,
    "content_similarity": 0.8841,
    "popularity": 0.7620,
    "inventory": 1.0,
    "apriori_score": 0.9125,
    "search_score": 0.7200,
    "similarity_score": 0.8841,
    "popularity_score": 0.7620,
    "inventory_score": 1.0
  },

  "source": [
    "apriori",
    "recent_search",
    "content_similarity",
    "popularity",
    "inventory"
  ],
  "provenance": [
    "apriori",
    "recent_search",
    "content_similarity",
    "popularity",
    "inventory"
  ],

  "reasons": [
    "Frequently purchased alongside your UltraBook Pro setup",
    "Matches your recent search for 'usb-c multiport hub'",
    "Currently in stock and ready to ship"
  ],

  "reason": "Frequently purchased alongside your UltraBook Pro setup",
  "algorithm": "Hybrid Explanation (COMPLETE_YOUR_SETUP)",

  "technical_explanation": {
    "ranking_position": 1,
    "final_score": 0.8642,
    "ai_match_percentage": 86,
    "recommendation_type": "COMPLETE_YOUR_SETUP",
    "context_profile": "cart",
    "scoring_formula": "Final = (w_apr × S_apr) + (w_srch × S_srch) + (w_sim × S_sim) + (w_pop × S_pop)",
    "weights_applied": {
      "apriori": 0.55,
      "search": 0.05,
      "similarity": 0.30,
      "popularity": 0.10
    },
    "signal_breakdown": {
      "apriori_score": 0.9125,
      "search_intent_score": 0.72,
      "content_similarity_score": 0.8841,
      "popularity_score": 0.762,
      "inventory_score": 1.0
    },
    "weighted_contributions": {
      "apriori": 0.5019,
      "search_intent": 0.036,
      "content_similarity": 0.2652,
      "popularity": 0.0762
    },
    "provenance_sources": [
      "apriori",
      "recent_search",
      "content_similarity",
      "popularity",
      "inventory"
    ],
    "apriori_details": {
      "active": true,
      "affinity_score": 0.9125,
      "rule_statement": "UltraBook Pro 15-inch Laptop → Multi-Port USB-C Hub",
      "support": 0.045,
      "confidence": 0.812,
      "lift": 2.14
    },
    "search_details": {
      "active": true,
      "score": 0.72,
      "matched_query": "usb-c multiport hub"
    },
    "similarity_details": {
      "active": true,
      "score": 0.8841,
      "reference_product": "UltraBook Pro 15-inch Laptop"
    },
    "popularity_details": {
      "score": 0.762,
      "avg_rating": 4.8,
      "review_count": 28
    },
    "inventory_details": {
      "in_stock": true,
      "stock_quantity": 80
    }
  }
}
```

---

## 4. Customer-Facing Explanation UI

In accordance with Phase 6 design principles, technical jargon (e.g., confidence percentages and lift multipliers) has been replaced on storefront cards with clear, subtle explanations:

```
┌────────────────────────────────────────────────────────┐
│ [Computing & Laptops]                                ♥ │
│ ConnectPro                                             │
│ Multi-Port USB-C Hub                                   │
│ ★★★★★ 4.8 (28)                                         │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ ⚡ COMPLETE YOUR SETUP              86% AI Match   │ │
│ │ ✓ Bought with your UltraBook Pro                   │ │
│ │ ✓ Matches your recent search for 'usb-c hub'       │ │
│ │ ✓ Currently in stock and ready to ship             │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ $49.99                      [+ Add to Cart]            │
│ In Stock (80)                                          │
└────────────────────────────────────────────────────────┘
```

### Key UI Features
- **Calibrated Match Badges**: Displays e.g., `86% AI Match` (Exceptional Match), `78% AI Match` (Strong Match), or `64% AI Match` (Good Match).
- **Checkmark Explanations**: 2–3 structured plain-language bullets highlighting the strongest contributing signals.
- **Glassmorphism Integration**: Dark-mode styling matching the application aesthetic.

---

## 5. Admin Technical Explanation UI (Viva Auditor)

The Admin portal (`#admin-tab-rules`) now features a dedicated **Explainable AI (XAI) & Recommendation Auditor**:
- **Persona Simulator**: Audits any customer persona (`C101`–`C108` or Guest User).
- **Shopping Context Switcher**: Simulates browsing (`default`), active search (`search_dominant`), product view (`product_view`), cart completion (`cart`), out-of-stock alternatives (`alternatives`), or cold start (`cold_start`).
- **Dynamic Weight Matrix**: Visualizes active linear combination weights ($w_{apr}, w_{srch}, w_{sim}, w_{pop}$).
- **Signal Contribution Meters**: Displays raw scores and weighted points for all 5 signals.
- **Mathematical & Symbolic Proof Box**:
  - Exact Association Rule: `{Antecedent} → {Consequent}`
  - Rule Metrics: `Support: X% | Confidence: Y% | Lift: Zx`
  - Lexical Search Evidence: Matched query with exponential recency decay
  - Content Similarity Evidence: Reference item and TF-IDF Cosine percentage
  - Provenance Tags: `[apriori]`, `[recent_search]`, `[content_similarity]`, `[popularity]`, `[inventory]`

---

## 6. Examples of Generated Explanations Across Contexts

| Scenario / Context | Customer State | Top Reason Shown to Customer | Provenance (`source`) | Underlying Technical Proof |
|---|---|---|---|---|
| **A. Historical Purchases** | Alex Rivera (`C101`) on Homepage | *"Frequently bought with your UltraBook Pro"* | `[apriori, similarity, popularity, inventory]` | Rule: `Laptop → Sleeve` (Conf: 74%, Lift: 2.1x) |
| **B. Search Active** | Customer searching for *"gaming keyboard"* | *"Matches your recent search for 'mechanical gaming keyboard'"* | `[recent_search, similarity, popularity, inventory]` | TF-IDF Query Cosine: 0.72 with exponential decay |
| **C. Product Detail View** | Customer inspecting Camera (`P401`) | *"Frequently bought together with Weatherproof Camera Backpack"* | `[apriori, content_similarity, popularity, inventory]` | Rule: `Camera Backpack → 128GB SD Card` (Conf: 81%, Lift: 2.8x) |
| **D. Active Cart** | Cart contains `Laptop` | *"Frequently bought with items currently in your cart"* | `[apriori, content_similarity, inventory]` | Cart item `P101` acts as Apriori seed; `P101` excluded |
| **E. Complete Your Setup** | Setup view for Workstation | *"Frequently purchased alongside your Workstation setup"* | `[apriori, content_similarity, inventory]` | Complementary category match (`CAT08`) with 84% affinity |
| **F. Out-of-Stock Alternative** | Target item stock $\le 0$ | *"Similar features and price range (92% spec match)"* | `[content_similarity, inventory]` | Same category, price ratio 1.05x, TF-IDF cosine 0.92 |
| **G. Cold Start / Guest** | Brand new user (0 records) | *"Popular choice among shoppers (4.8/5 stars across 32 reviews)"* | `[popularity, inventory]` | Cold start profile ($w_{pop} = 1.0$); 0 false history claims |

---

## 7. Verification & Test Report

### Automated Test Suite: `test_phase6_explainability.py`
All 10 scenarios and mathematical invariants passed with 100% success:
- **Scenario A (Purchase History)**: PASS (Purchased products excluded, valid Apriori explanations).
- **Scenario B (Recent Search)**: PASS (Search intent accurately traced in provenance & reasons).
- **Scenario C (Product View)**: PASS (Product view context verified, current product excluded).
- **Scenario D (Active Cart)**: PASS (Active cart items excluded, complementary items recommended).
- **Scenario E (Complete Your Setup)**: PASS (Multi-product setup peripheral complements verified).
- **Scenario F (Alternative Product)**: PASS (In-stock alternatives verified with spec match & price proximity).
- **Scenario G (Cold Start)**: PASS (Popularity baseline verified, 0 false purchase claims).
- **Scenario H (No Apriori Rule)**: PASS (No false Apriori claims, falls back to similarity & popularity).
- **Scenario I (No Search History)**: PASS (No false search claims, `recent_search` excluded from source).
- **Scenario J (Out-of-Stock Product)**: PASS (Inventory gate verified, zero-stock items excluded).
- **Mathematical Invariants**: PASS (Scoring formula `Final = w · S` and calibrated AI match indicators verified).

### Regression Verification:
- `python test_phase5_context.py`: **100% PASS** (all 7 scenarios + invariants + HTTP endpoints)
- `python test_ai_verification.py`: **100% PASS** (Apriori mining, TF-IDF cosine, multi-signal ranking)
- `python test_db_verification.py`: **100% PASS** (11 tables, 4 views, 2 triggers, 10 indexes, 0 FK violations)
- `node -c frontend/app.js`: **100% PASS** (0 syntax errors)

---

## 8. Bugs Fixed and Safeguards Enforced

1. **Terminal Charmap Encoding**:
   - Replaced raw unicode star symbols (`★`) with descriptive strings (`4.8/5 stars`) in generated text to ensure safe logging and terminal output across Windows PowerShell and cp1252 character sets.
2. **Strict Provenance Filtering**:
   - Ensured `sources` only contains signals that strictly exceed their activation thresholds and were actively verified against customer records.
3. **Evidentiary Metadata Forwarding**:
   - Updated `compute_candidate_score` in `ai/ranking.py` and `candidate_records` in `ai/recommender.py` to preserve `matched_antecedents`, `matched_search_query`, `matched_reference_product`, and `support` through the ranking pass into `ExplanationEngine`.

---

## 9. Known Limitations

1. **Lexical Stemming vs. Semantic Embeddings**:
   - Search intent matching utilizes TF-IDF and n-gram lexical token overlap rather than dense vector embeddings (preserved in accordance with phase constraints prohibiting external vector databases/deep learning).
2. **Rule Sparsity**:
   - Where Apriori support is below minimum thresholds, the engine falls back to pure content-based cosine similarity and analytical SQL view co-occurrences.

---

## 10. Recommendation for Phase 7

- **Predictive Customer Lifetime Value (CLV) & Dynamic RFM Segmentation**:
  Implement mathematical RFM (Recency, Frequency, Monetary) clustering on customer purchase transactions to deliver personalized promotional thresholds and loyalty tier benefits.
- **Automated Inventory Replenishment Triggers**:
  Introduce database triggers calculating rolling product sales velocity to forecast stock exhaustion dates and automate supplier reordering warnings.
