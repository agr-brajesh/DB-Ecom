-- ==========================================================
-- VIEWS, INDEXES, AND TRIGGERS FOR E-COMMERCE DBMS
-- Provides analytical views for AI recommendation,
-- performance indexes, and inventory integrity triggers.
-- ==========================================================

-- ==========================================================
-- 1. PERFORMANCE INDEXES
-- Speed up frequent joins and queries used in recommendation
-- ==========================================================
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_product_rating ON reviews(product_id, rating);
CREATE INDEX IF NOT EXISTS idx_search_customer ON search_history(customer_id);
CREATE INDEX IF NOT EXISTS idx_cart_customer ON shopping_cart(customer_id);
CREATE INDEX IF NOT EXISTS idx_wishlist_customer ON wishlist(customer_id);
CREATE INDEX IF NOT EXISTS idx_session_events_customer ON session_events(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_events_product ON session_events(product_id);


-- ==========================================================
-- 2. ANALYTICAL DATABASE VIEWS
-- ==========================================================

-- View A: Market Basket View (Feeds directly into the AI Recommendation Engine)
-- Groups each completed order into a single basket of product IDs and names
CREATE VIEW IF NOT EXISTS v_market_basket AS
SELECT 
    o.order_id,
    o.customer_id,
    o.order_date,
    GROUP_CONCAT(p.product_id, ',') AS product_ids,
    GROUP_CONCAT(p.product_name, ' | ') AS product_names,
    COUNT(oi.product_id) AS basket_size,
    SUM(oi.quantity * oi.unit_price) AS order_total
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.order_status = 'COMPLETED'
GROUP BY o.order_id, o.customer_id, o.order_date
HAVING COUNT(oi.product_id) >= 1;

-- View B: Customer Purchase History Summary
-- Aggregates orders, distinct items bought, and lifetime spend per customer
CREATE VIEW IF NOT EXISTS v_customer_purchase_summary AS
SELECT 
    c.customer_id,
    c.name AS customer_name,
    c.city,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(oi.order_item_id) AS total_items_purchased,
    COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) AS lifetime_spend,
    GROUP_CONCAT(DISTINCT p.product_id) AS purchased_product_ids,
    GROUP_CONCAT(DISTINCT p.product_name) AS purchased_product_names
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'COMPLETED'
LEFT JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN products p ON oi.product_id = p.product_id
GROUP BY c.customer_id, c.name, c.city;

-- View C: Product Performance & Review Metrics
-- Calculates total units sold, gross revenue, review count, and average rating
CREATE VIEW IF NOT EXISTS v_product_performance AS
SELECT 
    p.product_id,
    p.product_name,
    cat.category_name,
    p.price,
    p.stock_quantity,
    COALESCE(SUM(oi.quantity), 0) AS units_sold,
    COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) AS total_revenue,
    COUNT(DISTINCT r.review_id) AS review_count,
    ROUND(AVG(r.rating), 2) AS avg_rating
FROM products p
JOIN categories cat ON p.category_id = cat.category_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN reviews r ON p.product_id = r.product_id
GROUP BY p.product_id, p.product_name, cat.category_name, p.price, p.stock_quantity;

-- View D: Frequent 2-Item Co-occurrence (SQL-based Basket Analysis)
-- Demonstrates SQL self-join logic to find products frequently purchased together
CREATE VIEW IF NOT EXISTS v_frequent_product_pairs AS
SELECT 
    oi1.product_id AS product_a_id,
    p1.product_name AS product_a_name,
    oi2.product_id AS product_b_id,
    p2.product_name AS product_b_name,
    COUNT(*) AS co_purchase_count
FROM order_items oi1
JOIN order_items oi2 ON oi1.order_id = oi2.order_id AND oi1.product_id < oi2.product_id
JOIN products p1 ON oi1.product_id = p1.product_id
JOIN products p2 ON oi2.product_id = p2.product_id
GROUP BY oi1.product_id, p1.product_name, oi2.product_id, p2.product_name
HAVING COUNT(*) >= 2
ORDER BY co_purchase_count DESC;

-- ==========================================================
-- 3. INVENTORY INTEGRITY TRIGGERS
-- ==========================================================

-- Trigger 1: Decrement stock quantity after an item is ordered
CREATE TRIGGER IF NOT EXISTS trg_decrement_product_stock
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
    UPDATE products
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE product_id = NEW.product_id;
END;

-- Trigger 2: Prevent inserting an order item if stock is insufficient
CREATE TRIGGER IF NOT EXISTS trg_validate_stock_before_order
BEFORE INSERT ON order_items
FOR EACH ROW
WHEN (SELECT stock_quantity FROM products WHERE product_id = NEW.product_id) < NEW.quantity
BEGIN
    SELECT RAISE(ABORT, 'Insufficient stock available for this product.');
END;
