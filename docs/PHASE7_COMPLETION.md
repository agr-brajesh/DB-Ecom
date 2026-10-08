# Phase 7 Completion Report: Business Intelligence & Inventory Intelligence

**Project**: NexusAI / DB-Ecom  
**Phase**: Phase 7 — Business Intelligence: Customer Segmentation & Inventory Intelligence  
**Status**: COMPLETE (100% Verified)  
**Architecture**: Autonomous Relational Analytics & Deterministic RFM Cohort Engine  
**Modules**: [`ai/business_intelligence.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/business_intelligence.py), [`backend/app.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/backend/app.py), [`frontend/index.html`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/frontend/index.html), [`frontend/app.js`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/frontend/app.js), [`frontend/style.css`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/frontend/style.css)

---

## 1. Executive Summary

Phase 7 elevates NexusAI from an intelligent personalized shopping system into an **intelligent enterprise commerce platform**. It equips store operators with two levels of explainable business intelligence:

1. **Customer Intelligence**: Understands *who* customers are through normalized Recency, Frequency, Monetary (RFM) modeling, classifying accounts into deterministic, explainable cohorts (High Value, Frequent Shopper, Active Shopper, Occasional Shopper, New Customer, At-Risk / Inactive).
2. **Inventory & Business Intelligence**: Monitors real-time sales velocities ($v = \text{sold} / \Delta t$), forecasts days of remaining stock coverage, identifies stockout hazards before they occur, flags excess capital locked in overstocked items, and surfaces high-conviction strategic insights backed by real transactional data.

All analytical computations are **100% derived from existing normalized relational tables and views** (`customers`, `orders`, `order_items`, `products`, `reviews`, `v_customer_purchase_summary`, `v_product_performance`, `v_frequent_product_pairs`). No external LLMs, black-box neural networks, embeddings, or vector databases were introduced, preserving database performance, ACID transaction guarantees, and university exam explainability.

---

## 2. Customer Intelligence & Segmentation Methodology

### RFM Mathematical Formulation
Customer purchasing behavior is evaluated across three fundamental dimensions relative to the store's transaction horizon:

- **Recency ($R$)**: Number of days elapsed between the store's reference date and the customer's most recent completed order.
  $$\Delta t_{\text{recency}} = t_{\text{ref}} - \max(t_{\text{order}})$$
  *(If customer has 0 orders, $R = \text{None}$ / Infinity).*
- **Frequency ($F$)**: Total count of completed purchase orders:
  $$F = \sum \mathbf{1}_{\{ \text{order\_status} = \text{'COMPLETED'} \}}$$
- **Monetary ($M$)**: Total cumulative lifetime spend on completed transactions:
  $$M = \sum_{\text{orders}} \sum_{\text{items}} (\text{quantity} \times \text{unit\_price})$$
- **Average Order Value (AOV)**:
  $$\text{AOV} = \begin{cases} \frac{M}{F} & \text{if } F > 0 \\ 0.00 & \text{if } F = 0 \end{cases}$$

### Normalized RFM Scoring (1 to 5 Scale)
Each customer is scored on a normalized 1–5 scale across each dimension:

| Score | Recency ($R$) | Frequency ($F$) | Monetary ($M$) |
|:---:|:---|:---|:---|
| **5** | $\le 14$ days | $\ge 20$ orders | $\ge \$13,000$ |
| **4** | $15 - 35$ days | $12 - 19$ orders | $\$9,000 - \$12,999$ |
| **3** | $36 - 60$ days | $6 - 11$ orders | $\$4,000 - \$8,999$ |
| **2** | $61 - 90$ days | $2 - 5$ orders | $\$1,000 - \$3,999$ |
| **1** | $> 90$ days or 0 orders | $\le 1$ order | $< \$1,000$ |

$$\text{Composite RFM Index} = (S_R \times 0.30) + (S_F \times 0.35) + (S_M \times 0.35)$$

### Deterministic Customer Cohorts
Customers are classified deterministically with human-readable evidentiary proofs:

1. **HIGH VALUE**: Lifetime spend $M \ge \$12,000$ OR ($M \ge \$9,000$ and $F \ge 10$).
   - *Evidence Proof*: Top-tier lifetime spend ($X), high repeat commitment ($Y orders), substantial AOV ($Z).
   - *Strategic Action*: VIP Concierge onboarding with dedicated priority support and drop access.
