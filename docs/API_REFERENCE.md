# NexusAI REST API Reference

All endpoints return JSON responses with standard status codes (`200 OK`, `400 Bad Request`, `404 Not Found`, `500 Server Error`).

Base URL: `http://127.0.0.1:5000`

---

## 1. Catalog & Customer Endpoints

### `GET /api/customers`
Returns all registered customer accounts.
- **Response**: `{"status": "success", "customers": [...]}`

### `GET /api/products`
Returns all catalog products grouped by category, including price, stock, and reviews.
- **Query Params**: `category_id` (optional)
- **Response**: `{"status": "success", "categories": [...], "products": [...]}`

### `GET /api/product/<product_id>`
Returns complete product details, reviews, frequently bought together rules, and similar products.
- **Aliases**: `GET /api/products/<product_id>`
- **Response**: `{"status": "success", "product": {...}, "reviews": [...], "fbt": [...], "similar_products": [...]}`

### `GET /api/profile/<customer_id>`
Returns full customer purchase history, RFM profile, lifetime spend, and wishlist count.
- **Response**: `{"status": "success", "profile": {...}}`

### `GET /api/orders/<customer_id>`
Returns customer orders and item breakdown.
- **Response**: `{"status": "success", "orders": [...]}`

### `GET /api/home/sections`
Returns homepage featured products, top-rated products, and market-basket co-purchase bundle.
- **Response**: `{"status": "success", "sections": {...}}`

---

## 2. Cart & Wishlist Operations

### `GET /api/cart/<customer_id>`
Returns active cart items, item subtotals, and total price.
- **Response**: `{"status": "success", "items": [...], "cart_total": 129.99}`

### `POST /api/cart/add`
Adds an item to the customer's cart.
- **Payload**: `{"customer_id": "C101", "product_id": "P105", "quantity": 1}`
- **Response**: `{"status": "success", "message": "Added to cart"}`

### `POST /api/cart/update`
Updates item quantity with stock boundary validation.
- **Payload**: `{"customer_id": "C101", "product_id": "P105", "quantity": 2}`
- **Response**: `{"status": "success", "quantity": 2, "subtotal": 59.98, "cart_total": 59.98}`

### `POST /api/cart/remove`
Removes an item from cart.
- **Payload**: `{"customer_id": "C101", "product_id": "P105"}`

### `GET /api/wishlist/<customer_id>`
Returns saved wishlist products.
- **Response**: `{"status": "success", "wishlist": [...]}`

### `POST /api/wishlist/toggle`
Toggles wishlist state for a product.
- **Payload**: `{"customer_id": "C101", "product_id": "P101"}`
- **Response**: `{"status": "success", "action": "added"|"removed", "in_wishlist": true|false}`

---

## 3. Search & Real-Time Context Events

### `GET /api/search/suggestions`
Prefix and keyword search suggestions.
- **Query Params**: `q` (e.g., `q=lap`)
- **Response**: `{"status": "success", "suggestions": [...]}`

### `POST /api/search/record`
Records customer search query in `search_history`.
- **Payload**: `{"customer_id": "C101", "query": "wireless mouse"}`

### `POST /api/events/record`
Records real-time interaction in `session_events`.
- **Payload**: `{"customer_id": "C101", "product_id": "P101", "event_type": "PRODUCT_VIEW"}`

---

## 4. ACID Checkout Transaction

### `POST /api/checkout`
Executes atomic checkout transaction.
- **Payload**:
  ```json
  {
    "customer_id": "C101",
    "payment_method": "CREDIT_CARD",
    "simulate_fail": false
  }
  ```
- **Success Response (200)**:
  ```json
  {
    "status": "success",
    "result": {
      "status": "SUCCESS",
      "order_id": "ORD1A2B3C",
      "amount": 129.99,
      "total_amount": 129.99
    }
  }
  ```
- **Failure / Rollback Response (400)**:
  ```json
  {
    "status": "error",
    "result": {
      "status": "FAILED",
      "error": "SIMULATED EXCEPTION: ..."
    }
  }
  ```

