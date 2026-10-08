"""
Phase 7: Business Intelligence Engine for NexusAI E-Commerce Platform
Provides deterministic, explainable analytics for:
1. Customer Intelligence & RFM Segmentation
2. Inventory Intelligence & Velocity Analysis
3. Product Performance & Rank Matrix
4. Actionable Business Insights derived from actual database transactions
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


class BusinessIntelligenceEngine:
    """
    Pure Python & SQLite Business Intelligence Engine.
    Computes explainable RFM customer segmentation, inventory sales velocities,
    days-of-stock-coverage forecasts, product performance matrices, and live business insights.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Returns SQLite database connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_dataset_reference_date(self, conn: sqlite3.Connection) -> Tuple[datetime, int]:
        """
        Determines the dataset's latest transaction date and active time span in days.
        Uses this reference date to evaluate recency deterministically.
        """
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MIN(order_date), MAX(order_date) 
            FROM orders 
            WHERE order_status = 'COMPLETED';
        """)
        row = cursor.fetchone()
        if row and row[0] and row[1]:
            min_d = datetime.fromisoformat(row[0])
            max_d = datetime.fromisoformat(row[1])
            span_days = max((max_d - min_d).days, 1)
            return max_d, span_days
        # Fallback if no completed orders exist
        now = datetime.now()
        return now, 1

    # =========================================================================
    # 1. CUSTOMER INTELLIGENCE & RFM SEGMENTATION
    # =========================================================================

    def compute_rfm_scores(self, recency_days: Optional[int], frequency: int, monetary: float) -> Dict[str, Any]:
        """
        Calculates normalized RFM scores on a 1 to 5 scale.
        - Recency Score (R): 5 = very recent, 1 = long dormant / no orders
        - Frequency Score (F): 5 = high repeat buyer (20+), 1 = single/no purchase
        - Monetary Score (M): 5 = top spend ($13k+), 1 = lowest spend (<$1k)
        """
        # Recency score (lower days -> higher score)
        if recency_days is None:
            r_score = 1
        elif recency_days <= 14:
            r_score = 5
        elif recency_days <= 35:
            r_score = 4
        elif recency_days <= 60:
            r_score = 3
        elif recency_days <= 90:
            r_score = 2
        else:
            r_score = 1

        # Frequency score (higher orders -> higher score)
        if frequency >= 20:
            f_score = 5
        elif frequency >= 12:
            f_score = 4
        elif frequency >= 6:
            f_score = 3
        elif frequency >= 2:
            f_score = 2
        else:
            f_score = 1

        # Monetary score (higher spend -> higher score)
        if monetary >= 13000.0:
            m_score = 5
        elif monetary >= 9000.0:
            m_score = 4
        elif monetary >= 4000.0:
            m_score = 3
        elif monetary >= 1000.0:
            m_score = 2
        else:
            m_score = 1

        # Composite RFM Index (weighted: R: 30%, F: 35%, M: 35%)
        composite = round((r_score * 0.30) + (f_score * 0.35) + (m_score * 0.35), 2)

        return {
            "recency_score": r_score,
            "frequency_score": f_score,
            "monetary_score": m_score,
            "composite_score": composite,
            "rfm_tier": f"R{r_score}F{f_score}M{m_score}"
        }

    def classify_customer(
        self,
        frequency: int,
        monetary: float,
        recency_days: Optional[int],
        account_age_days: Optional[int] = None
    ) -> Tuple[str, List[str], str]:
        """
        Classifies a customer into one of 6 deterministic, explainable segments:
        - HIGH VALUE
        - FREQUENT SHOPPER
        - ACTIVE SHOPPER
        - OCCASIONAL SHOPPER
        - AT-RISK / INACTIVE
        - NEW CUSTOMER

        Returns: (segment_name, [reasons/proofs], suggested_action)
        """
        # 1. Zero order customers or very recently registered with <= 1 order
        if frequency == 0:
            reasons = [
                "Zero completed transactions recorded to date",
                "New account profile pending initial purchase activation",
                "Requires welcome engagement and catalog onboarding"
            ]
            action = "Activation Offer: Trigger introductory 15% discount for first checkout."
            return "NEW CUSTOMER", reasons, action

        # 2. At-risk / Inactive: Long dormancy (> 75 days) with low-to-moderate historical spend
        if recency_days is not None and recency_days > 75 and monetary < 3500:
            reasons = [
                f"Dormant account: {recency_days} days elapsed since last purchase",
                f"Low lifetime order volume ({frequency} total order(s))",
                f"Modest cumulative spend (${monetary:,.2f}) at risk of churn"
            ]
            action = "Win-Back Campaign: Dispatch targeted re-engagement email with category incentives."
            return "AT-RISK / INACTIVE", reasons, action

        # 3. High Value: Substantial gross spend ($12,000+ or $9,000+ with 10+ orders)
        if monetary >= 12000.0 or (monetary >= 9000.0 and frequency >= 10):
            avg_order = round(monetary / frequency, 2)
            reasons = [
                f"Top-tier lifetime spend (${monetary:,.2f})",
                f"High order frequency ({frequency} completed orders)",
                f"Substantial average order value of ${avg_order:,.2f}"
            ]
            action = "VIP Concierge: Enroll in exclusive rewards tier with dedicated support and early access."
            return "HIGH VALUE", reasons, action

        # 4. Frequent Shopper: Consistent repeat ordering habit (12+ orders)
        if frequency >= 12:
            avg_order = round(monetary / frequency, 2)
            rec_str = f"{recency_days} days ago" if recency_days is not None else "N/A"
            reasons = [
                f"Strong repeat purchase habit ({frequency} completed orders)",
                f"Cumulative spend of ${monetary:,.2f} (Avg: ${avg_order:,.2f}/order)",
                f"Recent activity observed ({rec_str})"
            ]
            action = "Loyalty Habit Loop: Offer bundled replenishment rewards to sustain high transaction cadence."
            return "FREQUENT SHOPPER", reasons, action

        # 5. Active Shopper: Purchased recently (<= 35 days) with multiple orders (frequency >= 2)
        if recency_days is not None and recency_days <= 35 and frequency >= 2:
            reasons = [
                f"Recent store activity ({recency_days} day(s) since last completed order)",
                f"Engaged customer profile ({frequency} order(s), ${monetary:,.2f} lifetime spend)",
                "Active presence across product catalog"
            ]
            action = "Cross-Sell Acceleration: Recommend compatible ecosystem accessories based on recent purchases."
            return "ACTIVE SHOPPER", reasons, action

        # 6. Occasional Shopper: Moderate frequency (2-8 orders) with moderate elapsed recency
        if frequency >= 2:
            avg_order = round(monetary / frequency, 2)
            reasons = [
                f"Intermittent shopping pattern ({frequency} completed orders)",
                f"Moderate lifetime spend (${monetary:,.2f}, Avg: ${avg_order:,.2f}/order)",
                f"Last active {recency_days} days ago"
            ]
            action = "Re-Engagement Push: Target seasonal promotional banners and new arrivals in preferred domain."
            return "OCCASIONAL SHOPPER", reasons, action

        # 7. Fallback: New customer with single order
        reasons = [
            f"Early customer lifecycle stage ({frequency} order placed)",
            f"Initial spend of ${monetary:,.2f}",
            "Nurturing stage for repeat order conversion"
        ]
        action = "Post-Purchase Nurturing: Deliver product guides and complementary accessory suggestions."
        return "NEW CUSTOMER", reasons, action

    def get_customer_segments_summary(self) -> Dict[str, Any]:
        """
        Retrieves all customers, calculates RFM metrics, segment classifications,
        segment distributions, and portfolio KPIs.
        """
        conn = self._get_connection()
        ref_date, _ = self._get_dataset_reference_date(conn)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                c.customer_id,
                c.name,
                c.email,
                c.city,
                c.created_at,
                COUNT(DISTINCT o.order_id) AS total_orders,
                COALESCE(SUM(oi.quantity * oi.unit_price), 0.0) AS lifetime_spend,
                MAX(o.order_date) AS last_order_date,
                MIN(o.order_date) AS first_order_date
            FROM customers c
            LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'COMPLETED'
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            GROUP BY c.customer_id, c.name, c.email, c.city, c.created_at
            ORDER BY lifetime_spend DESC;
        """)
        rows = cursor.fetchall()

        customers_list = []
        segment_counts = {
            "HIGH VALUE": 0,
            "FREQUENT SHOPPER": 0,
            "ACTIVE SHOPPER": 0,
            "OCCASIONAL SHOPPER": 0,
            "NEW CUSTOMER": 0,
            "AT-RISK / INACTIVE": 0
        }
        segment_spend = {k: 0.0 for k in segment_counts}
        segment_orders = {k: 0 for k in segment_counts}

        total_customers = len(rows)
        total_spend = 0.0
        total_orders_store = 0

        for r in rows:
            cid = r["customer_id"]
            name = r["name"]
            email = r["email"]
            city = r["city"]
            reg_date = r["created_at"]
            orders_cnt = r["total_orders"]
            spend = round(float(r["lifetime_spend"]), 2)
            last_date_str = r["last_order_date"]
            first_date_str = r["first_order_date"]

            if last_date_str:
                last_dt = datetime.fromisoformat(last_date_str)
                recency_days = max((ref_date - last_dt).days, 0)
            else:
                recency_days = None

            aov = round(spend / orders_cnt, 2) if orders_cnt > 0 else 0.0
            rfm = self.compute_rfm_scores(recency_days, orders_cnt, spend)
            segment, reasons, action = self.classify_customer(orders_cnt, spend, recency_days)

            segment_counts[segment] = segment_counts.get(segment, 0) + 1
            segment_spend[segment] = segment_spend.get(segment, 0.0) + spend
            segment_orders[segment] = segment_orders.get(segment, 0) + orders_cnt

            total_spend += spend
            total_orders_store += orders_cnt

            customers_list.append({
                "customer_id": cid,
                "name": name,
                "email": email,
                "city": city,
                "registered_at": reg_date,
                "total_orders": orders_cnt,
                "lifetime_spend": spend,
                "aov": aov,
                "last_order_date": last_date_str,
                "first_order_date": first_date_str,
                "recency_days": recency_days,
                "rfm_scores": rfm,
                "segment": segment,
                "reasons": reasons,
                "suggested_action": action
            })

        conn.close()

        # Build structured segment breakdown
        segment_breakdown = []
        badge_map = {
            "HIGH VALUE": "badge-high-value",
            "FREQUENT SHOPPER": "badge-frequent",
            "ACTIVE SHOPPER": "badge-active",
            "OCCASIONAL SHOPPER": "badge-occasional",
            "NEW CUSTOMER": "badge-new",
            "AT-RISK / INACTIVE": "badge-inactive"
        }

        for seg_name, count in segment_counts.items():
            pct = round((count / total_customers * 100), 1) if total_customers > 0 else 0.0
            spend_agg = segment_spend[seg_name]
            orders_agg = segment_orders[seg_name]
            avg_cust_spend = round(spend_agg / count, 2) if count > 0 else 0.0
            avg_cust_orders = round(orders_agg / count, 1) if count > 0 else 0.0
            seg_aov = round(spend_agg / orders_agg, 2) if orders_agg > 0 else 0.0

            segment_breakdown.append({
                "segment": seg_name,
                "count": count,
                "percentage": pct,
                "total_spend": round(spend_agg, 2),
                "avg_spend": avg_cust_spend,
                "avg_orders": avg_cust_orders,
                "aov": seg_aov,
                "badge_class": badge_map.get(seg_name, "badge-default")
            })

        overall_metrics = {
            "total_customers": total_customers,
            "active_shoppers": segment_counts["ACTIVE SHOPPER"] + segment_counts["FREQUENT SHOPPER"] + segment_counts["HIGH VALUE"],
            "total_revenue": round(total_spend, 2),
            "avg_spend_per_customer": round(total_spend / total_customers, 2) if total_customers > 0 else 0.0,
            "overall_aov": round(total_spend / total_orders_store, 2) if total_orders_store > 0 else 0.0,
            "avg_order_frequency": round(total_orders_store / total_customers, 1) if total_customers > 0 else 0.0
        }

        return {
            "status": "success",
            "as_of_reference_date": ref_date.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_metrics": overall_metrics,
            "segment_counts": segment_counts,
            "segment_breakdown": segment_breakdown,
            "customers": customers_list
        }

    def get_customer_insights(self, customer_id: str) -> Dict[str, Any]:
        """
        Retrieves in-depth business intelligence profile for a specific customer:
        - Lifetime metrics (orders, spend, AOV, span, recency)
        - Explainable segment classification with evidence proofs
        - Preferred categories and top products purchased
        - Cart & wishlist indicators
        - Tailored business action recommendation
        """
        conn = self._get_connection()
        ref_date, _ = self._get_dataset_reference_date(conn)
        cursor = conn.cursor()

        # Customer basics & lifetime aggregates
        cursor.execute("""
            SELECT 
                c.customer_id, c.name, c.email, c.phone, c.city, c.created_at,
                COUNT(DISTINCT o.order_id) AS total_orders,
                COALESCE(SUM(oi.quantity * oi.unit_price), 0.0) AS lifetime_spend,
                MAX(o.order_date) AS last_order_date,
                MIN(o.order_date) AS first_order_date
            FROM customers c
            LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'COMPLETED'
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE c.customer_id = ?
            GROUP BY c.customer_id, c.name, c.email, c.phone, c.city, c.created_at;
        """, (customer_id,))
        cust = cursor.fetchone()

        if not cust:
            conn.close()
            return {"status": "error", "message": f"Customer '{customer_id}' not found."}

        total_orders = cust["total_orders"]
        lifetime_spend = round(float(cust["lifetime_spend"]), 2)
        last_date_str = cust["last_order_date"]
        first_date_str = cust["first_order_date"]

        if last_date_str:
            last_dt = datetime.fromisoformat(last_date_str)
            recency_days = max((ref_date - last_dt).days, 0)
        else:
            recency_days = None

        aov = round(lifetime_spend / total_orders, 2) if total_orders > 0 else 0.0
        rfm_scores = self.compute_rfm_scores(recency_days, total_orders, lifetime_spend)
        segment, reasons, suggested_action = self.classify_customer(total_orders, lifetime_spend, recency_days)

        # Top product categories purchased
        cursor.execute("""
            SELECT 
                cat.category_id,
                cat.category_name,
                COUNT(oi.order_item_id) AS items_purchased,
                ROUND(SUM(oi.quantity * oi.unit_price), 2) AS category_spend
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            WHERE o.customer_id = ? AND o.order_status = 'COMPLETED'
            GROUP BY cat.category_id, cat.category_name
            ORDER BY category_spend DESC LIMIT 4;
        """, (customer_id,))
        top_categories = [{
            "category_id": r["category_id"],
            "category_name": r["category_name"],
            "items_purchased": r["items_purchased"],
            "category_spend": r["category_spend"]
        } for r in cursor.fetchall()]

        # Top individual products purchased
        cursor.execute("""
            SELECT 
                p.product_id,
                p.product_name,
                p.price,
                cat.category_name,
                SUM(oi.quantity) AS total_quantity,
                ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_spend
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            WHERE o.customer_id = ? AND o.order_status = 'COMPLETED'
            GROUP BY p.product_id, p.product_name, p.price, cat.category_name
            ORDER BY total_quantity DESC, total_spend DESC LIMIT 5;
        """, (customer_id,))
        top_products = [{
            "product_id": r["product_id"],
            "product_name": r["product_name"],
            "price": r["price"],
            "category_name": r["category_name"],
            "total_quantity": r["total_quantity"],
            "total_spend": r["total_spend"]
        } for r in cursor.fetchall()]

        # Active engagement indicators (cart & wishlist)
        cursor.execute("SELECT COUNT(*) FROM shopping_cart WHERE customer_id = ?;", (customer_id,))
        cart_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM wishlist WHERE customer_id = ?;", (customer_id,))
        wishlist_count = cursor.fetchone()[0]

        # Recent 3 orders
        cursor.execute("""
            SELECT o.order_id, o.order_date, o.total_amount, o.order_status,
                   COALESCE(p.payment_method, 'CREDIT_CARD') as payment_method
            FROM orders o
            LEFT JOIN payments p ON o.order_id = p.order_id
            WHERE o.customer_id = ?
            ORDER BY o.order_date DESC LIMIT 3;
        """, (customer_id,))
        recent_orders = [{
            "order_id": r["order_id"],
            "order_date": r["order_date"],
            "total_amount": r["total_amount"],
            "order_status": r["order_status"],
            "payment_method": r["payment_method"]
        } for r in cursor.fetchall()]

        conn.close()

        return {
            "status": "success",
            "customer": {
                "customer_id": cust["customer_id"],
                "name": cust["name"],
                "email": cust["email"],
                "phone": cust["phone"],
                "city": cust["city"],
                "registered_at": cust["created_at"],
                "total_orders": total_orders,
                "lifetime_spend": lifetime_spend,
                "aov": aov,
                "first_order_date": first_date_str,
                "last_order_date": last_date_str,
                "recency_days": recency_days,
                "rfm_scores": rfm_scores,
                "segment": segment,
                "reasons": reasons,
                "suggested_action": suggested_action,
                "cart_items_count": cart_count,
                "wishlist_items_count": wishlist_count,
                "top_categories": top_categories,
                "top_products": top_products,
                "recent_orders": recent_orders
            }
        }

    # =========================================================================
    # 2. INVENTORY INTELLIGENCE & DEMAND INDICATORS
    # =========================================================================

    def classify_inventory_risk(
        self,
        stock_quantity: int,
        avg_daily_sales: float,
        cover_days: Optional[float]
    ) -> Tuple[str, str, str, int]:
        """
        Evaluates deterministic inventory risk states and replenishment actions:
        - OUT OF STOCK: stock_quantity == 0
        - CRITICAL: stock cover <= 150 days (or stock <= 50 with steady velocity > 0.25)
        - LOW STOCK: stock cover <= 300 days (or stock <= 100 with steady velocity > 0.20)
        - HEALTHY: balanced cover
        - OVERSTOCKED: stock cover > 750 days and stock >= 200 (or stock >= 350 with velocity < 0.35)
        - INSUFFICIENT HISTORY: zero sales recorded

        Returns: (risk_state, risk_label, suggested_action, recommended_reorder_qty)
        """
        if stock_quantity == 0:
            risk = "OUT OF STOCK"
            label = "🚨 OUT OF STOCK"
            reorder = max(50, round(avg_daily_sales * 45)) if avg_daily_sales > 0 else 50
            action = f"Immediate Replenishment: Reorder ~{reorder} units immediately. Product is unavailable to customers."
            return risk, label, action, reorder

        if cover_days is None or avg_daily_sales <= 0:
            risk = "INSUFFICIENT HISTORY"
            label = "ℹ INSUFFICIENT HISTORY"
            action = "Monitor Demand: Zero sales velocity recorded. Maintain current baseline inventory."
            return risk, label, action, 0

        # High risk / Low coverage
        if cover_days <= 150.0 or (stock_quantity <= 50 and avg_daily_sales >= 0.25):
            risk = "CRITICAL"
            label = "⚠ CRITICAL STOCK"
            reorder = max(30, round(avg_daily_sales * 60 - stock_quantity))
            action = f"Expedite Reorder: Estimated stock cover is ~{cover_days:.1f} days. Increase inventory priority and reorder ~{reorder} units."
            return risk, label, action, reorder

        if cover_days <= 300.0 or (stock_quantity <= 100 and avg_daily_sales >= 0.20):
            risk = "LOW STOCK"
            label = "⚠ RESTOCK SOON"
            reorder = max(25, round(avg_daily_sales * 45 - stock_quantity))
            action = f"Plan Replenishment: Stock cover is ~{cover_days:.1f} days. Queue replenishment of ~{reorder} units with supplier."
            return risk, label, action, reorder

        # Excess / Overstocked capital
        if (cover_days > 750.0 and stock_quantity >= 200) or (stock_quantity >= 350 and avg_daily_sales < 0.35):
            risk = "OVERSTOCKED"
            label = "📉 OVERSTOCKED"
            action = f"Excess Capital Allocation: High stock cover (~{cover_days:.1f} days). Recommend promotional bundling or homepage feature to liquidate surplus."
            return risk, label, action, 0

        # Normal healthy inventory
        risk = "HEALTHY"
        label = "✓ HEALTHY"
        action = f"Balanced Supply: Stock coverage (~{cover_days:.1f} days) is sufficient for normal customer demand."
        return risk, label, action, 0

    def get_inventory_intelligence(self, recent_window_days: int = 30) -> Dict[str, Any]:
        """
        Computes storewide inventory demand indicators:
        - Current stock
        - Units sold overall and in recent window
        - Average daily sales velocity (units/day)
        - Estimated days of stock coverage remaining
        - Risk classifications & prioritized restock recommendations
        """
        conn = self._get_connection()
        ref_date, active_span_days = self._get_dataset_reference_date(conn)
        cursor = conn.cursor()

        # Query all products with aggregated lifetime sales and recent window sales
        cursor.execute(f"""
            SELECT 
                p.product_id,
                p.product_name,
                p.brand,
                p.price,
                p.stock_quantity,
                cat.category_id,
                cat.category_name,
                COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
                COALESCE(SUM(oi.quantity * oi.unit_price), 0.0) AS total_revenue,
                COALESCE(SUM(CASE WHEN o.order_date >= datetime((SELECT MAX(order_date) FROM orders WHERE order_status = 'COMPLETED'), '-{recent_window_days} days') THEN oi.quantity ELSE 0 END), 0) AS recent_units_sold,
                ROUND(AVG(r.rating), 2) AS avg_rating,
                COUNT(DISTINCT r.review_id) AS review_count
            FROM products p
            JOIN categories cat ON p.category_id = cat.category_id
            LEFT JOIN order_items oi ON p.product_id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.order_id AND o.order_status = 'COMPLETED'
            LEFT JOIN reviews r ON p.product_id = r.product_id
            GROUP BY p.product_id, p.product_name, p.brand, p.price, p.stock_quantity, cat.category_id, cat.category_name
            ORDER BY p.product_id ASC;
        """)
        rows = cursor.fetchall()
        conn.close()

        inventory_matrix = []
        restock_recommendations = []

        risk_counts = {
            "OUT OF STOCK": 0,
            "CRITICAL": 0,
            "LOW STOCK": 0,
            "HEALTHY": 0,
            "OVERSTOCKED": 0,
            "INSUFFICIENT HISTORY": 0
        }

        total_skus = len(rows)
        total_stock_units = 0
        total_inventory_valuation = 0.0

        for r in rows:
            pid = r["product_id"]
            name = r["product_name"]
            brand = r["brand"]
            price = float(r["price"])
            stock = int(r["stock_quantity"])
            cat_id = r["category_id"]
            cat_name = r["category_name"]
            units_sold = int(r["total_units_sold"])
            revenue = round(float(r["total_revenue"]), 2)
            recent_sold = int(r["recent_units_sold"])
            avg_rating = float(r["avg_rating"]) if r["avg_rating"] is not None else 4.5
            review_count = int(r["review_count"])

            total_stock_units += stock
            total_inventory_valuation += round(stock * price, 2)

            # Sales velocity calculation (units per day)
            avg_daily_sales = round(units_sold / active_span_days, 2) if active_span_days > 0 else 0.0
            recent_daily_sales = round(recent_sold / recent_window_days, 2) if recent_window_days > 0 else 0.0

            # Stock coverage calculation (days remaining)
            if stock == 0:
                cover_days = 0.0
                cover_text = "Out of stock (0 days)"
            elif avg_daily_sales > 0:
                cover_days = round(stock / avg_daily_sales, 1)
                cover_text = f"Estimated stock-out in ~{cover_days:.0f} days"
            else:
                cover_days = None
                cover_text = "No sales velocity recorded"

            risk, risk_label, action, reorder_qty = self.classify_inventory_risk(stock, avg_daily_sales, cover_days)
            risk_counts[risk] = risk_counts.get(risk, 0) + 1

            item_data = {
                "product_id": pid,
                "product_name": name,
                "brand": brand,
                "category_id": cat_id,
                "category_name": cat_name,
                "price": price,
                "stock_quantity": stock,
                "units_sold": units_sold,
                "recent_units_sold": recent_sold,
                "revenue": revenue,
                "avg_daily_sales": avg_daily_sales,
                "recent_daily_sales": recent_daily_sales,
                "estimated_stock_cover_days": cover_days,
                "stock_cover_text": cover_text,
                "risk_state": risk,
                "risk_label": risk_label,
                "suggested_action": action,
                "reorder_quantity": reorder_qty,
                "avg_rating": avg_rating,
                "review_count": review_count,
                "inventory_value": round(stock * price, 2)
            }
            inventory_matrix.append(item_data)

            # Restock recommendation list (prioritize Critical, Low Stock, Out of stock)
            if risk in ["OUT OF STOCK", "CRITICAL", "LOW STOCK"]:
                priority_weight = 1 if risk == "OUT OF STOCK" else (2 if risk == "CRITICAL" else 3)
                restock_recommendations.append({
                    **item_data,
                    "priority_weight": priority_weight
                })

        # Sort restock recommendations by urgency
        restock_recommendations.sort(key=lambda x: (x["priority_weight"], x["estimated_stock_cover_days"] if x["estimated_stock_cover_days"] is not None else 9999))

        return {
            "status": "success",
            "active_span_days": active_span_days,
            "recent_window_days": recent_window_days,
            "kpis": {
                "total_skus": total_skus,
                "total_stock_units": total_stock_units,
                "inventory_valuation": round(total_inventory_valuation, 2),
                "out_of_stock_count": risk_counts["OUT OF STOCK"],
                "critical_count": risk_counts["CRITICAL"],
                "low_stock_count": risk_counts["LOW STOCK"],
                "healthy_count": risk_counts["HEALTHY"],
                "overstocked_count": risk_counts["OVERSTOCKED"],
                "insufficient_history_count": risk_counts["INSUFFICIENT HISTORY"]
            },
            "risk_counts": risk_counts,
            "restock_recommendations": restock_recommendations,
            "inventory_matrix": inventory_matrix
        }

    # =========================================================================
    # 3. PRODUCT PERFORMANCE & RANKING INTELLIGENCE
    # =========================================================================

    def get_product_intelligence(self) -> Dict[str, Any]:
        """
        Combines v_product_performance, inventory risk, and co-purchase affinity
        to expose comprehensive product intelligence ranks and commercial health.
        """
        inv_data = self.get_inventory_intelligence()
        matrix = inv_data["inventory_matrix"]

        # Sort matrix by total revenue descending to assign performance ranks
        sorted_by_revenue = sorted(matrix, key=lambda x: x["revenue"], reverse=True)
        for idx, item in enumerate(sorted_by_revenue):
            item["revenue_rank"] = idx + 1

        # Sort by units sold descending for volume ranks
        sorted_by_units = sorted(matrix, key=lambda x: x["units_sold"], reverse=True)
        for idx, item in enumerate(sorted_by_units):
            item["volume_rank"] = idx + 1

        # Fetch top companion pairs for each product
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_a_id, product_a_name, product_b_id, product_b_name, co_purchase_count FROM v_frequent_product_pairs;")
        pair_rows = cursor.fetchall()
        conn.close()

        pair_map = {}
        for r in pair_rows:
            pa, pan, pb, pbn, cnt = r[0], r[1], r[2], r[3], r[4]
            if pa not in pair_map:
                pair_map[pa] = {"companion_id": pb, "companion_name": pbn, "co_purchases": cnt}
            if pb not in pair_map:
                pair_map[pb] = {"companion_id": pa, "companion_name": pan, "co_purchases": cnt}

        for item in matrix:
            pid = item["product_id"]
            item["top_companion"] = pair_map.get(pid, None)

        return {
            "status": "success",
            "total_products": len(matrix),
            "products": matrix
        }

    # =========================================================================
    # 4. ACTIONABLE BUSINESS INSIGHTS (AI INSIGHTS)
    # =========================================================================

    def get_ai_insights(self) -> Dict[str, Any]:
        """
        Generates concise, actionable business intelligence insights strictly derived
        from real database metrics across customers, sales, inventory, and product categories.
        No fabricated metrics or hallucinated numbers.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        ref_date, span_days = self._get_dataset_reference_date(conn)

        # 1. Gross revenue & order totals
        cursor.execute("SELECT COUNT(order_id), COALESCE(SUM(total_amount), 0.0) FROM orders WHERE order_status = 'COMPLETED';")
        tot_orders, tot_revenue = cursor.fetchone()
        tot_revenue = float(tot_revenue)

        # 2. Revenue share by category
        cursor.execute("""
            SELECT 
                cat.category_name,
                ROUND(SUM(oi.quantity * oi.unit_price), 2) AS category_revenue,
                COUNT(DISTINCT oi.order_id) AS orders_count
            FROM categories cat
            JOIN products p ON cat.category_id = p.category_id
            JOIN order_items oi ON p.product_id = oi.product_id
            GROUP BY cat.category_name
            ORDER BY category_revenue DESC;
        """)
        category_rows = cursor.fetchall()

        # 3. Customer Pareto share (Top 5 customer revenue share)
        cursor.execute("""
            SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0.0) AS spend
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'COMPLETED'
            JOIN order_items oi ON o.order_id = oi.order_id
            GROUP BY c.customer_id
            ORDER BY spend DESC;
        """)
        customer_spends = [float(r[0]) for r in cursor.fetchall()]
        top_5_cust_spend = sum(customer_spends[:5]) if len(customer_spends) >= 5 else sum(customer_spends)

        # 4. High rating, low sales opportunity products
        cursor.execute("""
            SELECT 
                p.product_id,
                p.product_name,
                cat.category_name,
                ROUND(AVG(r.rating), 2) AS avg_rating,
                COUNT(DISTINCT r.review_id) AS review_count,
                COALESCE(SUM(oi.quantity), 0) AS units_sold,
                p.price
            FROM products p
            JOIN categories cat ON p.category_id = cat.category_id
            LEFT JOIN reviews r ON p.product_id = r.product_id
            LEFT JOIN order_items oi ON p.product_id = oi.product_id
            GROUP BY p.product_id, p.product_name, cat.category_name, p.price
            HAVING avg_rating >= 4.7 AND units_sold < 20
            ORDER BY avg_rating DESC, units_sold ASC LIMIT 3;
        """)
        gem_rows = cursor.fetchall()

        # 5. Top market basket co-occurrence pair
        cursor.execute("""
            SELECT product_a_name, product_b_name, co_purchase_count 
            FROM v_frequent_product_pairs 
            ORDER BY co_purchase_count DESC LIMIT 1;
        """)
        top_pair_row = cursor.fetchone()

        conn.close()

        # Get inventory demand metrics
        inv_data = self.get_inventory_intelligence()
        inv_kpis = inv_data["kpis"]
        restock_recs = inv_data["restock_recommendations"]
        overstocked_items = [p for p in inv_data["inventory_matrix"] if p["risk_state"] == "OVERSTOCKED"]

        insights = []

        # INSIGHT 1: Category Revenue Concentration
        if category_rows and tot_revenue > 0:
            top_cat = category_rows[0]
            top_cat_name = top_cat["category_name"]
            top_cat_rev = float(top_cat["category_revenue"])
            top_cat_orders = top_cat["orders_count"]
            share_pct = round((top_cat_rev / tot_revenue) * 100, 1)

            insights.append({
                "id": "INSIGHT_CAT_REVENUE",
                "category": "REVENUE_DISTRIBUTION",
                "type": "GROWTH",
                "badge": "Category Dominance",
                "title": f"'{top_cat_name}' generates {share_pct}% of total store gross revenue.",
                "description": f"The '{top_cat_name}' product domain is the primary commercial driver, contributing ${top_cat_rev:,.2f} across {top_cat_orders} completed orders out of ${tot_revenue:,.2f} total store revenue.",
                "metrics": {
                    "top_category": top_cat_name,
                    "category_revenue": top_cat_rev,
                    "revenue_share_percentage": share_pct,
                    "orders_count": top_cat_orders
                },
                "action": f"Expand supplier depth and cross-merchandise accessories around '{top_cat_name}' hero SKUs."
            })

        # INSIGHT 2: Inventory Restock Urgency
        if restock_recs:
            top_risk = restock_recs[0]
            pname = top_risk["product_name"]
            stock = top_risk["stock_quantity"]
            vel = top_risk["avg_daily_sales"]
            cover = top_risk["estimated_stock_cover_days"]
            cover_str = f"~{cover:.0f} days" if cover is not None else "0 days"

            insights.append({
                "id": "INSIGHT_STOCK_URGENCY",
                "category": "INVENTORY_ALERT",
                "type": "WARNING",
                "badge": "Restock Priority",
                "title": f"'{pname}' has high velocity ({vel}/day) with lowest stock coverage ({cover_str}).",
                "description": f"Current inventory level is {stock} units with sales velocity of {vel} units/day. At current pace, stockout is estimated in {cover_str}.",
                "metrics": {
                    "product_id": top_risk["product_id"],
                    "product_name": pname,
                    "current_stock": stock,
                    "daily_velocity": vel,
                    "days_cover": cover,
                    "recommended_reorder": top_risk["reorder_quantity"]
                },
                "action": f"Dispatch urgent reorder of {top_risk['reorder_quantity']} units to avoid losing high-velocity sales."
            })

        # INSIGHT 3: Customer Pareto Disproportion
        if customer_spends and tot_revenue > 0:
            top_count = min(5, len(customer_spends))
            pareto_pct = round((top_5_cust_spend / tot_revenue) * 100, 1)
            cust_pct = round((top_count / len(customer_spends)) * 100, 1)

            insights.append({
                "id": "INSIGHT_CUSTOMER_PARETO",
                "category": "CUSTOMER_LIFETIME_VALUE",
                "type": "OPPORTUNITY",
                "badge": "Revenue Pareto",
                "title": f"Top {cust_pct}% of customers generate {pareto_pct}% of total lifetime sales.",
                "description": f"The top {top_count} high-value shoppers have contributed ${top_5_cust_spend:,.2f} of ${tot_revenue:,.2f} store revenue, demonstrating high revenue concentration in the High-Value segment.",
                "metrics": {
                    "top_customer_count": top_count,
                    "top_customer_spend": round(top_5_cust_spend, 2),
                    "pareto_share_percentage": pareto_pct
                },
                "action": "Prioritize VIP concierge retention, personalized loyalty incentives, and dedicated priority support."
            })

        # INSIGHT 4: High-Rating Hidden Gems
        if gem_rows:
            gem = gem_rows[0]
            gname = gem["product_name"]
            grat = gem["avg_rating"]
            grev = gem["review_count"]
            gsold = gem["units_sold"]

            insights.append({
                "id": "INSIGHT_HIDDEN_GEMS",
                "category": "PRODUCT_OPPORTUNITY",
                "type": "OPPORTUNITY",
                "badge": "Catalog Hidden Gem",
                "title": f"'{gname}' has a {grat}/5.0 rating but only {gsold} units sold.",
                "description": f"Customer sentiment is overwhelmingly positive ({grat}/5.0 across {grev} reviews), yet sales volume remains low ({gsold} units). The product suffers from low storefront discovery.",
                "metrics": {
                    "product_id": gem["product_id"],
                    "product_name": gname,
                    "average_rating": grat,
                    "review_count": grev,
                    "units_sold": gsold,
                    "price": gem["price"]
                },
                "action": "Feature this SKU in homepage hero carousels and bundle it with complementary bestsellers."
            })

        # INSIGHT 5: Basket Synergy & Bundling
        if top_pair_row:
            pa_name, pb_name, co_cnt = top_pair_row[0], top_pair_row[1], top_pair_row[2]
            insights.append({
                "id": "INSIGHT_BASKET_SYNERGY",
                "category": "BASKET_SYNERGY",
                "type": "GROWTH",
                "badge": "Co-Purchase Affinity",
                "title": f"'{pa_name}' and '{pb_name}' co-occur frequently ({co_cnt} orders).",
                "description": f"Relational basket analysis reveals strong natural pairing between these two SKUs across {co_cnt} customer checkouts.",
                "metrics": {
                    "product_a": pa_name,
                    "product_b": pb_name,
                    "co_purchases": co_cnt
                },
                "action": "Enable an automated 10% bundle discount banner on the product detail page to lift average order value."
            })

        # INSIGHT 6: Excess Inventory Capital Efficiency
        if overstocked_items:
            # Pick highest capital overstocked item
            overstocked_sorted = sorted(overstocked_items, key=lambda x: x["inventory_value"], reverse=True)
            top_over = overstocked_sorted[0]
            val = top_over["inventory_value"]
            stock = top_over["stock_quantity"]
            vel = top_over["avg_daily_sales"]

            insights.append({
                "id": "INSIGHT_OVERSTOCK_CAPITAL",
                "category": "CAPITAL_EFFICIENCY",
                "type": "INFORMATIONAL",
                "badge": "Working Capital",
                "title": f"${val:,.2f} in working capital locked in excess '{top_over['product_name']}' inventory.",
                "description": f"With {stock} units in stock and sales velocity of {vel} units/day, this SKU holds substantial capital that is slow-moving.",
                "metrics": {
                    "product_id": top_over["product_id"],
                    "product_name": top_over["product_name"],
                    "locked_capital": val,
                    "stock_quantity": stock,
                    "daily_velocity": vel
                },
                "action": "Run flash bundle promotion or include as a free gift with purchase on high-ticket workstation orders."
            })

        return {
            "status": "success",
            "insights_count": len(insights),
            "insights": insights
        }