2. **FREQUENT SHOPPER**: Repeat order count $F \ge 12$ orders.
   - *Evidence Proof*: High transaction habit ($F orders), substantial cumulative spend ($M).
   - *Strategic Action*: Loyalty habit rewards to sustain high cadence.
3. **ACTIVE SHOPPER**: Recent purchase $R \le 35$ days and $F \ge 2$ orders.
   - *Evidence Proof*: Recent store activity ($R days ago), engaged profile ($F orders).
   - *Strategic Action*: Cross-sell acceleration with compatible accessories.
4. **OCCASIONAL SHOPPER**: Intermittent order history $2 \le F < 12$ with moderate elapsed time.
   - *Evidence Proof*: Moderate lifetime spend, intermittent cadence.
   - *Strategic Action*: Re-engagement banners and seasonal new arrival updates.
5. **AT-RISK / INACTIVE**: Long dormancy $R > 75$ days with modest spend ($M < \$3,500$).
   - *Evidence Proof*: Dormant account ($R days since last order), declining order velocity.
   - *Strategic Action*: Targeted win-back campaign with category incentives.
6. **NEW CUSTOMER**: Account with 0 orders OR early lifecycle with $F \le 1$ order.
   - *Evidence Proof*: Initial purchase or pending first order, early lifecycle.
   - *Strategic Action*: Onboarding nurturing with first/second-order incentive.

---

## 3. Inventory Intelligence & Velocity Methodology

### Demand Indicators
- **Active Store Span**: Analyzes transaction duration across the store history:
  $$\Delta t_{\text{span}} = \max(t_{\text{order}}) - \min(t_{\text{order}})$$
- **Average Daily Sales Velocity ($v$)**:
  $$v = \frac{\text{Total Units Sold}}{\Delta t_{\text{span}}}$$
- **Recent Sales Velocity ($v_{\text{recent}}$)**: Units sold within the recent window (e.g. 30 days) divided by 30 days.
- **Estimated Days of Stock Cover**:
  $$\text{Cover Days} = \begin{cases} 0.0 & \text{if } \text{stock} = 0 \\ \frac{\text{Current Stock Quantity}}{v} & \text{if } v > 0 \\ \text{None (No Velocity)} & \text{if } v = 0 \end{cases}$$

### Inventory Risk States
- **OUT OF STOCK**: $\text{stock\_quantity} = 0$. (Item completely unavailable).
- **CRITICAL**: $\text{Cover Days} \le 150 \text{ days}$ OR ($\text{stock} \le 50$ and $v \ge 0.25/\text{day}$).
- **LOW STOCK**: $\text{Cover Days} \le 300 \text{ days}$ OR ($\text{stock} \le 100$ and $v \ge 0.20/\text{day}$).
- **HEALTHY**: Balanced coverage sufficient for normal consumer cycles.
- **OVERSTOCKED**: $\text{Cover Days} > 750 \text{ days}$ with $\text{stock} \ge 200$, or $\text{stock} \ge 350$ with $v < 0.35/\text{day}$.
- **INSUFFICIENT HISTORY**: 0 lifetime units sold (no velocity recorded).

### Restock Recommendations
Derives actionable replenishment priority orders:
- **Urgent Action**: Suggests concrete reorder quantity based on target 45–60 day buffer:
  $$\text{Reorder Units} = \max(25, \text{round}(v \times 60 - \text{Current Stock}))$$
- Phrased realistically: e.g., *"Estimated stock-out in ~23 days"* (no false future certainty).

---

## 4. Product Intelligence & Matrix

