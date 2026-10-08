# NexusAI Database Management System (DBMS) Features & Specification

## 1. Relational Schema Architecture

NexusAI uses a database-first design implemented in SQLite, adhering strictly to Third Normal Form (3NF) and Boyce-Codd Normal Form (BCNF).

### Entity-Relationship Overview (11 Normalized Tables)

```
[categories] 1 ──── ∞ [products] 1 ──── ∞ [reviews] ∞ ──── 1 [customers]
                           │                                      │
                           │ 1                                    │ 1
                           │                                      │
                           ▼ ∞                                    ▼ ∞
                     [order_items] ∞ ──── 1 [orders] 1 ──── 1 [payments]
                           ▲
                           │ (M:N Bridge)
                           ▼
                    [shopping_cart]  [wishlist]  [search_history]  [session_events]
```

---

## 2. Relational Tables Specification

| Table | Primary Key | Foreign Keys | Domain Constraints / Checks |
|---|---|---|---|
| `categories` | `category_id` | - | `category_name UNIQUE NOT NULL` |
| `products` | `product_id` | `category_id` $\to$ `categories(category_id)` [RESTRICT] | `price >= 0`, `stock_quantity >= 0` |
| `customers` | `customer_id` | - | `email UNIQUE NOT NULL` |
| `orders` | `order_id` | `customer_id` $\to$ `customers(customer_id)` [CASCADE] | `total_amount >= 0`, `order_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'CANCELLED')` |
| `order_items` | `order_item_id` | `order_id` [CASCADE], `product_id` [RESTRICT] | `quantity > 0`, `unit_price >= 0`, `UNIQUE(order_id, product_id)` |
| `payments` | `payment_id` | `order_id` [CASCADE] | `amount >= 0`, `payment_method IN ('CREDIT_CARD', 'DEBIT_CARD', 'UPI', 'NET_BANKING', 'CASH_ON_DELIVERY')`, `payment_status IN ('SUCCESS', 'PENDING', 'FAILED')` |
| `shopping_cart`| `cart_id` | `customer_id` [CASCADE], `product_id` [CASCADE] | `quantity > 0`, `UNIQUE(customer_id, product_id)` |
| `reviews` | `review_id` | `customer_id` [CASCADE], `product_id` [CASCADE] | `rating BETWEEN 1 AND 5`, `UNIQUE(customer_id, product_id)` |
| `search_history`|`search_id` | `customer_id` [CASCADE] | `search_query NOT NULL` |
| `wishlist` | `wishlist_id` | `customer_id` [CASCADE], `product_id` [CASCADE] | `UNIQUE(customer_id, product_id)` |
| `session_events`|`event_id` | `customer_id` [CASCADE], `product_id` [CASCADE] | `event_type IN ('PRODUCT_VIEW', 'SEARCH', 'ADD_TO_CART', 'PURCHASE', 'WISHLIST_ADD')` |

---

## 3. Academic Proof of Normalization (3NF & BCNF)

### 1NF (First Normal Form)
- All attribute domains contain only atomic, indivisible values.
- No repeating groups or array columns (e.g. multiple items in an order are decomposed into individual rows in `order_items`).

### 2NF (Second Normal Form)
- In 1NF and every non-prime attribute is fully functionally dependent on the primary key.
- For tables with composite unique keys (`order_items(order_id, product_id)`):
  - `quantity` depends on both `(order_id, product_id)`.
  - `unit_price` captures the historical price snapshot at purchase time for that specific order-item pair.
  - Product details (`product_name`, `brand`, `category_id`) reside exclusively in `products`, avoiding partial functional dependency.

### 3NF (Third Normal Form)
- In 2NF and no transitive functional dependencies ($X \to Y \to Z$) exist.
- In `products`: `product_id` $\to$ `category_id` $\to$ `category_name`. To eliminate transitive dependency, category attributes are extracted into the `categories` relation.
- In `orders`: `order_id` $\to$ `customer_id` $\to$ `customer_name`. Customer details reside solely in `customers`.

### BCNF (Boyce-Codd Normal Form)
- A relation is in BCNF if for every non-trivial functional dependency $X \to Y$, $X$ is a superkey.
- In all 11 tables, every functional determinant is an explicit candidate or primary key.

---

## 4. Database Triggers (Automated Integrity)

Implemented in [`database/views_triggers.sql`](../database/views_triggers.sql):

### Trigger 1: Automatic Inventory Decrement
```sql
CREATE TRIGGER IF NOT EXISTS trg_decrement_product_stock
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
    UPDATE products
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE product_id = NEW.product_id;
END;
```

### Trigger 2: Overdraft Prevention Guard
```sql
CREATE TRIGGER IF NOT EXISTS trg_validate_stock_before_order
BEFORE INSERT ON order_items
FOR EACH ROW
WHEN (SELECT stock_quantity FROM products WHERE product_id = NEW.product_id) < NEW.quantity
BEGIN
    SELECT RAISE(ABORT, 'Insufficient stock available for this product.');
END;
```

---

## 5. Analytical Views

NexusAI uses database views to decouple analytical queries from application logic:

1. **`v_market_basket`**:
   Aggregates completed orders into concatenated strings of product IDs and titles, feeding the Apriori association engine.
2. **`v_customer_purchase_summary`**:
   Computes customer order count, items purchased, and lifetime spend via indexed joins.
3. **`v_product_performance`**:
   Computes gross revenue, units sold, review count, and average customer rating per SKU.
4. **`v_frequent_product_pairs`**:
   Pure-SQL self-join on `order_items` discovering co-occurrence counts without external libraries.

---

## 6. Performance Indexes & EXPLAIN QUERY PLAN

### Active Indexes (11 B-Tree Indexes):
- `idx_products_category`: Optimizes category filter lookups.
- `idx_orders_customer`: Speeds customer order history aggregation.
- `idx_order_items_product`: Accelerates co-purchase self-joins.
- `idx_order_items_order`: Optimizes basket joins on order ID.
- `idx_orders_status_date`: Speeds date-range analytical window queries.
- `idx_reviews_product_rating`: Optimizes average rating and review aggregation.
- `idx_search_customer`: Optimizes search intent lookup.
- `idx_cart_customer`: Speeds shopping cart queries.
- `idx_wishlist_customer`: Optimizes customer wishlist lookups.
- `idx_session_events_customer`: Speeds recent context retrieval (`created_at DESC`).
- `idx_session_events_product`: Accelerates product view aggregation.

### EXPLAIN QUERY PLAN Verification:
```sql
EXPLAIN QUERY PLAN SELECT * FROM order_items WHERE order_id = 'ORD101';
-- Result: SEARCH order_items USING INDEX idx_order_items_order (order_id=?)
```

---

## 7. ACID Transactions & Atomicity Proof

Checkout transactions are managed by [`database/transactions.py`](../database/transactions.py):
- **Atomicity**: The entire order, order items, trigger-driven stock updates, payment records, and cart clearing either commit together or roll back cleanly.
- **Consistency**: Relational invariants (`stock_quantity >= 0`, `price >= 0`) are guaranteed at engine level.
- **Isolation**: Serialized transaction blocks prevent race conditions on concurrent checkout attempts.
- **Durability**: Upon `COMMIT`, SQLite flushes pages to persistent storage.
