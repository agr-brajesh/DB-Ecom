"""
Flask REST API Server for AI-Based E-Commerce Project
Exposes endpoints for Storefront, Recommendations, Cart,
ACID Transactions, Apriori Analytics, and Live SQL Runner.
"""

import os
import sys
import time
import sqlite3
from flask import Flask, jsonify, request, send_from_directory, g, has_request_context
from flask_cors import CORS

# Add root directory to sys.path so we can import from database and ai
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ai.recommender import ProductRecommender
from ai.business_intelligence import BusinessIntelligenceEngine
from ai.sentiment_analyzer import ReviewSentimentAnalyzer
from ai.analytics_engine import AdminAnalyticsEngine
from database.transactions import checkout_cart, get_db_connection as _db_get_connection

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "frontend"), static_url_path="")
CORS(app)


def get_db_connection():
    """
    Returns a request-scoped SQLite connection stored on Flask's g object.
    Automatically managed and closed via teardown_request.
    """
    if has_request_context():
        if "db" in g:
            try:
                g.db.execute("SELECT 1;")
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                g.db = _db_get_connection()
        else:
            g.db = _db_get_connection()
        return g.db
    return _db_get_connection()


@app.teardown_request
def teardown_request_db(exception=None):
    """Closes request-scoped database connection if one was opened during the request."""
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


DB_PATH = os.path.join(BASE_DIR, "database", "ecommerce.db")
recommender = ProductRecommender(DB_PATH)
bi_engine = BusinessIntelligenceEngine(DB_PATH)
review_analyzer = ReviewSentimentAnalyzer(DB_PATH)
admin_analytics = AdminAnalyticsEngine(DB_PATH)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/customers", methods=["GET"])
def get_customers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.customer_id, c.name, c.email, c.city, 
               COALESCE(v.total_orders, 0) as total_orders,
               COALESCE(v.lifetime_spend, 0.0) as lifetime_spend
        FROM customers c
        LEFT JOIN v_customer_purchase_summary v ON c.customer_id = v.customer_id
        ORDER BY c.customer_id ASC;
    """)
    rows = cursor.fetchall()
    conn.close()

    customers = []
    for r in rows:
        customers.append({
            "customer_id": r[0],
            "name": r[1],
            "email": r[2],
            "city": r[3],
            "total_orders": r[4],
            "lifetime_spend": round(r[5], 2)
        })
    return jsonify({"status": "success", "customers": customers})


@app.route("/api/products", methods=["GET"])
def get_products():
    category_id = request.args.get("category_id")
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT p.product_id, p.product_name, p.brand, p.price, p.stock_quantity, 
               p.description, cat.category_id, cat.category_name,
               ROUND(AVG(r.rating), 1) as avg_rating, COUNT(r.review_id) as review_count
        FROM products p
        JOIN categories cat ON p.category_id = cat.category_id
        LEFT JOIN reviews r ON p.product_id = r.product_id
    """
    params = []
    if category_id:
        query += " WHERE cat.category_id = ?"
        params.append(category_id)

    query += " GROUP BY p.product_id ORDER BY p.category_id, p.product_id;"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.execute("SELECT category_id, category_name, description FROM categories ORDER BY category_id;")
    cat_rows = cursor.fetchall()
    conn.close()

    products = []
    for r in rows:
        products.append({
            "product_id": r[0],
            "product_name": r[1],
            "brand": r[2],
            "price": r[3],
            "stock_quantity": r[4],
            "description": r[5],
            "category_id": r[6],
            "category_name": r[7],
            "avg_rating": r[8] or 4.5,
            "review_count": r[9] or 0
        })

    categories = [{"category_id": c[0], "category_name": c[1], "description": c[2]} for c in cat_rows]
    return jsonify({"status": "success", "categories": categories, "products": products})


