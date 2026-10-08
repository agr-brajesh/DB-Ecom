-- ====================================================================
-- NexusAI Data Integrity Repair Script: Reconcile Order Totals & Payments
-- ====================================================================
-- Recalculates orders.total_amount to exactly equal the sum of line items:
-- total_amount = SUM(quantity * unit_price)
-- Then reconciles payments.amount to match orders.total_amount.

-- 1. Update orders.total_amount from order_items
UPDATE orders
SET total_amount = ROUND((
    SELECT SUM(oi.quantity * oi.unit_price)
    FROM order_items oi
    WHERE oi.order_id = orders.order_id
), 2)
WHERE order_id IN (
    SELECT DISTINCT order_id FROM order_items
);

-- 2. Update payments.amount to match orders.total_amount
UPDATE payments
SET amount = (
    SELECT o.total_amount
    FROM orders o
    WHERE o.order_id = payments.order_id
)
WHERE order_id IN (
    SELECT order_id FROM orders
);
