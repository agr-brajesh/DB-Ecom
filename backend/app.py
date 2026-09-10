"""
Flask REST API Server for AI-Based E-Commerce Project
Exposes endpoints for Storefront, Recommendations, Cart,
ACID Transactions, Apriori Analytics, and Live SQL Runner.
"""

import os
import sys
import sqlite3
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add root directory to sys.path so we can import from database and ai
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ai.recommender import ProductRecommender
from database.transactions import checkout_cart, get_db_connection

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "frontend"), static_url_path="")
CORS(app)

DB_PATH = os.path.join(BASE_DIR, "database", "ecommerce.db")
recommender = ProductRecommender(DB_PATH)


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


@app.route("/api/recommendations/<customer_id>", methods=["GET"])
def get_recommendations(customer_id):
    top_n = int(request.args.get("top_n", 4))
    res = recommender.recommend(customer_id, top_n=top_n)
    if "error" in res:
        return jsonify({"status": "error", "message": res["error"]}), 404
    return jsonify({"status": "success", "data": res})


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
    quantity = int(data.get("quantity", 1))

    if not customer_id or not product_id:
        return jsonify({"status": "error", "message": "Missing customer_id or product_id"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check stock
    cursor.execute("SELECT stock_quantity, product_name FROM products WHERE product_id = ?;", (product_id,))
    prod = cursor.fetchone()
    if not prod:
        conn.close()
        return jsonify({"status": "error", "message": "Product not found"}), 404

    if prod[0] < quantity:
        conn.close()
        return jsonify({"status": "error", "message": f"Only {prod[0]} in stock for {prod[1]}"}), 400

    # Upsert into cart
    cursor.execute("""
        INSERT INTO shopping_cart (customer_id, product_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(customer_id, product_id) 
        DO UPDATE SET quantity = quantity + excluded.quantity;
    """, (customer_id, product_id, quantity))

    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Added {prod[1]} to cart."})


@app.route("/api/cart/remove", methods=["POST"])
def remove_from_cart():
    data = request.json or {}
    customer_id = data.get("customer_id")
    product_id = data.get("product_id")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shopping_cart WHERE customer_id = ? AND product_id = ?;", (customer_id, product_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Item removed from cart."})


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
    min_conf = float(request.args.get("min_confidence", 0.5))
    min_lift = float(request.args.get("min_lift", 1.5))
    limit = int(request.args.get("limit", 50))

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

    # Safety check: allow SELECT / EXPLAIN only
    first_word = query.split()[0].upper()
    if first_word not in ("SELECT", "EXPLAIN", "PRAGMA", "WITH"):
        return jsonify({"status": "error", "message": "Only read-only queries (SELECT, EXPLAIN, PRAGMA) are allowed in the live runner."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        conn.close()

        formatted_rows = [dict(zip(columns, r)) for r in rows]
        return jsonify({
            "status": "success",
            "columns": columns,
            "row_count": len(formatted_rows),
            "rows": formatted_rows[:100]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    print("[*] Starting E-Commerce AI Recommender API Server on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