@app.route("/api/product/<product_id>", methods=["GET"])
@app.route("/api/products/<product_id>", methods=["GET"])
def get_product_details(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.product_id, p.product_name, p.brand, p.price, p.stock_quantity, 
               p.description, cat.category_id, cat.category_name,
               ROUND(AVG(r.rating), 1) as avg_rating, COUNT(r.review_id) as review_count
        FROM products p
        JOIN categories cat ON p.category_id = cat.category_id
        LEFT JOIN reviews r ON p.product_id = r.product_id
        WHERE p.product_id = ?
        GROUP BY p.product_id;
    """, (product_id,))
    prod = cursor.fetchone()
    if not prod:
        conn.close()
        return jsonify({"status": "error", "message": "Product not found"}), 404

    # Fetch product reviews
    cursor.execute("""
        SELECT r.rating, r.comment, r.review_date, c.name as customer_name
        FROM reviews r
        JOIN customers c ON r.customer_id = c.customer_id
        WHERE r.product_id = ?
        ORDER BY r.review_date DESC LIMIT 10;
    """, (product_id,))
    reviews = [{
        "rating": r[0],
        "comment": r[1],
        "review_date": r[2],
        "customer_name": r[3]
    } for r in cursor.fetchall()]
    conn.close()

    # Frequently bought together (Apriori rules where product_id is in antecedent)
    frequently_bought = []
    seen_fbt = set()
    for rule in recommender.rules:
        if product_id in rule["antecedent"]:
            for con in rule["consequent"]:
                if con != product_id and con not in seen_fbt:
                    details = recommender._get_product_details(con)
                    if details:
                        details["confidence"] = rule["confidence"]
                        details["lift"] = rule["lift"]
                        frequently_bought.append(details)
                        seen_fbt.add(con)
                if len(frequently_bought) >= 4:
                    break
        if len(frequently_bought) >= 4:
            break

    # Similar products from Content-Based engine
    similar_products = recommender.content_engine.recommend_similar_products(product_id, top_n=4)

    # Phase 8: AI Review Intelligence & Sentiment Analysis
    review_intel = review_analyzer.get_product_review_intelligence(product_id)

    return jsonify({
        "status": "success",
        "product": {
            "product_id": prod[0],
            "product_name": prod[1],
            "brand": prod[2],
            "price": prod[3],
            "stock_quantity": prod[4],
            "description": prod[5],
            "category_id": prod[6],
            "category_name": prod[7],
            "avg_rating": prod[8] or 4.5,
            "review_count": prod[9] or 0,
            "reviews": reviews,
            "review_intelligence": review_intel,
            "frequently_bought": frequently_bought,
            "similar_products": similar_products
        }
    })


@app.route("/api/orders/<customer_id>", methods=["GET"])
def get_customer_orders(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.order_id, o.order_date, o.total_amount, o.order_status,
               COALESCE(p.payment_method, 'CREDIT_CARD') as payment_method,
               COALESCE(p.payment_status, 'SUCCESS') as payment_status,
               oi.product_id, pr.product_name, oi.quantity, oi.unit_price, cat.category_name
        FROM orders o
        LEFT JOIN payments p ON o.order_id = p.order_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products pr ON oi.product_id = pr.product_id
        JOIN categories cat ON pr.category_id = cat.category_id
        WHERE o.customer_id = ?
        ORDER BY o.order_date DESC, o.order_id DESC;
    """, (customer_id,))
    rows = cursor.fetchall()
    conn.close()

    orders_dict = {}
    for r in rows:
        oid = r[0]
        if oid not in orders_dict:
            orders_dict[oid] = {
                "order_id": oid,
                "order_date": r[1],
                "total_amount": r[2],
                "order_status": r[3],
                "payment_method": r[4],
                "payment_status": r[5],
                "items": []
            }
        orders_dict[oid]["items"].append({
            "product_id": r[6],
            "product_name": r[7],
            "quantity": r[8],
            "unit_price": r[9],
            "category_name": r[10],
            "subtotal": round(r[8] * r[9], 2)
        })

    return jsonify({"status": "success", "orders": list(orders_dict.values())})


