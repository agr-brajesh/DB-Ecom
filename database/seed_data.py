"""
Seed Data Generator for E-Commerce Database
Populates 8 distinct product domains, 40+ products, 25 customers,
and 150+ realistic orders with statistically robust co-purchase patterns
tailored for Apriori association rule mining and collaborative filtering.
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "ecommerce.db")
SCHEMA_PATH = os.path.join(DB_DIR, "schema.sql")
VIEWS_TRIGGERS_PATH = os.path.join(DB_DIR, "views_triggers.sql")


def execute_sql_file(cursor, filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        sql_content = f.read()
    cursor.executescript(sql_content)


def seed_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[x] Removed existing database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    print("[*] Executing schema.sql...")
    execute_sql_file(cursor, SCHEMA_PATH)

    print("[*] Executing views_triggers.sql...")
    execute_sql_file(cursor, VIEWS_TRIGGERS_PATH)

    # ---------------------------------------------------------
    # 1. CATEGORIES (8 Domains)
    # ---------------------------------------------------------
    categories = [
        ("CAT01", "Computing & Laptops", "Laptops, high-performance peripherals, and productivity accessories"),
        ("CAT02", "Mobile & Audio", "Smartphones, fast chargers, protective cases, and audio gear"),
        ("CAT03", "Gaming Gear", "Consoles, gamepads, gaming headsets, and low-latency cables"),
        ("CAT04", "Photography & Video", "Mirrorless cameras, prime lenses, carbon tripods, and memory"),
        ("CAT05", "Fitness & Wearables", "Smartwatches, replacement straps, scales, and nutrition bottles"),
        ("CAT06", "Home Office Ergonomics", "Standing desks, ergonomic chairs, monitor mounts, and desk mats"),
        ("CAT07", "Specialty Coffee Bar", "Espresso brewers, burr grinders, artisan beans, and barista tools"),
        ("CAT08", "Student & Productivity", "Digital paper tablets, stylus pens, notebooks, and study tools")
    ]
    cursor.executemany(
        "INSERT INTO categories (category_id, category_name, description) VALUES (?, ?, ?);",
        categories
    )
    print(f"[+] Inserted {len(categories)} categories across 8 domains.")

    # ---------------------------------------------------------
    # 2. PRODUCTS (40+ Products across the 8 Categories)
    # ---------------------------------------------------------
    products = [
        # CAT01: Computing & Laptops
        ("P101", "CAT01", "UltraBook Pro 15-inch Laptop", "Zenith", 1299.99, 150, "High performance Intel Core i7 laptop with 16GB RAM and 512GB SSD"),
        ("P102", "CAT01", "Ergonomic Wireless Mouse", "LogiTech", 39.99, 300, "Precision 2.4GHz wireless optical mouse with quiet click and ergonomic contour"),
        ("P103", "CAT01", "RGB Mechanical Keyboard", "KeyPro", 89.99, 200, "Tactile blue switches, custom RGB lighting, and braided detachable cable"),
        ("P104", "CAT01", "Multi-Port USB-C Hub", "AnkerTech", 49.99, 250, "7-in-1 hub with 4K HDMI, 100W PD charging, 3x USB 3.0, and SD reader"),
        ("P105", "CAT01", "Waterproof Padded Laptop Sleeve", "CaseLogic", 29.99, 250, "Shockproof protective sleeve with fleece lining and zipper accessory pocket"),
        ("P106", "CAT01", "27-inch 4K UHD Monitor", "UltraView", 349.99, 100, "IPS panel with HDR400, USB-C connectivity, and height adjustable stand"),

        # CAT02: Mobile & Audio
        ("P201", "CAT02", "Flagship 5G Smartphone", "NovaTech", 899.99, 180, "6.7-inch OLED 120Hz display, 256GB storage, and triple-lens camera system"),
        ("P202", "CAT02", "65W GaN Fast Charger", "PowerGen", 34.99, 350, "Ultra-compact Gallium Nitride dual USB-C rapid charger for phone and laptop"),
        ("P203", "CAT02", "9H Tempered Glass Screen Protector", "ArmorShield", 14.99, 500, "Anti-scratch, fingerprint resistant 2-pack screen protector with easy align tray"),
        ("P204", "CAT02", "Shockproof Slim Silicone Case", "ArmorShield", 24.99, 400, "Military-grade drop-tested silicone case with microfiber interior lining"),
        ("P205", "CAT02", "Noise-Cancelling Wireless Earbuds", "SoundPulse", 149.99, 220, "Active noise cancelling, 30-hour total battery, and transparency mode"),
        ("P206", "CAT02", "Magnetic 10000mAh Power Bank", "PowerGen", 45.99, 250, "Slim wireless portable battery with strong magnetic attachment"),

        # CAT03: Gaming Gear
        ("P301", "CAT03", "Next-Gen Gaming Console", "PlayCore", 499.99, 120, "1TB SSD 4K gaming system with ray tracing and ultra-high speed loading"),
        ("P302", "CAT03", "Wireless Pro Gamepad Controller", "PlayCore", 69.99, 300, "Haptic feedback, adaptive triggers, and textured rubberized grips"),
        ("P303", "CAT03", "Surround Sound Gaming Headset", "HyperAudio", 79.99, 200, "50mm neodymium drivers, detachable noise-cancelling boom mic, and memory foam pads"),
        ("P304", "CAT03", "Dual Controller Charging Dock", "PowerGen", 29.99, 250, "Fast magnetic drop-and-charge cradle with LED charge indicators"),
        ("P305", "CAT03", "Ultra High Speed HDMI 2.1 Cable", "WirePro", 19.99, 350, "Braided 8K@60Hz / 4K@120Hz 48Gbps high-bandwidth gaming cable"),
        ("P306", "CAT03", "RGB Extended Gaming Mousepad", "KeyPro", 24.99, 300, "Extra large 900x400mm waterproof micro-textured cloth pad with 14 RGB modes"),

        # CAT04: Photography & Video
        ("P401", "CAT04", "Mirrorless 4K Digital Camera", "Lumina", 1199.00, 80, "24.2MP full-frame sensor with 4K60p video and in-body 5-axis image stabilization"),
        ("P402", "CAT04", "50mm f/1.8 Prime Portrait Lens", "Lumina", 179.99, 150, "Fast aperture standard prime lens delivering creamy bokeh and edge-to-edge sharpness"),
        ("P403", "CAT04", "Carbon Fiber Travel Tripod", "SteadyCam", 89.99, 180, "Lightweight 1.2kg tripod with 360-degree panoramic ball head and quick-release plate"),
        ("P404", "CAT04", "128GB High-Speed V30 SD Card", "DataPro", 39.99, 450, "UHS-I U3 Read speeds up to 170MB/s, ideal for 4K video recording"),
        ("P405", "CAT04", "Weatherproof Camera Backpack", "TrailGear", 69.99, 160, "Customizable modular dividers with waterproof rain cover and laptop compartment"),
        ("P406", "CAT04", "Rechargeable Bi-Color LED Video Light", "Lumina", 49.99, 200, "CRI 96+ dimmable video panel with cold shoe mount and digital display"),

        # CAT05: Fitness, Health & Wearables
        ("P501", "CAT05", "GPS Smart Sports Watch", "AeroTrack", 249.99, 190, "Built-in GPS, heart-rate/SpO2 tracking, 7-day battery, and 50m water resistance"),
        ("P502", "CAT05", "Breathable Silicone Sport Strap", "AeroTrack", 19.99, 400, "Sweat-resistant quick release replacement band with stainless pin buckle"),
        ("P503", "CAT05", "Smart Body Composition Scale", "FitMetrics", 59.99, 210, "Measures body fat, muscle mass, BMI, and syncs via Bluetooth to mobile app"),
        ("P504", "CAT05", "100% Whey Isolate Protein (2kg)", "NutriPure", 64.99, 280, "Ultra-filtered vanilla whey isolate powder with 27g protein per scoop"),
        ("P505", "CAT05", "Insulated Stainless Shaker Bottle", "HydroPro", 22.99, 320, "24oz odor-resistant vacuum insulated shaker cup with silent blender ball"),
        ("P506", "CAT05", "Heavy Duty Resistance Exercise Bands", "FitMetrics", 25.99, 250, "Set of 5 color-coded natural latex loop bands with carrying pouch"),

        # CAT06: Home Office & Ergonomics
        ("P601", "CAT06", "Dual-Motor Electric Standing Desk", "ErgoWork", 399.99, 90, "Height-adjustable 55x28 inch desk with 4 memory presets and anti-collision sensor"),
        ("P602", "CAT06", "Ergonomic High-Back Mesh Chair", "ErgoWork", 279.99, 110, "Breathable mesh back with adjustable 3D lumbar support and reclining tilt"),
        ("P603", "CAT06", "Heavy-Duty Dual Monitor Arm Mount", "ErgoWork", 59.99, 180, "Gas spring articulating desk clamp mount fitting screens 17 to 32 inches"),
        ("P604", "CAT06", "Merino Wool Felt Desk Mat (90x40cm)", "CraftDesk", 32.99, 260, "Anti-slip natural wool felt pad providing wrist cushion and desk protection"),
        ("P605", "CAT06", "ScreenBar Monitor Light Bar", "LightCraft", 49.99, 220, "Auto-dimming eye care e-reading LED desk lamp with zero screen glare"),

        # CAT07: Specialty Coffee Bar
        ("P701", "CAT07", "Compact 15-Bar Espresso Machine", "BaristaPro", 299.99, 100, "Italian pump espresso maker with manual steam wand and thermo-block heating"),
        ("P702", "CAT07", "Electric Conical Burr Coffee Grinder", "BaristaPro", 89.99, 140, "30 precise grind settings for espresso, drip, and French press"),
        ("P703", "CAT07", "Single-Origin Whole Bean Coffee (1kg)", "RoastMaster", 18.99, 350, "Ethically sourced Ethiopian Yirgacheffe medium roast with floral notes"),
        ("P704", "CAT07", "Stainless Steel Milk Frothing Pitcher", "BaristaPro", 16.99, 300, "12oz 350ml calibrated steaming pitcher with precision pour spout"),
        ("P705", "CAT07", "Digital Precision Coffee Timer Scale", "BrewLogic", 29.99, 240, "0.1g accuracy scale with built-in auto timer for pourover and espresso"),

        # CAT08: Student Essentials & Productivity
        ("P801", "CAT08", "10.3-inch Digital Paper E-Reader Tablet", "PaperLite", 329.99, 130, "Anti-glare E-Ink notebook for distraction-free reading, note-taking, and PDF annotating"),
        ("P802", "CAT08", "Pressure-Sensitive Digital Stylus", "PaperLite", 49.99, 260, "4096 pressure levels, tilt recognition, and eraser button without charging needed"),
        ("P803", "CAT08", "Replacement Stylus Felt Nibs (5-Pack)", "PaperLite", 14.99, 380, "Paper-like textured friction tips for natural pencil-on-paper feeling"),
        ("P804", "CAT08", "Premium Dotted Hardcover Journal", "CraftDesk", 19.99, 310, "160gsm bleed-proof bamboo paper notebook with elastic band and inner pocket"),
        ("P805", "CAT08", "Pastel Dual-Tip Highlighters (6-Pack)", "ColorFlow", 12.99, 450, "Chisel and fine bullet tip mild aesthetic pastel water-based markers")
    ]

    cursor.executemany(
        """INSERT INTO products 
           (product_id, category_id, product_name, brand, price, stock_quantity, description) 
           VALUES (?, ?, ?, ?, ?, ?, ?);""",
        products
    )
    print(f"[+] Inserted {len(products)} products across 8 categories.")

    # ---------------------------------------------------------
    # 3. CUSTOMERS (25 Customers)
    # ---------------------------------------------------------
    customers = [
        ("C101", "Alex Rivera", "alex.rivera@example.com", "555-0101", "Seattle"),
        ("C102", "Samantha Hayes", "sam.hayes@example.com", "555-0102", "San Francisco"),
        ("C103", "Marcus Chen", "marcus.chen@example.com", "555-0103", "Austin"),
        ("C104", "Elena Rostova", "elena.r@example.com", "555-0104", "New York"),
        ("C105", "David Kim", "david.kim@example.com", "555-0105", "Chicago"),
        ("C106", "Chloe Bennett", "chloe.b@example.com", "555-0106", "Denver"),
        ("C107", "Julian Vance", "julian.v@example.com", "555-0107", "Portland"),
        ("C108", "Aria Patel", "aria.patel@example.com", "555-0108", "Boston"),
        ("C109", "Liam O'Connor", "liam.oc@example.com", "555-0109", "San Diego"),
        ("C110", "Sophia Martinez", "sophia.m@example.com", "555-0110", "Miami"),
        ("C111", "Lucas Becker", "lucas.b@example.com", "555-0111", "Atlanta"),
        ("C112", "Zoe Washington", "zoe.w@example.com", "555-0112", "Washington DC"),
        ("C113", "Ethan Wright", "ethan.w@example.com", "555-0113", "Dallas"),
        ("C114", "Maya Lin", "maya.lin@example.com", "555-0114", "Minneapolis"),
        ("C115", "Noah Scott", "noah.scott@example.com", "555-0115", "Philadelphia"),
        ("C116", "Isabella Ross", "isabella.r@example.com", "555-0116", "Phoenix"),
        ("C117", "Oliver King", "oliver.k@example.com", "555-0117", "Charlotte"),
        ("C118", "Ava Morales", "ava.m@example.com", "555-0118", "San Jose"),
        ("C119", "Jackson Taylor", "jackson.t@example.com", "555-0119", "Nashville"),
        ("C120", "Emma Clark", "emma.c@example.com", "555-0120", "Columbus"),
        ("C121", "William Davies", "william.d@example.com", "555-0121", "Indianapolis"),
        ("C122", "Grace Miller", "grace.m@example.com", "555-0122", "Salt Lake City"),
        ("C123", "Benjamin Hall", "ben.hall@example.com", "555-0123", "Kansas City"),
        ("C124", "Harper Lee", "harper.lee@example.com", "555-0124", "Raleigh"),
        ("C125", "Daniel Adams", "daniel.a@example.com", "555-0125", "Pittsburgh")
    ]
    cursor.executemany(
        "INSERT INTO customers (customer_id, name, email, phone, city) VALUES (?, ?, ?, ?, ?);",
        customers
    )
    print(f"[+] Inserted {len(customers)} customers.")

    # Price lookup map for fast order calculation
    price_map = {p[0]: p[4] for p in products}

    # ---------------------------------------------------------
    # 4. ORDERS & ORDER_ITEMS (150+ Transactions with Embedded Patterns)
    # ---------------------------------------------------------
    # Patterns for the 8 Domains:
    # 1. Computing: [P101 (Laptop), P102 (Mouse), P103 (Keyboard)] -> P104 (USB Hub), P105 (Sleeve)
    # 2. Mobile: [P201 (Phone), P204 (Case)] -> P203 (Screen Protector), P202 (Fast Charger)
    # 3. Gaming: [P301 (Console), P302 (Controller)] -> P304 (Charging Dock), P305 (HDMI 2.1)
    # 4. Photo: [P401 (Camera), P402 (50mm Lens)] -> P404 (SD Card), P405 (Backpack)
    # 5. Fitness: [P501 (Watch)] -> P502 (Strap), P503 (Scale); [P504 (Protein)] -> P505 (Shaker)
    # 6. Ergonomics: [P601 (Desk), P602 (Chair)] -> P604 (Desk Mat), P603 (Arm Mount)
    # 7. Coffee: [P701 (Espresso), P703 (Beans)] -> P704 (Pitcher), P705 (Scale)
    # 8. Student: [P801 (Tablet), P802 (Stylus)] -> P803 (Nibs), P804 (Journal)

    domain_baskets = {
        "comp_full": ["P101", "P102", "P103", "P104", "P105"],
        "comp_core": ["P101", "P102", "P105"],
        "comp_hub": ["P101", "P104"],
        "comp_mouse_key": ["P102", "P103"],
        
        "mob_full": ["P201", "P204", "P203", "P202"],
        "mob_prot": ["P201", "P204", "P203"],
        "mob_power": ["P201", "P202", "P206"],
        "mob_audio": ["P201", "P205"],
        
        "gam_full": ["P301", "P302", "P304", "P305"],
        "gam_audio": ["P301", "P303", "P305"],
        "gam_extra": ["P302", "P304"],
        "gam_desk": ["P303", "P306"],
        
        "photo_full": ["P401", "P402", "P404", "P405"],
        "photo_tripod": ["P401", "P403", "P404"],
        "photo_starter": ["P401", "P402", "P404"],
        "photo_acc": ["P404", "P405"],
        
        "fit_watch_combo": ["P501", "P502", "P503"],
        "fit_nutrition": ["P504", "P505", "P506"],
        "fit_watch_alone": ["P501", "P502"],
        
        "ergo_full": ["P601", "P602", "P604"],
        "ergo_mount": ["P601", "P603", "P605"],
        "ergo_chair_mat": ["P602", "P604"],
        
        "coffee_full": ["P701", "P702", "P703", "P704", "P705"],
        "coffee_starter": ["P701", "P703", "P704"],
        "coffee_grind": ["P702", "P703", "P705"],
        
        "study_full": ["P801", "P802", "P803", "P804"],
        "study_nibs": ["P801", "P802", "P803"],
        "study_notes": ["P804", "P805"],
        "study_pen": ["P801", "P802"]
    }

    # Generate distinct orders
    order_id_counter = 1000
    payment_id_counter = 5000
    payment_methods = ['CREDIT_CARD', 'DEBIT_CARD', 'UPI', 'NET_BANKING']
    
    # We will generate 160 orders ensuring every domain has at least 15-20 co-purchase transactions
    random.seed(42)  # Deterministic seed for reproducible evaluation
    start_date = datetime.now() - timedelta(days=90)

    all_orders = []
    all_order_items = []
    all_payments = []

    # Assign showcase customers their designated historical orders
    showcase_profiles = [
        ("C101", ["P101", "P102", "P103"]),         # Computing buyer: Laptop + Mouse + Keyboard
        ("C102", ["P201", "P204"]),                 # Mobile buyer: Phone + Case
        ("C103", ["P301", "P302"]),                 # Gamer: Console + Controller
        ("C104", ["P401", "P402"]),                 # Photographer: Camera + 50mm Lens
        ("C105", ["P501"]),                         # Fitness: Smart Watch
        ("C106", ["P601", "P602"]),                 # Home Office: Desk + Chair
        ("C107", ["P701", "P703"]),                 # Coffee Lover: Espresso Machine + Beans
        ("C108", ["P801", "P802"])                  # Student: Digital Tablet + Stylus
    ]

    for cust_id, p_list in showcase_profiles:
        order_id_counter += 1
        payment_id_counter += 1
        oid = f"ORD{order_id_counter}"
        pid = f"PAY{payment_id_counter}"
        odate = (start_date + timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d %H:%M:%S")
        total = sum(price_map[p] for p in p_list)
        all_orders.append((oid, cust_id, odate, round(total, 2), "COMPLETED"))
        all_payments.append((pid, oid, "CREDIT_CARD", "SUCCESS", odate, round(total, 2)))
        for p in p_list:
            all_order_items.append((oid, p, 1, price_map[p]))

    # Now generate recurring pattern transactions to build statistical Apriori Support & Confidence
    pattern_keys = list(domain_baskets.keys())
    # Frequencies to weight baskets realistically
    pattern_weights = [
        12, 14, 10, 8,    # Computing patterns
        15, 12, 10, 8,    # Mobile patterns
        14, 10, 8, 8,     # Gaming patterns
        12, 10, 12, 8,    # Photography patterns
        12, 10, 8,        # Fitness patterns
        10, 8, 8,         # Ergonomics patterns
        12, 10, 8,        # Coffee patterns
        12, 10, 8, 8      # Study patterns
    ]

    for p_idx, p_key in enumerate(pattern_keys):
        repeat_count = pattern_weights[p_idx]
        basket_items = domain_baskets[p_key]
        for _ in range(repeat_count):
            order_id_counter += 1
            payment_id_counter += 1
            oid = f"ORD{order_id_counter}"
            pid = f"PAY{payment_id_counter}"
            # Use customers C109-C125 for random pattern aggregation to keep C101-C108 pristine showcase profiles
            cust_id = f"C{random.randint(109, 125)}"
            days_offset = random.randint(10, 85)
            odate = (start_date + timedelta(days=days_offset, minutes=random.randint(10, 500))).strftime("%Y-%m-%d %H:%M:%S")
            
            # Select 1 to all items from the basket pattern
            chosen_items = list(basket_items)
            # occasionally add a random impulse accessory from other categories (realistic noise)
            if random.random() < 0.15:
                random_extra = random.choice(["P104", "P202", "P305", "P805", "P505"])
                if random_extra not in chosen_items:
                    chosen_items.append(random_extra)

            method = random.choice(payment_methods)
            order_items_this_order = []
            total = 0.0
            for item in chosen_items:
                qty = 1 if price_map[item] > 100 else random.choice([1, 1, 2])
                order_items_this_order.append((oid, item, qty, price_map[item]))
                total += qty * price_map[item]

            all_order_items.extend(order_items_this_order)
            all_orders.append((oid, cust_id, odate, round(total, 2), "COMPLETED"))
            all_payments.append((pid, oid, method, "SUCCESS", odate, round(total, 2)))

    # Insert Orders
    cursor.executemany(
        "INSERT INTO orders (order_id, customer_id, order_date, total_amount, order_status) VALUES (?, ?, ?, ?, ?);",
        all_orders
    )
    # Insert Order Items
    cursor.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?);",
        all_order_items
    )
    # Insert Payments
    cursor.executemany(
        "INSERT INTO payments (payment_id, order_id, payment_method, payment_status, payment_date, amount) VALUES (?, ?, ?, ?, ?, ?);",
        all_payments
    )
    print(f"[+] Inserted {len(all_orders)} completed orders and {len(all_order_items)} order items.")

    # ---------------------------------------------------------
    # 5. REVIEWS (Product Ratings & Comments for Collaborative Filtering)
    # ---------------------------------------------------------
    reviews_data = []
    review_comments = {
        5: ["Exceeded all my expectations! Build quality and performance are top tier.", "Best purchase I've made all year. Highly recommend!", "Flawless performance and arrived very quickly."],
        4: ["Really good value for money. Minor learning curve but works great.", "Solid build and performs well. Good battery life.", "Very satisfied with this product."],
        3: ["Decent overall, does what it says on the box.", "Average quality, could have better instructions."],
        2: ["Had higher expectations. Feels a bit overpriced for what you get.", "Works okay, but had some minor connectivity glitches."]
    }

    # Generate reviews from various customers across products
    for p in products:
        pid = p[0]
        # 3 to 6 reviews per product
        num_reviews = random.randint(3, 6)
        reviewers = random.sample(customers, num_reviews)
        for r_cust in reviewers:
            cid = r_cust[0]
            rating = random.choices([5, 4, 3, 2], weights=[50, 35, 10, 5])[0]
            comment = random.choice(review_comments[rating])
            rev_date = (start_date + timedelta(days=random.randint(15, 88))).strftime("%Y-%m-%d %H:%M:%S")
            reviews_data.append((cid, pid, rating, comment, rev_date))

    cursor.executemany(
        "INSERT INTO reviews (customer_id, product_id, rating, comment, review_date) VALUES (?, ?, ?, ?, ?);",
        reviews_data
    )
    print(f"[+] Inserted {len(reviews_data)} product reviews.")

    # ---------------------------------------------------------
    # 6. SHOPPING CARTS (Active Carts to simulate live recommendation)
    # ---------------------------------------------------------
    # Add active items to showcase customers' carts to test instant recommendation!
    carts_data = [
        # Customer C101 has Laptop in cart (or wants accessory)
        ("C101", "P101", 1),   # Laptop in cart
        ("C102", "P201", 1),   # 5G Phone in cart
        ("C103", "P301", 1),   # Gaming Console in cart
        ("C104", "P401", 1),   # Mirrorless camera in cart
        ("C105", "P501", 1),   # Sports watch in cart
        ("C106", "P601", 1),   # Standing desk in cart
        ("C107", "P701", 1),   # Espresso machine in cart
        ("C108", "P801", 1),   # E-reader tablet in cart
    ]
    cursor.executemany(
        "INSERT INTO shopping_cart (customer_id, product_id, quantity) VALUES (?, ?, ?);",
        carts_data
    )
    print(f"[+] Seeded {len(carts_data)} active shopping cart entries.")

    # ---------------------------------------------------------
    # 7. SEARCH HISTORY (Customer query logs for content/intent matching)
    # ---------------------------------------------------------
    search_queries = [
        ("C101", "ergonomic laptop backpack sleeve"),
        ("C101", "multiport usb-c adapter 4k"),
        ("C102", "fast wireless charger for phone"),
        ("C102", "tempered glass screen protector"),
        ("C103", "wireless controller charging dock"),
        ("C103", "ultra high speed hdmi cable 120hz"),
        ("C104", "fast 128gb v30 sd card for 4k"),
        ("C104", "camera travel backpack water resistant"),
        ("C105", "silicone sport watch strap 20mm"),
        ("C105", "bluetooth body fat scale app"),
        ("C106", "felt desk pad wool mat"),
        ("C106", "dual monitor desk arm"),
        ("C107", "milk frothing pitcher stainless"),
        ("C107", "fresh roasted whole bean coffee"),
        ("C108", "stylus replacement felt nibs"),
        ("C108", "dotted hardcover journal notebook")
    ]
    cursor.executemany(
        "INSERT INTO search_history (customer_id, search_query) VALUES (?, ?);",
        search_queries
    )
    print(f"[+] Seeded {len(search_queries)} search history records.")

    conn.commit()
    conn.close()
    print("[OK] Database seed complete! SQLite database saved to:", DB_PATH)


if __name__ == "__main__":
    seed_database()