Blends operational stock tracking with commercial performance:
- **Revenue Rank (#1 to #45)**: Assigned via gross revenue from `v_product_performance`.
- **Volume Rank (#1 to #45)**: Assigned via total units sold.
- **Sentiment**: Exposes average customer rating (1.0–5.0) and total verified review count.
- **Market Basket Companion**: Identifies strongest co-purchased SKU from `v_frequent_product_pairs`.

---

## 5. AI Business Insights (Actionable Live Briefings)

Derives autonomous strategic insights strictly from database metrics:
1. **Category Revenue Dominance**: Identifies top category revenue share (e.g. *Computing & Laptops generates 32.0% of store sales ($75,199.19)*).
2. **Restock Priority Alert**: Surfaces top velocity SKU nearing stockout (e.g. *Mirrorless 4K Camera has 1.88/day velocity and ~23 days cover*).
3. **Customer Pareto Disproportion**: Quantifies concentration (e.g. *Top 20% of customers generate 36.0% of total lifetime sales*).
4. **Catalog Hidden Gem**: Highlights high rating, low volume items (e.g. *27-inch 4K UHD Monitor has 5.0/5.0 rating but 0 sales*).
5. **Market Basket Synergy**: Highlights top co-purchase affinity pair (e.g. *Camera and 128GB SD Card co-purchased 34 times*).
6. **Working Capital Efficiency**: Calculates capital locked in surplus stock (e.g. *$17,352.33 in capital locked in excess whey protein inventory*).

---

## 6. Files Created and Modified

| File | Status | Description |
|---|---|---|
| [`ai/business_intelligence.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/ai/business_intelligence.py) | **Created** | Core Business Intelligence Engine implementing RFM modeling, cohort segmentation, inventory velocity analytics, risk states, restock recommendations, and actionable business insights. |
| [`test_phase7_bi.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/test_phase7_bi.py) | **Created** | Comprehensive unit and integration test suite covering scenarios A through K. |
| [`docs/PHASE7_COMPLETION.md`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/docs/PHASE7_COMPLETION.md) | **Created** | Full Phase 7 architectural specification, formulas, API documentation, and viva defense guide. |
| [`backend/app.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/backend/app.py) | **Modified** | Added 5 dedicated REST endpoints: `/api/admin/customer-segments`, `/api/admin/customer/<id>/insights`, `/api/admin/inventory-intelligence`, `/api/admin/product-intelligence`, and `/api/admin/ai-insights`. |
| [`frontend/index.html`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/frontend/index.html) | **Modified** | Added 4 new admin sections: Customer Intelligence, Inventory Intelligence, Product Intelligence, and AI Insights, plus updated sidebar navigation. |
| [`frontend/style.css`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/frontend/style.css) | **Modified** | Added design system extensions for visual segment bars, RFM chips, risk badges, restock cards, and strategic briefing cards. |
| [`frontend/app.js`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/frontend/app.js) | **Modified** | Implemented interactive frontend data loaders, filters, search inputs, customer detail inspector, and chart renderers. |

---

## 7. REST API Endpoints Specification

### 1. `GET /api/admin/customer-segments`
Returns complete customer portfolio RFM distribution and customer list.
- **Response**:
```json
{
  "status": "success",
  "overall_metrics": {
    "total_customers": 25,
    "active_shoppers": 19,
    "total_revenue": 234891.45,
    "avg_spend_per_customer": 9395.66,
    "overall_aov": 736.34,
    "avg_order_frequency": 12.8
  },
  "segment_counts": {
    "HIGH VALUE": 15,
    "FREQUENT SHOPPER": 2,
    "ACTIVE SHOPPER": 2,
    "OCCASIONAL SHOPPER": 1,
    "NEW CUSTOMER": 0,
    "AT-RISK / INACTIVE": 5
  },
  "segment_breakdown": [
    {
      "segment": "HIGH VALUE",
      "count": 15,
      "percentage": 60.0,
      "total_spend": 218731.84,
      "avg_spend": 14582.12,
      "avg_orders": 19.3,
      "aov": 756.86,
      "badge_class": "badge-high-value"
    }
  ],
  "customers": [...]
}
```

### 2. `GET /api/admin/customer/<customer_id>/insights`
Returns detailed customer profile with RFM proofs and actionable recommendations.
- **Response**:
```json
{
  "status": "success",
  "customer": {
    "customer_id": "C101",
    "name": "Alex Rivera",
    "email": "alex.rivera@example.com",
    "city": "Seattle",
    "total_orders": 10,
    "lifetime_spend": 6914.86,
    "aov": 691.49,
    "recency_days": 0,
    "rfm_scores": {
      "recency_score": 5,
      "frequency_score": 3,
      "monetary_score": 3,
      "composite_score": 3.6,
      "rfm_tier": "R5F3M3"
    },
    "segment": "ACTIVE SHOPPER",
    "reasons": [
      "Recent store activity (0 day(s) since last completed order)",
      "Engaged customer profile (10 order(s), $6,914.86 lifetime spend)",
      "Active presence across product catalog"
    ],
    "suggested_action": "Cross-Sell Acceleration: Recommend compatible ecosystem accessories based on recent purchases.",
    "top_categories": [...],
    "top_products": [...]
  }
}
```

### 3. `GET /api/admin/inventory-intelligence?recent_days=30`
Returns inventory demand velocities, days of coverage, and prioritized restock recommendations.

### 4. `GET /api/admin/product-intelligence`
Returns product commercial matrix, revenue/volume ranks, rating sentiment, and companion co-purchase affinity.

### 5. `GET /api/admin/ai-insights`
Returns actionable business intelligence insights strictly derived from actual database data.

---

## 8. Verification & Test Results

The test suite [`test_phase7_bi.py`](file:///c:/Users/agrbr/OneDrive/Desktop/DB%20Project/test_phase7_bi.py) executes 11 comprehensive automated tests covering all requirements:

| Test ID | Scenario | Result | Notes |
|---|---|:---:|---|
| **Test A** | Multiple customer RFM segmentation | **PASS** | 25 customers segmented; counts sum to 25; percentages sum to 100%. |
| **Test B** | New customer classification | **PASS** | Frequency $\le 1$ evaluated as NEW CUSTOMER with R5F1M1 scores. |
| **Test C** | Frequent customer classification | **PASS** | Frequency $\ge 12$ categorized as FREQUENT SHOPPER; habit proofs verified. |
| **Test D** | High-value customer classification | **PASS** | Lifetime spend $\ge \$12,000$ categorized as HIGH VALUE; VIP action verified. |
| **Test E** | Customer with zero orders | **PASS** | $F=0, M=0.0$; zero division errors; classified as NEW CUSTOMER. |
| **Test F** | High sales velocity product | **PASS** | Stock 42, Vel 8.1/day $\implies$ Cover 5.2 days; CRITICAL restock flagged. |
| **Test G** | Low-stock product | **PASS** | Stock 50, Vel 0.25/day $\implies$ Cover 200 days; LOW STOCK flagged. |
| **Test H** | Out-of-stock product | **PASS** | Stock 0 $\implies$ Cover 0.0 days; OUT OF STOCK immediate replenishment. |
| **Test I** | SKU with zero sales history | **PASS** | Units sold 0 $\implies$ Vel 0.0, Cover None; INSUFFICIENT HISTORY verified. |
| **Test J** | 5 Admin REST Endpoints | **PASS** | All endpoints return 200 OK with validated JSON structures. |
| **Test K** | Non-regression verification | **PASS** | Hybrid recommendations, Phase 6 XAI explanations, and DBMS views intact. |

### Storewide Full Test Suite Results
```
test_db_verification.py          -> PASS
test_ai_verification.py          -> PASS
test_api_verification.py         -> PASS
test_phase5_context.py           -> PASS
test_phase6_explainability.py    -> PASS
test_phase7_bi.py                -> PASS
test_customer_journey.py         -> PASS (Live HTTP)
test_phase4_hybrid.py            -> PASS (Live HTTP)

ALL SUITES STATUS: ALL PASS
```

---

## 9. Known Limitations

1. **Static Analysis Window**: The default sales velocity calculation divides lifetime units sold by the dataset's active order span (115 days). While recent window velocity (30 days) is also exposed, highly seasonal bursts require exponential smoothing or moving averages.
2. **Rule-Based RFM Thresholds**: RFM score boundaries use fixed commercial thresholds suited to this catalog's price range ($10–$1,300) rather than dynamically adjusted quantile percentiles.
3. **No External Forecasting Models**: Demand estimation strictly reports current daily sales run-rate and days coverage; it does not claim future demand or incorporate calendar holidays.

---

## 10. Recommendations for Phase 8

1. **Automated Replenishment Workflows**: Implement one-click simulated purchase orders from the Admin Restock Recommendations screen to directly adjust `products.stock_quantity`.
2. **Customer Cohort Campaign Simulator**: Add an admin feature to simulate the revenue impact of targeted discount codes sent to the "AT-RISK / INACTIVE" or "NEW CUSTOMER" cohorts.
3. **Seasonal Trend Detection**: Implement lightweight polynomial regression or EWMA (Exponentially Weighted Moving Average) in pure Python to detect accelerating or decelerating demand trends per product category.
