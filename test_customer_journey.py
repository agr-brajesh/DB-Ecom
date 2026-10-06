import requests
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_full_customer_journey():
    print("=== STARTING FULL CUSTOMER JOURNEY TEST ===")
    
    # 1. BROWSE PRODUCTS & CATEGORIES
    r = requests.get(f"{BASE_URL}/api/products")
    assert r.status_code == 200, f"Products failed: {r.status_code}"
    products = r.json().get("products", [])
    assert len(products) > 0, "No products returned"
    print(f"[STEP 1: Browse] Loaded {len(products)} products from catalogue.")
    
    # Select test customer and test product
    customer_id = "C102" # Priya Sharma
    test_prod = products[0]
    p_id = test_prod["product_id"]
    p_name = test_prod["product_name"]
    initial_stock = test_prod["stock_quantity"]
    price = test_prod["price"]
    print(f"Selected Test Customer: {customer_id}, Product: {p_id} ({p_name}), Initial Stock: {initial_stock}, Price: ${price}")

    # 2. SEARCH & SUGGESTIONS
    term = p_name[:4]
    r = requests.get(f"{BASE_URL}/api/search/suggestions?q={term}")
    assert r.status_code == 200
    sugg = r.json()
    assert sugg.get("status") == "success"
    print(f"[STEP 2: Search] Query '{term}' returned {len(sugg.get('suggestions', []))} suggestions.")
    
    # Record search history
    r = requests.post(f"{BASE_URL}/api/search/record", json={"customer_id": customer_id, "query": term})
    assert r.status_code == 200
    print(f"[STEP 2: Search] Recorded search query into search_history table.")

    # 3. PRODUCT DETAILS & REVIEWS
    r = requests.get(f"{BASE_URL}/api/product/{p_id}")
    assert r.status_code == 200
    p_detail = r.json()
    assert p_detail.get("product", {}).get("product_id") == p_id
    reviews = p_detail.get("reviews", [])
    print(f"[STEP 3: Product Details] Fetched details for {p_id} with {len(reviews)} reviews.")

    # 4. WISHLIST TOGGLE (ADD & VERIFY)
    r = requests.post(f"{BASE_URL}/api/wishlist/toggle", json={"customer_id": customer_id, "product_id": p_id})
    assert r.status_code == 200
    w_res = r.json()
    print(f"[STEP 4: Wishlist] Toggle result: {w_res.get('action')} (in_wishlist={w_res.get('in_wishlist')})")
    
    # If it was already in wishlist and toggled off, toggle it back on
    if not w_res.get("in_wishlist"):
        r = requests.post(f"{BASE_URL}/api/wishlist/toggle", json={"customer_id": customer_id, "product_id": p_id})
        w_res = r.json()
        print(f"[STEP 4: Wishlist] Toggled back on: in_wishlist={w_res.get('in_wishlist')}")
    
    r = requests.get(f"{BASE_URL}/api/wishlist/{customer_id}")
    assert r.status_code == 200
    w_items = r.json().get("wishlist", [])
    assert any(item["product_id"] == p_id for item in w_items), "Product not found in wishlist"
    print(f"[STEP 4: Wishlist] Verified {p_id} is persistent in customer's wishlist (total items: {len(w_items)}).")

    # 5. CLEAR EXISTING CART (so test is deterministic)
    r = requests.get(f"{BASE_URL}/api/cart/{customer_id}")
    cur_cart = r.json().get("items", [])
    for it in cur_cart:
        requests.post(f"{BASE_URL}/api/cart/remove", json={"customer_id": customer_id, "product_id": it["product_id"]})
    print("[STEP 5: Cart] Cleared existing test cart.")

    # 6. ADD TO CART
    r = requests.post(f"{BASE_URL}/api/cart/add", json={"customer_id": customer_id, "product_id": p_id, "quantity": 1})
    assert r.status_code == 200
    print(f"[STEP 6: Cart] Added 1x {p_id} to cart.")

    # 7. MODIFY QUANTITY WITH STOCK CEILING VALIDATION
    # Update to 2
    r = requests.post(f"{BASE_URL}/api/cart/update", json={"customer_id": customer_id, "product_id": p_id, "quantity": 2})
    assert r.status_code == 200
    u_res = r.json()
    assert u_res.get("quantity") == 2
    print(f"[STEP 7: Cart Update] Incremented quantity to 2, subtotal: ${u_res.get('subtotal')}, cart total: ${u_res.get('cart_total')}.")

    # Test exceeding stock ceiling
    r = requests.post(f"{BASE_URL}/api/cart/update", json={"customer_id": customer_id, "product_id": p_id, "quantity": initial_stock + 100})
    assert r.status_code == 400
    print(f"[STEP 7: Stock Ceiling Validation] Successfully blocked quantity exceeding stock: {r.json().get('error')}")

    # 8. CHECKOUT: TEST SIMULATED FAILURE (ROLLBACK) FIRST
    print("[STEP 8: ACID Rollback] Testing simulated checkout failure...")
    r = requests.post(f"{BASE_URL}/api/checkout", json={"customer_id": customer_id, "payment_method": "UPI", "simulate_fail": True})
    assert r.status_code == 400
    # Verify stock was NOT decremented
    r = requests.get(f"{BASE_URL}/api/product/{p_id}")
    post_fail_stock = r.json().get("product", {}).get("stock_quantity")
    assert post_fail_stock == initial_stock, f"Stock changed on rollback! Expected {initial_stock}, got {post_fail_stock}"
    # Verify cart was NOT cleared
    r = requests.get(f"{BASE_URL}/api/cart/{customer_id}")
    cart_items = r.json().get("items", [])
    assert len(cart_items) == 1 and cart_items[0]["quantity"] == 2, "Cart was cleared or altered on failed checkout!"
    print(f"[STEP 8: ACID Rollback] Verified ROLLBACK: Stock preserved ({post_fail_stock}) and Cart intact.")

    # 9. CHECKOUT: REAL CUSTOMER TRANSACTION (COMMIT)
    print("[STEP 9: Real Checkout (COMMIT)] Executing valid customer checkout...")
    r = requests.post(f"{BASE_URL}/api/checkout", json={"customer_id": customer_id, "payment_method": "UPI", "simulate_fail": False})
    assert r.status_code == 200
    c_res = r.json()
    assert c_res.get("status") == "success"
    order_id = c_res.get("result", {}).get("order_id")
    order_total = c_res.get("result", {}).get("total_amount")
    print(f"[STEP 9: Real Checkout] Successfully placed order {order_id} for ${order_total} via UPI.")

    # 10. VERIFY INVENTORY TRIGGER DECREMENT & CART CLEARED
    r = requests.get(f"{BASE_URL}/api/product/{p_id}")
    post_commit_stock = r.json().get("product", {}).get("stock_quantity")
    expected_stock = initial_stock - 2
    assert post_commit_stock == expected_stock, f"Trigger failed! Expected {expected_stock}, got {post_commit_stock}"
    print(f"[STEP 10: Inventory Trigger] Database trigger trg_decrement_product_stock fired: stock reduced from {initial_stock} -> {post_commit_stock}.")

    r = requests.get(f"{BASE_URL}/api/cart/{customer_id}")
    assert len(r.json().get("items", [])) == 0, "Cart was not cleared after successful checkout!"
    print(f"[STEP 10: Cart Cleared] Customer cart cleared upon order completion.")

    # 11. VERIFY ORDER IN ORDER HISTORY
    r = requests.get(f"{BASE_URL}/api/orders/{customer_id}")
    assert r.status_code == 200
    orders = r.json().get("orders", [])
    assert any(o["order_id"] == order_id for o in orders), f"Order {order_id} not found in customer order history!"
    print(f"[STEP 11: Order History] Order {order_id} verified in customer order history.")

    # 12. VERIFY CUSTOMER PROFILE
    r = requests.get(f"{BASE_URL}/api/profile/{customer_id}")
    assert r.status_code == 200
    prof = r.json().get("profile", {})
    assert prof.get("customer_id") == customer_id
    assert prof.get("total_orders", 0) > 0
    assert prof.get("lifetime_spend", 0) > 0
    assert prof.get("wishlist_count", 0) >= 1
    print(f"[STEP 12: Customer Profile] Profile verified: {prof['total_orders']} orders, ${prof['lifetime_spend']} spend, {prof['wishlist_count']} wishlist items.")

    print("\n=== COMPLETE CUSTOMER JOURNEY TEST PASSED 100% ===")

if __name__ == "__main__":
    test_full_customer_journey()
