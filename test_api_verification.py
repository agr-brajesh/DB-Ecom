import os
import sys
import json
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from backend.app import app

def test_api_suite():
    client = app.test_client()

    print("=== TESTING BACKEND API ENDPOINTS ===")

    # 1. GET /
    res = client.get("/")
    assert res.status_code == 200
    assert b"NexusAI" in res.data
    print("[PASS] GET / (Root Frontend)")

    # 2. GET /api/customers
    res = client.get("/api/customers")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["customers"]) == 25
    print(f"[PASS] GET /api/customers (Count: {len(data['customers'])})")

    # 3. GET /api/products
    res = client.get("/api/products")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["products"]) == 45
    assert len(data["categories"]) == 8
    print(f"[PASS] GET /api/products (Total: {len(data['products'])})")

    # Filtered products by category
    res = client.get("/api/products?category_id=CAT01")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["products"]) == 6
    print(f"[PASS] GET /api/products?category_id=CAT01 (Filtered: {len(data['products'])})")

    # 4. GET /api/recommendations/<customer_id>
    res = client.get("/api/recommendations/C101?top_n=3")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["data"]["recommendations"]) == 3
    print("[PASS] GET /api/recommendations/C101 (Valid customer)")

    # Invalid customer
    res = client.get("/api/recommendations/NON_EXISTENT")
    assert res.status_code == 404
    print("[PASS] GET /api/recommendations/NON_EXISTENT (404 handled)")

    # 5. GET /api/cart/<customer_id>
    res = client.get("/api/cart/C101")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "items" in data
    print(f"[PASS] GET /api/cart/C101 (Items: {len(data['items'])}, Total: ${data['total_amount']})")

    # 6. POST /api/cart/add & POST /api/cart/remove
    # Add item
    res = client.post("/api/cart/add", json={"customer_id": "C101", "product_id": "P106", "quantity": 1})
    assert res.status_code == 200
    # Remove item
    res = client.post("/api/cart/remove", json={"customer_id": "C101", "product_id": "P106"})
    assert res.status_code == 200
    print("[PASS] POST /api/cart/add and /api/cart/remove")

    # 7. POST /api/checkout (simulate fail = rollback verification)
    # First add an item to C101
    client.post("/api/cart/add", json={"customer_id": "C101", "product_id": "P106", "quantity": 1})
    res = client.post("/api/checkout", json={"customer_id": "C101", "simulate_fail": True})
    assert res.status_code == 400
    data = res.get_json()
    assert data["status"] == "error"
    # Cart item should still exist
    cart_res = client.get("/api/cart/C101").get_json()
    assert any(i["product_id"] == "P106" for i in cart_res["items"])
    # Clean up cart item
    client.post("/api/cart/remove", json={"customer_id": "C101", "product_id": "P106"})
    print("[PASS] POST /api/checkout (Rollback verification on simulated failure)")

    # 8. GET /api/analytics/rules
    res = client.get("/api/analytics/rules?min_confidence=0.6&min_lift=2.0&limit=10")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "rules" in data
    print(f"[PASS] GET /api/analytics/rules (Filtered Rules: {len(data['rules'])})")

    # 9. GET /api/analytics/view/<view_name>
    for v in ["v_market_basket", "v_customer_purchase_summary", "v_product_performance", "v_frequent_product_pairs"]:
        res = client.get(f"/api/analytics/view/{v}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert len(data["columns"]) > 0
    print("[PASS] GET /api/analytics/view/<view_name> (All 4 views)")

    # Invalid view name
    res = client.get("/api/analytics/view/non_existent_view")
    assert res.status_code == 404
    print("[PASS] GET /api/analytics/view/invalid (404 handled)")

    # 10. POST /api/sql/execute
    # Valid read-only query
    res = client.post("/api/sql/execute", json={"query": "SELECT category_id, category_name FROM categories ORDER BY category_id;"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["row_count"] == 8
    print(f"[PASS] POST /api/sql/execute (Valid SELECT returned {data['row_count']} rows)")

    # Security Test: Piggyback SQL injection with semicolon
    res = client.post("/api/sql/execute", json={"query": "SELECT 1; DROP TABLE categories;"})
    assert res.status_code == 400
    assert "Multiple statements" in res.get_json()["message"]
    print("[PASS] POST /api/sql/execute (Blocked semicolon chained statements)")

    # Security Test: With CTE + Delete injection
    res = client.post("/api/sql/execute", json={"query": "WITH x AS (SELECT 1) DELETE FROM categories;"})
    assert res.status_code == 400
    assert "strictly prohibited" in res.get_json()["message"]
    print("[PASS] POST /api/sql/execute (Blocked CTE DELETE statement)")

    # Robustness Test: Invalid cart add quantity
    res = client.post("/api/cart/add", json={"customer_id": "C101", "product_id": "P101", "quantity": 0})
    assert res.status_code == 400
    assert "Quantity must be greater than 0" in res.get_json()["message"]
    print("[PASS] POST /api/cart/add (Rejected zero/negative quantity)")

    # Robustness Test: Invalid top_n query param
    res = client.get("/api/recommendations/C101?top_n=invalid_str")
    assert res.status_code == 200
    print("[PASS] GET /api/recommendations/C101?top_n=invalid_str (Defaulted safely)")

    # Robustness Test: Invalid rules slider parameters
    res = client.get("/api/analytics/rules?min_confidence=invalid&min_lift=bad")
    assert res.status_code == 200
    print("[PASS] GET /api/analytics/rules with invalid params (Handled gracefully)")

    # 11. GET /api/product/<product_id>
    res = client.get("/api/product/P101")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["product"]["product_id"] == "P101"
    assert "reviews" in data["product"]
    assert "frequently_bought" in data["product"]
    assert "similar_products" in data["product"]
    print(f"[PASS] GET /api/product/P101 (Details loaded with {len(data['product']['reviews'])} reviews)")

    # 12. GET /api/orders/<customer_id>
    res = client.get("/api/orders/C101")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["orders"]) > 0
    assert "items" in data["orders"][0]
    print(f"[PASS] GET /api/orders/C101 (Found {len(data['orders'])} past orders)")

    # 13. GET /api/admin/overview
    res = client.get("/api/admin/overview")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "gross_revenue" in data["overview"]
    assert "top_products" in data["overview"]
    assert "category_sales" in data["overview"]
    print(f"[PASS] GET /api/admin/overview (Gross Revenue: ${data['overview']['gross_revenue']:.2f}, Orders: {data['overview']['total_orders']})")

    print("\n=== ALL API ENDPOINTS, NEW COMMERCE ROUTES, AND SECURITY TESTS VERIFIED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_api_suite()