---

## 5. Recommendation & Explainability (XAI) Endpoints

### `GET /api/recommendations/<customer_id>`
Returns ranked, context-aware personalized recommendations.
- **Query Params**: `top_n` (default: 4), `context_product_id` (optional)
- **Response**: `{"status": "success", "recommendations": [...]}`

### `GET /api/recommendations/audit/<customer_id>`
Returns detailed XAI provenance, candidate scoring breakdowns, and signal traces.
- **Response**: `{"status": "success", "audit": [...]}`

### `GET /api/recommendations/bundle/<product_id>`
Returns Apriori co-purchase companion product with bundle savings.
- **Response**: `{"status": "success", "bundle": {...}}`

### `GET /api/recommendations/alternatives/<product_id>`
Returns similar spec-matched in-stock alternatives.
- **Response**: `{"status": "success", "alternatives": [...]}`

### `GET /api/product/<product_id>/review-intelligence`
Returns NLP aspect themes, sentiment score, and rating mismatch warnings.
- **Response**: `{"status": "success", "intelligence": {...}}`

---

## 6. Admin Business Intelligence & Operations Endpoints

### `GET /api/admin/overview`
Headline executive KPIs and truthful historical comparisons.
- **Query Params**: `range=7d|30d|90d|all`
- **Response**: `{"status": "success", "kpis": {...}, "comparisons": {...}, "alerts": [...]}`

### `GET /api/admin/sales-analytics`
Daily timeline buckets, category shares, payment distribution, and top sellers.
- **Query Params**: `range=7d|30d|90d|all`
- **Response**: `{"status": "success", "timeline": [...], "categories": [...], "payment_methods": [...]}`

### `GET /api/admin/product-analytics`
Consolidated commercial velocity and review sentiment matrix table.
- **Query Params**: `sort_by=best_selling|highest_revenue|highest_rated|low_stock|poorly_reviewed`, `category_id`
- **Response**: `{"status": "success", "products": [...]}`

### `GET /api/admin/customer-analytics`
Phase 7 RFM customer segmentation and lifetime spend summary.
- **Response**: `{"status": "success", "segment_counts": {...}, "customers": [...]}`

### `GET /api/admin/inventory-analytics`
Stock health buckets, daily velocities, stock cover days, and restock queue.
- **Response**: `{"status": "success", "kpis": {...}, "restock_recommendations": [...]}`

### `GET /api/admin/review-analytics`
Storewide rating health, aspect themes, and complaint breakdowns.
- **Response**: `{"status": "success", "overview": {...}, "aspect_breakdown": [...]}`

### `GET /api/admin/ai-analytics`
Active Apriori rules, multi-signal hybrid weights, and companion frequencies.
- **Response**: `{"status": "success", "hybrid_weights": {...}, "top_apriori_rules": [...]}`

### `GET /api/admin/insights`
SQL-derived actionable business intelligence alerts with 1-click drilldowns.
- **Query Params**: `range=7d|30d|90d|all`
- **Response**: `{"status": "success", "insights": [...]}`

---

## 7. Database Lab & SQL Runner

### `GET /api/analytics/view/<view_name>`
Queries live rows from pre-compiled analytical database views.
- **Supported Views**: `v_market_basket`, `v_customer_purchase_summary`, `v_product_performance`, `v_frequent_product_pairs`.
- **Response**: `{"status": "success", "columns": [...], "data": [...]}`

### `POST /api/sql/execute`
Executes sandboxed read-only SQL queries (`SELECT`, `EXPLAIN QUERY PLAN`, `PRAGMA`).
- **Engine Guard**: SQLite connection opened in read-only mode (`mode=ro`). Write keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`) and multi-statement queries strictly blocked.
- **Payload**: `{"query": "EXPLAIN QUERY PLAN SELECT * FROM order_items WHERE order_id = 'ORD101';"}`
- **Response**: `{"status": "success", "columns": [...], "rows": [...], "row_count": 1}`