@app.route("/api/admin/overview", methods=["GET"])
def get_admin_overview():
    """
    Phase 9 & Legacy: High-quality Admin Overview KPI Dashboard.
    Accepts ?range=7d|30d|90d|all. Calculates real SQL metrics and genuine historical comparisons.
    """
    date_range = request.args.get("range", "all").strip().lower()
    if date_range not in ("7d", "30d", "90d", "all"):
        date_range = "all"

    try:
        overview_data = admin_analytics.get_overview_kpis(date_range=date_range)
        kpis = overview_data["kpis"]
        growth = overview_data.get("growth_comparison")

        # Fetch recent orders and low-stock alerts for immediate action
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT product_id, product_name, stock_quantity, price FROM products WHERE stock_quantity < 120 ORDER BY stock_quantity ASC LIMIT 10;")
        low_stock = [{"product_id": r[0], "product_name": r[1], "stock_quantity": r[2], "price": r[3]} for r in cursor.fetchall()]

        cursor.execute("SELECT product_id, product_name, category_name, units_sold, total_revenue, avg_rating FROM v_product_performance ORDER BY units_sold DESC LIMIT 5;")
        top_products = [{"product_id": r[0], "product_name": r[1], "category_name": r[2], "units_sold": r[3], "total_revenue": r[4], "avg_rating": r[5]} for r in cursor.fetchall()]

        cursor.execute("""
            SELECT cat.category_name, COUNT(oi.order_item_id) as items_sold, ROUND(SUM(oi.quantity * oi.unit_price), 2) as revenue
            FROM categories cat
            JOIN products p ON cat.category_id = p.category_id
            JOIN order_items oi ON p.product_id = oi.product_id
            GROUP BY cat.category_id, cat.category_name
            ORDER BY revenue DESC;
        """)
        category_sales = [{"category_name": r[0], "items_sold": r[1], "revenue": r[2]} for r in cursor.fetchall()]

        cursor.execute("""
            SELECT o.order_id, c.name, o.order_date, o.total_amount, o.order_status, COALESCE(p.payment_method, 'CREDIT_CARD')
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            LEFT JOIN payments p ON o.order_id = p.order_id
            ORDER BY o.order_date DESC LIMIT 10;
        """)
        recent_orders = [{
            "order_id": r[0],
            "customer_name": r[1],
            "order_date": r[2],
            "total_amount": r[3],
            "order_status": r[4],
            "payment_method": r[5]
        } for r in cursor.fetchall()]

        conn.close()

        # Legacy backward-compatible payload nested inside 'overview'
        legacy_overview = {
            "gross_revenue": kpis["total_revenue"],
            "total_orders": kpis["total_orders"],
            "total_customers": kpis["total_customers"],
            "average_order_value": kpis["average_order_value"],
            "products_sold": kpis["products_sold"],
            "low_stock_products": low_stock,
            "total_products": len(recommender.miner.product_name_map),
            "total_rules": len(recommender.rules),
            "top_products": top_products,
            "category_sales": category_sales,
            "recent_orders": recent_orders,
            "growth_comparison": growth
        }

        return jsonify({
            "status": "success",
            "date_range": date_range,
            "kpis": kpis,
            "growth_comparison": growth,
            "low_stock_alerts": low_stock,
            "top_products": top_products,
            "category_sales": category_sales,
            "recent_orders": recent_orders,
            "overview": legacy_overview
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/sales-analytics", methods=["GET"])
def get_admin_sales_analytics():
    """
    Phase 9: Comprehensive Sales Analytics with Timeline Buckets, Category Breakdown,
    Payment Distributions, and Volume / Revenue Leaders.
    """
    date_range = request.args.get("range", "30d").strip().lower()
    if date_range not in ("7d", "30d", "90d", "all"):
        date_range = "30d"

    try:
        data = admin_analytics.get_sales_analytics(date_range=date_range)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/product-analytics", methods=["GET"])
def get_admin_product_analytics_consolidated():
    """
    Phase 9: Consolidated Product Intelligence matrix combining commercial velocity,
    revenue rankings, stock coverage risk, and Phase 8 review sentiment health.
    """
    sort_by = request.args.get("sort", "best_selling").strip().lower()
    category_id = request.args.get("category_id")
    if category_id:
        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            category_id = None

    try:
        data = admin_analytics.get_consolidated_product_intelligence(sort_by=sort_by, category_id=category_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/customer-analytics", methods=["GET"])
def get_admin_customer_analytics():
    """
    Phase 9: Customer Intelligence integrating RFM segmentation, customer lifetime value,
    and purchase activity.
    """
    try:
        data = bi_engine.get_customer_segments_summary()
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/inventory-analytics", methods=["GET"])
def get_admin_inventory_analytics_alias():
    """Phase 9: Operational Inventory Intelligence alias."""
    try:
        recent_days = int(request.args.get("recent_days", 30))
        if recent_days <= 0:
            recent_days = 30
    except (ValueError, TypeError):
        recent_days = 30

    try:
        data = bi_engine.get_inventory_intelligence(recent_window_days=recent_days)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/ai-analytics", methods=["GET"])
@app.route("/api/admin/ai-recommendation-analytics", methods=["GET"])
def get_admin_ai_recommendation_analytics():
    """
    Phase 9: AI Intelligence Dashboard showing Apriori association rules,
    hybrid signal weights, active commerce intent types, and companion product frequencies.
    """
    try:
        data = admin_analytics.get_ai_recommendation_analytics(recommender)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/insights", methods=["GET"])
def get_admin_consolidated_insights():
    """
    Phase 9: Real-time business intelligence insights derived strictly from database queries.
    """
    date_range = request.args.get("range", "all").strip().lower()
    if date_range not in ("7d", "30d", "90d", "all"):
        date_range = "all"

    try:
        data = admin_analytics.get_business_insights(date_range=date_range)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# PHASE 7: BUSINESS INTELLIGENCE & SEGMENTATION ENDPOINTS
# =============================================================================

@app.route("/api/admin/customer-segments", methods=["GET"])
def get_admin_customer_segments():
    """Phase 7: Explainable RFM Customer Segmentation & Cohort Analysis."""
    try:
        data = bi_engine.get_customer_segments_summary()
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/customer/<customer_id>/insights", methods=["GET"])
def get_admin_customer_insights(customer_id):
    """Phase 7: Customer-specific lifetime value, RFM proof, and segment reasoning."""
    try:
        data = bi_engine.get_customer_insights(customer_id)
        if data.get("status") == "error":
            return jsonify(data), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/inventory-intelligence", methods=["GET"])
def get_admin_inventory_intelligence():
    """Phase 7: Inventory demand velocity, days coverage, and restock prioritization."""
    try:
        recent_days = int(request.args.get("recent_days", 30))
        if recent_days <= 0:
            recent_days = 30
    except (ValueError, TypeError):
        recent_days = 30

    try:
        data = bi_engine.get_inventory_intelligence(recent_window_days=recent_days)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/product-intelligence", methods=["GET"])
def get_admin_product_intelligence():
    """Phase 7: Product commercial matrix, revenue/volume ranks, ratings, and companion affinity."""
    try:
        data = bi_engine.get_product_intelligence()
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/ai-insights", methods=["GET"])
def get_admin_ai_insights():
    """Phase 7: Actionable business insights derived directly from database transactions."""
    try:
        data = bi_engine.get_ai_insights()
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# PHASE 8: AI REVIEW INTELLIGENCE & SENTIMENT ANALYSIS ENDPOINTS
# =============================================================================

@app.route("/api/products/<product_id>/review-intelligence", methods=["GET"])
@app.route("/api/product/<product_id>/review-intelligence", methods=["GET"])
def get_product_review_intelligence(product_id):
    """
    Phase 8: Extract explainable sentiment, product health scorecard, 
    aspect themes, and concise customer summary from reviews table.
    """
    try:
        data = review_analyzer.get_product_review_intelligence(product_id)
        if data.get("status") == "error":
            return jsonify(data), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/review-intelligence", methods=["GET"])
@app.route("/api/admin/review-analytics", methods=["GET"])
def get_admin_review_intelligence():
    """
    Phase 8: Catalog-wide review intelligence matrix for admin portal.
    Supports filtering by 'all', 'most_positive', 'most_negative', 'most_reviewed', 'mismatched'.
    """
    filter_type = request.args.get("filter", "all").strip().lower()
    try:
        data = review_analyzer.get_catalog_review_intelligence(filter_type=filter_type)
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/product/<product_id>/review-intelligence", methods=["GET"])
def get_admin_product_review_intelligence(product_id):
    """
    Phase 8: Deep-dive inspector endpoint for admin review drilldown.
    """
    try:
        data = review_analyzer.get_product_review_intelligence(product_id)
        if data.get("status") == "error":
            return jsonify(data), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/recommendations/<customer_id>", methods=["GET"])
def get_recommendations(customer_id):
    """Phase 4 & 5: Context-Aware Multi-Signal Hybrid Recommendations."""
    try:
        top_n = int(request.args.get("top_n", 4))
        if top_n <= 0:
            top_n = 4
    except (ValueError, TypeError):
        top_n = 4

    current_product_id = request.args.get("current_product_id")
    context_type = request.args.get("context_type")

    res = recommender.recommend(
        customer_id,
        current_product_id=current_product_id,
        context_type=context_type,
        top_n=top_n
    )
    if "error" in res:
        return jsonify({"status": "error", "message": res["error"]}), 404
    return jsonify({"status": "success", "data": res})


@app.route("/api/recommendations/audit/<customer_id>", methods=["GET"])
def audit_recommendations(customer_id):
    """
    Phase 6: Explainable AI & Recommendation Provenance Audit.
    Returns comprehensive trace of candidate scores, feature matrices,
    mathematical proofs (support, confidence, lift), and customer explanations.
    """
    try:
        top_n = int(request.args.get("top_n", 6))
        if top_n <= 0:
            top_n = 6
    except (ValueError, TypeError):
        top_n = 6

    current_product_id = request.args.get("current_product_id")
    context_type = request.args.get("context_type")

    res = recommender.recommend(
        customer_id,
        current_product_id=current_product_id,
        context_type=context_type,
        top_n=top_n
    )
    if "error" in res and not res.get("recommendations"):
        return jsonify({"status": "error", "message": res["error"]}), 404

    return jsonify({
        "status": "success",
        "audit": {
            "customer_id": customer_id,
            "context": res.get("context", {}),
            "customer": res.get("customer", {}),
            "history_count": len(res.get("history", [])),
            "cart_count": len(res.get("active_cart", [])),
            "search_count": len(res.get("recent_searches", [])),
            "recommendations": res.get("recommendations", [])
        }
    })


@app.route("/api/recommendations/bundle/<product_id>", methods=["GET"])
def get_frequently_bought_bundle(product_id):
    """Phase 5: Genuine Frequently Bought Together bundle with instant bundle savings."""
    try:
        top_n = int(request.args.get("top_n", 2))
    except (ValueError, TypeError):
        top_n = 2
    res = recommender.recommend_frequently_bought_together(product_id, top_n=top_n)
    if "error" in res:
        return jsonify({"status": "error", "message": res["error"]}), 404
    return jsonify({"status": "success", "bundle": res})


@app.route("/api/recommendations/alternatives/<product_id>", methods=["GET"])
def get_product_alternatives(product_id):
    """Phase 5: High-quality, in-stock alternatives for out-of-stock or product comparison."""
    try:
        top_n = int(request.args.get("top_n", 3))
    except (ValueError, TypeError):
        top_n = 3
    res = recommender.recommend_product_alternatives(product_id, top_n=top_n)
    if "error" in res:
        return jsonify({"status": "error", "message": res["error"]}), 404
    return jsonify({
        "status": "success",
        "data": res,
        "alternatives": res.get("alternatives", [])
    })


@app.route("/api/recommendations/setup/<customer_id>", methods=["GET"])
def get_complete_setup_recommendations(customer_id):
    """Phase 5: Setup completion peripheral recommendations."""
    current_product_id = request.args.get("current_product_id")
    try:
        top_n = int(request.args.get("top_n", 3))
    except (ValueError, TypeError):
        top_n = 3
    res = recommender.recommend_complete_your_setup(customer_id, current_product_id=current_product_id, top_n=top_n)
    if "error" in res:
        return jsonify({"status": "error", "message": res["error"]}), 404
    return jsonify({
        "status": "success",
        "data": res,
        "setup": res.get("setup", [])
    })


@app.route("/api/events/record", methods=["POST"])
def record_session_event():
    """Phase 5: Real-time session event tracking (PRODUCT_VIEW, SEARCH, ADD_TO_CART, etc.)."""
    data = request.json or {}
    customer_id = data.get("customer_id")
    product_id = data.get("product_id")
    event_type = data.get("event_type", "PRODUCT_VIEW")

    if not customer_id or not event_type:
        return jsonify({"status": "error", "message": "Missing customer_id or event_type"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO session_events (customer_id, product_id, event_type)
        VALUES (?, ?, ?);
    """, (customer_id, product_id, event_type))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Session event logged"}), 201



@app.route("/api/cart/<customer_id>", methods=["GET"])
def get_cart(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sc.cart_id, sc.product_id, p.product_name, p.price, sc.quantity, p.stock_quantity
        FROM shopping_cart sc
        JOIN products p ON sc.product_id = p.product_id
        WHERE sc.customer_id = ?;
    """, (customer_id,))
    rows = cursor.fetchall()
    conn.close()

    items = []
    total = 0.0
    for r in rows:
        subtotal = round(r[3] * r[4], 2)
        total += subtotal
        items.append({
            "cart_id": r[0],
            "product_id": r[1],
            "product_name": r[2],
            "price": r[3],
            "quantity": r[4],
            "stock_quantity": r[5],
            "subtotal": subtotal
        })

    return jsonify({"status": "success", "items": items, "total_amount": round(total, 2)})


@app.route("/api/cart/add", methods=["POST"])
def add_to_cart():
    data = request.json or {}
    customer_id = data.get("customer_id")
    product_id = data.get("product_id")

    if not customer_id or not product_id:
        return jsonify({"status": "error", "message": "Missing customer_id or product_id"}), 400

    try:
        quantity = int(data.get("quantity", 1))
        if quantity <= 0:
            return jsonify({"status": "error", "message": "Quantity must be greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid quantity provided"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify customer existence (return 404 if customer not found)
    cursor.execute("SELECT customer_id FROM customers WHERE customer_id = ?;", (customer_id,))
    if not cursor.fetchone():
        return jsonify({"status": "error", "message": f"Customer '{customer_id}' not found"}), 404

    # Check product existence and stock
    cursor.execute("SELECT stock_quantity, product_name FROM products WHERE product_id = ?;", (product_id,))
    prod = cursor.fetchone()
    if not prod:
        return jsonify({"status": "error", "message": "Product not found"}), 404

    stock_quantity, prod_name = prod[0], prod[1]

    # Validate stock ceiling accounting for items already in cart
    cursor.execute("SELECT quantity FROM shopping_cart WHERE customer_id = ? AND product_id = ?;", (customer_id, product_id))
    existing_row = cursor.fetchone()
    current_cart_qty = existing_row[0] if existing_row else 0

    if current_cart_qty + quantity > stock_quantity:
        return jsonify({
            "status": "error",
            "message": f"Requested quantity ({quantity}) plus existing cart quantity ({current_cart_qty}) exceeds available stock ({stock_quantity}) for {prod_name}"
        }), 400

    # Upsert into cart
    cursor.execute("""
        INSERT INTO shopping_cart (customer_id, product_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(customer_id, product_id) 
        DO UPDATE SET quantity = quantity + excluded.quantity;
    """, (customer_id, product_id, quantity))

    conn.commit()
    return jsonify({"status": "success", "message": f"Added {prod_name} to cart."})


@app.route("/api/cart/remove", methods=["POST"])
def remove_from_cart():
    data = request.json or {}
    customer_id = data.get("customer_id")
    product_id = data.get("product_id")

    if not customer_id or not product_id:
        return jsonify({"status": "error", "message": "Missing customer_id or product_id"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shopping_cart WHERE customer_id = ? AND product_id = ?;", (customer_id, product_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Item removed from cart."})


@app.route("/api/cart/update", methods=["POST"])
def update_cart_quantity():
    """Phase 3: Update item quantity in cart with strict stock ceiling validation."""
    data = request.json or {}
    customer_id = data.get("customer_id")
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if not customer_id or not product_id or quantity is None:
        return jsonify({"status": "error", "message": "Missing customer_id, product_id, or quantity"}), 400

    try:
        quantity = int(quantity)
        if quantity <= 0:
            return jsonify({"status": "error", "message": "Quantity must be greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid quantity provided"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Stock validation
    cursor.execute("SELECT stock_quantity, product_name, price FROM products WHERE product_id = ?;", (product_id,))
    prod = cursor.fetchone()
    if not prod:
        conn.close()
        return jsonify({"status": "error", "message": "Product not found"}), 404

    stock_quantity, prod_name, price = prod[0], prod[1], prod[2]
    if quantity > stock_quantity:
        conn.close()
        return jsonify({
            "status": "error",
            "message": f"Requested quantity ({quantity}) exceeds available stock ({stock_quantity}) for {prod_name}"
        }), 400

    # Verify item exists in cart
    cursor.execute("SELECT cart_id FROM shopping_cart WHERE customer_id = ? AND product_id = ?;", (customer_id, product_id))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return jsonify({"status": "error", "message": "Item not found in cart"}), 404

    cursor.execute("UPDATE shopping_cart SET quantity = ? WHERE customer_id = ? AND product_id = ?;", (quantity, customer_id, product_id))
    conn.commit()

    # Calculate updated cart total
    cursor.execute("""
        SELECT COALESCE(SUM(sc.quantity * p.price), 0.0)
        FROM shopping_cart sc
        JOIN products p ON sc.product_id = p.product_id
        WHERE sc.customer_id = ?;
    """, (customer_id,))
    cart_total = cursor.fetchone()[0]
    conn.close()

    return jsonify({
        "status": "success",
        "message": f"Updated quantity for {prod_name}",
        "product_id": product_id,
        "quantity": quantity,
        "subtotal": round(price * quantity, 2),
        "cart_total": round(cart_total, 2)
    })


@app.route("/api/wishlist/<customer_id>", methods=["GET"])
def get_customer_wishlist(customer_id):
    """Phase 3: Fetch persistent customer wishlist items with category and ratings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT w.wishlist_id, w.product_id, p.product_name, p.brand, p.price, p.stock_quantity,
               cat.category_name, ROUND(AVG(r.rating), 1) as avg_rating, w.added_at
        FROM wishlist w
        JOIN products p ON w.product_id = p.product_id
        JOIN categories cat ON p.category_id = cat.category_id
        LEFT JOIN reviews r ON p.product_id = r.product_id
        WHERE w.customer_id = ?
        GROUP BY w.wishlist_id, p.product_id
        ORDER BY w.added_at DESC;
    """, (customer_id,))
    rows = cursor.fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append({
            "wishlist_id": r[0],
            "product_id": r[1],
            "product_name": r[2],
            "brand": r[3],
            "price": r[4],
            "stock_quantity": r[5],
            "category_name": r[6],
            "avg_rating": r[7] or 4.5,
            "added_at": r[8]
        })

    return jsonify({"status": "success", "wishlist": items, "count": len(items)})


@app.route("/api/wishlist/toggle", methods=["POST"])
def toggle_wishlist():
    """Phase 3: Toggle product in customer wishlist (Insert or Delete)."""
    data = request.json or {}
    customer_id = data.get("customer_id")
    product_id = data.get("product_id")

    if not customer_id or not product_id:
        return jsonify({"status": "error", "message": "Missing customer_id or product_id"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT product_name FROM products WHERE product_id = ?;", (product_id,))
    prod = cursor.fetchone()
    if not prod:
        conn.close()
        return jsonify({"status": "error", "message": "Product not found"}), 404

    cursor.execute("SELECT wishlist_id FROM wishlist WHERE customer_id = ? AND product_id = ?;", (customer_id, product_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM wishlist WHERE customer_id = ? AND product_id = ?;", (customer_id, product_id))
        conn.commit()
        in_wishlist = False
        action = "removed"
        message = f"Removed {prod[0]} from wishlist"
    else:
        cursor.execute("INSERT INTO wishlist (customer_id, product_id) VALUES (?, ?);", (customer_id, product_id))
        conn.commit()
        in_wishlist = True
        action = "added"
        message = f"Added {prod[0]} to wishlist"

    cursor.execute("SELECT COUNT(*) FROM wishlist WHERE customer_id = ?;", (customer_id,))
    wishlist_count = cursor.fetchone()[0]
    conn.close()

    return jsonify({
        "status": "success",
        "action": action,
        "in_wishlist": in_wishlist,
        "message": message,
        "wishlist_count": wishlist_count
    })


@app.route("/api/search/suggestions", methods=["GET"])
def get_search_suggestions():
    """Phase 3: Real-time search typeahead suggestions matching products, brands, and categories."""
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"status": "success", "suggestions": []})

    conn = get_db_connection()
    cursor = conn.cursor()
    like_pat = f"%{q}%"

    # Match products & brands
    cursor.execute("""
        SELECT p.product_id, p.product_name, p.brand, p.price, cat.category_name
        FROM products p
        JOIN categories cat ON p.category_id = cat.category_id
        WHERE p.product_name LIKE ? OR p.brand LIKE ? OR cat.category_name LIKE ?
        ORDER BY CASE 
            WHEN p.product_name LIKE ? THEN 1 
            WHEN p.brand LIKE ? THEN 2 
            ELSE 3 
        END, p.product_name ASC
        LIMIT 6;
    """, (like_pat, like_pat, like_pat, f"{q}%", f"{q}%"))
    prod_rows = cursor.fetchall()

    # Match categories
    cursor.execute("""
        SELECT category_id, category_name FROM categories WHERE category_name LIKE ? LIMIT 2;
    """, (like_pat,))
    cat_rows = cursor.fetchall()
    conn.close()

    suggestions = []
    for c in cat_rows:
        suggestions.append({
            "type": "category",
            "id": c[0],
            "title": c[1],
            "subtitle": "Category"
        })
    for p in prod_rows:
        suggestions.append({
            "type": "product",
            "id": p[0],
            "title": p[1],
            "subtitle": f"{p[2]} • {p[4]} • ${p[3]}"
        })

    return jsonify({"status": "success", "suggestions": suggestions})


@app.route("/api/search/record", methods=["POST"])
def record_search():
    """Phase 3: Record customer search in search_history to authentically feed content-based engine."""
    data = request.json or {}
    customer_id = data.get("customer_id")
    query = (data.get("query") or "").strip()

    if not customer_id or not query:
        return jsonify({"status": "error", "message": "Missing customer_id or query"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO search_history (customer_id, search_query) VALUES (?, ?);", (customer_id, query))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Search recorded"})


@app.route("/api/profile/<customer_id>", methods=["GET"])
def get_customer_profile(customer_id):
    """Phase 3: Comprehensive customer account profile with statistics and history."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Customer row
    cursor.execute("SELECT customer_id, name, email, phone, city, created_at FROM customers WHERE customer_id = ?;", (customer_id,))
    cust = cursor.fetchone()
    if not cust:
        conn.close()
        return jsonify({"status": "error", "message": "Customer not found"}), 404

    # Purchase summary view
    cursor.execute("""
        SELECT total_orders, total_items_purchased, lifetime_spend
        FROM v_customer_purchase_summary WHERE customer_id = ?;
    """, (customer_id,))
    v_summary = cursor.fetchone()

    total_orders = v_summary[0] if v_summary else 0
    total_items = v_summary[1] if v_summary else 0
    lifetime_spend = round(v_summary[2], 2) if v_summary else 0.0
    avg_order_val = round(lifetime_spend / total_orders, 2) if total_orders > 0 else 0.0

    # First and last order date from orders
    cursor.execute("SELECT MIN(order_date), MAX(order_date) FROM orders WHERE customer_id = ?;", (customer_id,))
    date_row = cursor.fetchone()
    min_date = date_row[0] if date_row else None
    max_date = date_row[1] if date_row else None

    # Wishlist count
    cursor.execute("SELECT COUNT(*) FROM wishlist WHERE customer_id = ?;", (customer_id,))
    wishlist_count = cursor.fetchone()[0]

    # Cart items count
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0) FROM shopping_cart WHERE customer_id = ?;", (customer_id,))
    cart_summary = cursor.fetchone()

    # Top preferred categories
    cursor.execute("""
        SELECT cat.category_name, COUNT(oi.order_item_id) as items_count, ROUND(SUM(oi.quantity * oi.unit_price), 2) as total_spent
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN categories cat ON p.category_id = cat.category_id
        WHERE o.customer_id = ? AND o.order_status = 'COMPLETED'
        GROUP BY cat.category_id, cat.category_name
        ORDER BY total_spent DESC LIMIT 3;
    """, (customer_id,))
    top_categories = [{"category_name": r[0], "items_count": r[1], "total_spent": r[2]} for r in cursor.fetchall()]

    # Recent searches
    cursor.execute("""
        SELECT search_query, searched_at FROM search_history WHERE customer_id = ? ORDER BY searched_at DESC LIMIT 5;
    """, (customer_id,))
    recent_searches = [{"query": r[0], "searched_at": r[1]} for r in cursor.fetchall()]

    # Recent 5 orders
    cursor.execute("""
        SELECT o.order_id, o.order_date, o.total_amount, o.order_status,
               COALESCE(p.payment_method, 'CREDIT_CARD') as payment_method,
               COALESCE(p.payment_status, 'SUCCESS') as payment_status
        FROM orders o
        LEFT JOIN payments p ON o.order_id = p.order_id
        WHERE o.customer_id = ?
        ORDER BY o.order_date DESC LIMIT 5;
    """, (customer_id,))
    recent_orders = []
    for r in cursor.fetchall():
        recent_orders.append({
            "order_id": r[0],
            "order_date": r[1],
            "total_amount": r[2],
            "order_status": r[3],
            "payment_method": r[4],
            "payment_status": r[5]
        })

    conn.close()

    return jsonify({
        "status": "success",
        "profile": {
            "customer_id": cust[0],
            "name": cust[1],
            "email": cust[2],
            "phone": cust[3],
            "city": cust[4],
            "registered_at": cust[5],
            "total_orders": total_orders,
            "total_items": total_items,
            "lifetime_spend": lifetime_spend,
            "avg_order_value": avg_order_val,
            "first_order_date": min_date,
            "last_order_date": max_date,
            "wishlist_count": wishlist_count,
            "cart_count": cart_summary[1],
            "top_categories": top_categories,
            "recent_searches": recent_searches,
            "recent_orders": recent_orders
        }
    })


@app.route("/api/home/sections", methods=["GET"])
def get_home_sections():
    """Phase 3: Dynamic homepage commerce sections backed by database views."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Featured / Best-sellers from v_product_performance
    cursor.execute("""
        SELECT p.product_id, p.product_name, p.brand, p.price, p.stock_quantity,
               cat.category_name, ROUND(AVG(r.rating), 1) as avg_rating, COUNT(r.review_id) as review_count,
               v.units_sold
        FROM v_product_performance v
        JOIN products p ON v.product_id = p.product_id
        JOIN categories cat ON p.category_id = cat.category_id
        LEFT JOIN reviews r ON p.product_id = r.product_id
        GROUP BY p.product_id
        ORDER BY v.units_sold DESC LIMIT 4;
    """)
    featured = []
    for r in cursor.fetchall():
        featured.append({
            "product_id": r[0],
            "product_name": r[1],
            "brand": r[2],
            "price": r[3],
            "stock_quantity": r[4],
            "category_name": r[5],
            "avg_rating": r[6] or 4.8,
            "review_count": r[7] or 0,
            "badge": f"🔥 {r[8]} Sold"
        })

    # 2. Top-rated products
    cursor.execute("""
        SELECT p.product_id, p.product_name, p.brand, p.price, p.stock_quantity,
               cat.category_name, ROUND(AVG(r.rating), 1) as avg_rating, COUNT(r.review_id) as review_count
        FROM products p
        JOIN categories cat ON p.category_id = cat.category_id
        JOIN reviews r ON p.product_id = r.product_id
        GROUP BY p.product_id
        HAVING review_count >= 1
        ORDER BY avg_rating DESC, review_count DESC LIMIT 4;
    """)
    top_rated = []
    for r in cursor.fetchall():
        top_rated.append({
            "product_id": r[0],
            "product_name": r[1],
            "brand": r[2],
            "price": r[3],
            "stock_quantity": r[4],
            "category_name": r[5],
            "avg_rating": r[6],
            "review_count": r[7],
            "badge": f"⭐ {r[6]} Rating"
        })

    # 3. Frequent product pair / bundle from v_frequent_product_pairs
    cursor.execute("""
        SELECT product_a_id, product_a_name, product_b_id, product_b_name, co_purchase_count
        FROM v_frequent_product_pairs
        ORDER BY co_purchase_count DESC LIMIT 1;
    """)
    pair = cursor.fetchone()
    bundle = None
    if pair:
        cursor.execute("SELECT product_id, product_name, price, brand FROM products WHERE product_id IN (?, ?);", (pair[0], pair[2]))
        prods = {p[0]: {"id": p[0], "name": p[1], "price": p[2], "brand": p[3]} for p in cursor.fetchall()}
        if pair[0] in prods and pair[2] in prods:
            p1, p2 = prods[pair[0]], prods[pair[2]]
            bundle_price = round((p1["price"] + p2["price"]) * 0.9, 2)
            bundle = {
                "co_purchase_count": pair[4],
                "product1": p1,
                "product2": p2,
                "original_price": round(p1["price"] + p2["price"], 2),
                "bundle_price": bundle_price,
                "savings": round(p1["price"] + p2["price"] - bundle_price, 2)
            }

    # 4. Category highlights with counts
    cursor.execute("""
        SELECT cat.category_id, cat.category_name, cat.description, COUNT(p.product_id) as product_count
        FROM categories cat
        LEFT JOIN products p ON cat.category_id = p.category_id
        GROUP BY cat.category_id, cat.category_name
        ORDER BY product_count DESC;
    """)
    categories = [{
        "category_id": r[0],
        "category_name": r[1],
        "description": r[2],
        "product_count": r[3]
    } for r in cursor.fetchall()]

    conn.close()

    return jsonify({
        "status": "success",
        "sections": {
            "featured": featured,
            "top_rated": top_rated,
            "bundle": bundle,
            "categories": categories
        }
    })


@app.route("/api/checkout", methods=["POST"])
def execute_checkout():
    data = request.json or {}
    customer_id = data.get("customer_id")
    payment_method = data.get("payment_method", "CREDIT_CARD")
    simulate_fail = bool(data.get("simulate_fail", False))

    if not customer_id:
        return jsonify({"status": "error", "message": "Missing customer_id"}), 400

    result = checkout_cart(customer_id, payment_method=payment_method, simulate_failure=simulate_fail)
    if result["status"] == "SUCCESS":
        return jsonify({"status": "success", "result": result})
    else:
        return jsonify({"status": "error", "result": result}), 400


@app.route("/api/analytics/rules", methods=["GET"])
def get_association_rules():
    try:
        min_conf = float(request.args.get("min_confidence", 0.5))
        min_lift = float(request.args.get("min_lift", 1.5))
        limit = int(request.args.get("limit", 50))
    except (ValueError, TypeError):
        min_conf, min_lift, limit = 0.5, 1.5, 50

    filtered_rules = [
        r for r in recommender.rules 
        if r["confidence"] >= min_conf and r["lift"] >= min_lift
    ]
    return jsonify({
        "status": "success",
        "total_rules": len(filtered_rules),
        "rules": filtered_rules[:limit]
    })


@app.route("/api/analytics/view/<view_name>", methods=["GET"])
def get_dbms_view(view_name):
    allowed_views = {
        "v_market_basket": "SELECT * FROM v_market_basket LIMIT 25;",
        "v_customer_purchase_summary": "SELECT * FROM v_customer_purchase_summary LIMIT 25;",
        "v_product_performance": "SELECT * FROM v_product_performance ORDER BY units_sold DESC LIMIT 25;",
        "v_frequent_product_pairs": "SELECT * FROM v_frequent_product_pairs LIMIT 25;"
    }
    if view_name not in allowed_views:
        return jsonify({"status": "error", "message": f"View {view_name} not recognized."}), 404

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(allowed_views[view_name])
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    data = [dict(zip(columns, r)) for r in rows]
    return jsonify({"status": "success", "columns": columns, "data": data})


@app.route("/api/sql/execute", methods=["POST"])
def execute_raw_sql():
    """Live SQL Query runner restricted to read-only queries for student/examiner demo."""
    data = request.json or {}
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"status": "error", "message": "Query string is empty"}), 400

    # Clean trailing semicolon if present
    stripped_query = query.rstrip(";").strip()
    if ";" in stripped_query:
        return jsonify({"status": "error", "message": "Multiple statements are not permitted in the live runner."}), 400

    # Safety check: allow read-only query types only
    first_word = stripped_query.split()[0].upper()
    if first_word not in ("SELECT", "EXPLAIN", "PRAGMA", "WITH"):
        return jsonify({"status": "error", "message": "Only read-only queries (SELECT, EXPLAIN, PRAGMA) are allowed in the live runner."}), 400

    # Disallow destructive/modification keywords anywhere in query
    upper_query = stripped_query.upper()
    disallowed_keywords = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "CREATE ", "ATTACH ", "DETACH ", "REINDEX ", "VACUUM "]
    for kw in disallowed_keywords:
        if kw in upper_query:
            return jsonify({"status": "error", "message": f"Write/DDL command '{kw.strip()}' is strictly prohibited."}), 400

    conn = None
    try:
        # Enforce read-only connection at SQLite engine level
        db_uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)

        # 3-second progress handler timeout to prevent long-running queries from hanging the server
        start_time = time.time()
        def progress_handler():
            if time.time() - start_time > 3.0:
                return 1  # Abort query execution
            return 0

        conn.set_progress_handler(progress_handler, 1000)

        cursor = conn.cursor()
        cursor.execute(stripped_query)
        columns = [col[0] for col in cursor.description] if cursor.description else []

        # Safe bounded fetch: fetch at most 101 rows to prevent memory exhaustion on massive joins
        raw_rows = cursor.fetchmany(101)
        has_more = len(raw_rows) > 100
        display_rows = raw_rows[:100]

        formatted_rows = [dict(zip(columns, r)) for r in display_rows]
        return jsonify({
            "status": "success",
            "columns": columns,
            "row_count": len(formatted_rows),
            "has_more": has_more,
            "rows": formatted_rows
        })
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e).lower():
            return jsonify({"status": "error", "message": "Query execution timed out (exceeded 3.0 seconds limit)."}), 400
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("[*] Starting E-Commerce AI Recommender API Server on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
