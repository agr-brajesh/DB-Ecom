-- ==========================================================
-- SUPABASE POSTGRESQL SCHEMA & SEED MIGRATION
-- Project: NexusAI E-Commerce Database with Product Recommendation
-- Target: Supabase PostgreSQL (Public Schema)
-- ==========================================================

-- Clean up existing objects if re-running
DROP VIEW IF EXISTS v_frequent_product_pairs CASCADE;
DROP VIEW IF EXISTS v_product_performance CASCADE;
DROP VIEW IF EXISTS v_customer_purchase_summary CASCADE;
DROP VIEW IF EXISTS v_market_basket CASCADE;

DROP TABLE IF EXISTS search_history CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS shopping_cart CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- ==========================================================
-- 1. TABLES CREATION (3NF Normalized)
-- ==========================================================

-- 1. Categories
CREATE TABLE categories (
    category_id VARCHAR(10) PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Products
CREATE TABLE products (
    product_id VARCHAR(10) PRIMARY KEY,
    category_id VARCHAR(10) NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    product_name VARCHAR(150) NOT NULL,
    brand VARCHAR(100),
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    stock_quantity INT NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Customers
CREATE TABLE customers (
    customer_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20),
    city VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. Orders
CREATE TABLE orders (
    order_id VARCHAR(15) PRIMARY KEY,
    customer_id VARCHAR(10) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    order_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (total_amount >= 0),
    order_status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED' 
        CHECK (order_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'CANCELLED'))
);

-- 5. Order Items
CREATE TABLE order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(15) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id VARCHAR(10) NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    UNIQUE(order_id, product_id)
);

-- 6. Payments
CREATE TABLE payments (
    payment_id VARCHAR(15) PRIMARY KEY,
    order_id VARCHAR(15) NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
    payment_method VARCHAR(50) NOT NULL 
        CHECK (payment_method IN ('CREDIT_CARD', 'DEBIT_CARD', 'UPI', 'NET_BANKING', 'CASH_ON_DELIVERY')),
    payment_status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS' 
        CHECK (payment_status IN ('SUCCESS', 'PENDING', 'FAILED')),
    payment_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0)
);

-- 7. Shopping Cart
CREATE TABLE shopping_cart (
    cart_id BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(10) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    product_id VARCHAR(10) NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, product_id)
);

-- 8. Reviews
CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(10) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    product_id VARCHAR(10) NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    review_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, product_id)
);

-- 9. Search History
CREATE TABLE search_history (
    search_id BIGSERIAL PRIMARY KEY,
    customer_id VARCHAR(10) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    search_query VARCHAR(200) NOT NULL,
    searched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================
-- 2. INDEXES
-- ==========================================================
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_reviews_product_rating ON reviews(product_id, rating);
CREATE INDEX idx_search_customer ON search_history(customer_id);
CREATE INDEX idx_cart_customer ON shopping_cart(customer_id);

-- ==========================================================
-- 3. POSTGRESQL TRIGGERS (STOCK INTEGRITY)
-- ==========================================================
CREATE OR REPLACE FUNCTION fn_decrement_product_stock()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE products
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE product_id = NEW.product_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_decrement_product_stock
AFTER INSERT ON order_items
FOR EACH ROW
EXECUTE FUNCTION fn_decrement_product_stock();

-- Prevent Insufficient Stock
CREATE OR REPLACE FUNCTION fn_validate_stock_before_order()
RETURNS TRIGGER AS $$
DECLARE
    current_stock INT;
BEGIN
    SELECT stock_quantity INTO current_stock FROM products WHERE product_id = NEW.product_id;
    IF current_stock < NEW.quantity THEN
        RAISE EXCEPTION 'Insufficient stock for product ID: %', NEW.product_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_stock_before_order
BEFORE INSERT ON order_items
FOR EACH ROW
EXECUTE FUNCTION fn_validate_stock_before_order();

-- ==========================================================
-- 4. ANALYTICAL VIEWS FOR AI RECOMMENDATION
-- ==========================================================

-- View A: Market Basket (Groups products per completed order for Apriori)
CREATE VIEW v_market_basket AS
SELECT 
    o.order_id,
    o.customer_id,
    o.order_date,
    STRING_AGG(p.product_id, ',') AS product_ids,
    STRING_AGG(p.product_name, ' | ') AS product_names,
    COUNT(oi.product_id)::INT AS basket_size,
    SUM(oi.quantity * oi.unit_price) AS order_total
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.order_status = 'COMPLETED'
GROUP BY o.order_id, o.customer_id, o.order_date
HAVING COUNT(oi.product_id) >= 1;

-- View B: Customer Purchase History Summary
CREATE VIEW v_customer_purchase_summary AS
SELECT 
    c.customer_id,
    c.name AS customer_name,
    c.city,
    COUNT(DISTINCT o.order_id)::INT AS total_orders,
    COUNT(oi.order_item_id)::INT AS total_items_purchased,
    COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) AS lifetime_spend,
    STRING_AGG(DISTINCT p.product_id, ',') AS purchased_product_ids,
    STRING_AGG(DISTINCT p.product_name, ' | ') AS purchased_product_names
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.order_status = 'COMPLETED'
LEFT JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN products p ON oi.product_id = p.product_id
GROUP BY c.customer_id, c.name, c.city;

-- View C: Product Performance & Review Metrics
CREATE VIEW v_product_performance AS
SELECT 
    p.product_id,
    p.product_name,
    cat.category_name,
    p.price,
    p.stock_quantity,
    COALESCE(SUM(oi.quantity), 0)::INT AS units_sold,
    COALESCE(SUM(oi.quantity * oi.unit_price), 0.00) AS total_revenue,
    COUNT(DISTINCT r.review_id)::INT AS review_count,
    ROUND(AVG(r.rating), 2) AS avg_rating
FROM products p
JOIN categories cat ON p.category_id = cat.category_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN reviews r ON p.product_id = r.product_id
GROUP BY p.product_id, p.product_name, cat.category_name, p.price, p.stock_quantity;

-- View D: Frequent 2-Item SQL Pairs
CREATE VIEW v_frequent_product_pairs AS
SELECT 
    oi1.product_id AS product_a_id,
    p1.product_name AS product_a_name,
    oi2.product_id AS product_b_id,
    p2.product_name AS product_b_name,
    COUNT(*)::INT AS co_purchase_count
FROM order_items oi1
JOIN order_items oi2 ON oi1.order_id = oi2.order_id AND oi1.product_id < oi2.product_id
JOIN products p1 ON oi1.product_id = p1.product_id
JOIN products p2 ON oi2.product_id = p2.product_id
GROUP BY oi1.product_id, p1.product_name, oi2.product_id, p2.product_name
HAVING COUNT(*) >= 2
ORDER BY co_purchase_count DESC;

-- ==========================================================
-- 5. ENABLE ROW LEVEL SECURITY (RLS) FOR SUPABASE ANON ACCESS
-- Allows your publishable key to read and write without auth errors
-- ==========================================================
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE shopping_cart ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_history ENABLE ROW LEVEL SECURITY;

-- Allow public read access to all catalog and customer tables
CREATE POLICY "Public read categories" ON categories FOR SELECT USING (true);
CREATE POLICY "Public read products" ON products FOR SELECT USING (true);
CREATE POLICY "Public read customers" ON customers FOR SELECT USING (true);
CREATE POLICY "Public read orders" ON orders FOR SELECT USING (true);
CREATE POLICY "Public read order_items" ON order_items FOR SELECT USING (true);
CREATE POLICY "Public read payments" ON payments FOR SELECT USING (true);
CREATE POLICY "Public read shopping_cart" ON shopping_cart FOR SELECT USING (true);
CREATE POLICY "Public read reviews" ON reviews FOR SELECT USING (true);
CREATE POLICY "Public read search_history" ON search_history FOR SELECT USING (true);

-- Allow public insert/update/delete for shopping cart & checkout
CREATE POLICY "Public cart management" ON shopping_cart FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public order creation" ON orders FOR INSERT WITH CHECK (true);
CREATE POLICY "Public order items creation" ON order_items FOR INSERT WITH CHECK (true);
CREATE POLICY "Public payments creation" ON payments FOR INSERT WITH CHECK (true);
CREATE POLICY "Public search insert" ON search_history FOR INSERT WITH CHECK (true);

-- ==========================================================
-- 6. SEED DATA (8 CATEGORIES & 45 PRODUCTS)
-- ==========================================================
INSERT INTO categories (category_id, category_name, description) VALUES
('CAT01', 'Computing & Laptops', 'Laptops, high-performance peripherals, and productivity accessories'),
('CAT02', 'Mobile & Audio', 'Smartphones, fast chargers, protective cases, and audio gear'),
('CAT03', 'Gaming Gear', 'Consoles, gamepads, gaming headsets, and low-latency cables'),
('CAT04', 'Photography & Video', 'Mirrorless cameras, prime lenses, carbon tripods, and memory'),
('CAT05', 'Fitness & Wearables', 'Smartwatches, replacement straps, scales, and nutrition bottles'),
('CAT06', 'Home Office Ergonomics', 'Standing desks, ergonomic chairs, monitor mounts, and desk mats'),
('CAT07', 'Specialty Coffee Bar', 'Espresso brewers, burr grinders, artisan beans, and barista tools'),
('CAT08', 'Student & Productivity', 'Digital paper tablets, stylus pens, notebooks, and study tools');

INSERT INTO products (product_id, category_id, product_name, brand, price, stock_quantity, description) VALUES
('P101', 'CAT01', 'UltraBook Pro 15-inch Laptop', 'Zenith', 1299.99, 150, 'High performance Intel Core i7 laptop with 16GB RAM and 512GB SSD'),
('P102', 'CAT01', 'Ergonomic Wireless Mouse', 'LogiTech', 39.99, 300, 'Precision 2.4GHz wireless optical mouse with quiet click and ergonomic contour'),
('P103', 'CAT01', 'RGB Mechanical Keyboard', 'KeyPro', 89.99, 200, 'Tactile blue switches, custom RGB lighting, and braided detachable cable'),
('P104', 'CAT01', 'Multi-Port USB-C Hub', 'AnkerTech', 49.99, 250, '7-in-1 hub with 4K HDMI, 100W PD charging, 3x USB 3.0, and SD reader'),
('P105', 'CAT01', 'Waterproof Padded Laptop Sleeve', 'CaseLogic', 29.99, 250, 'Shockproof protective sleeve with fleece lining and zipper accessory pocket'),
('P106', 'CAT01', '27-inch 4K UHD Monitor', 'UltraView', 349.99, 100, 'IPS panel with HDR400, USB-C connectivity, and height adjustable stand'),

('P201', 'CAT02', 'Flagship 5G Smartphone', 'NovaTech', 899.99, 180, '6.7-inch OLED 120Hz display, 256GB storage, and triple-lens camera system'),
('P202', 'CAT02', '65W GaN Fast Charger', 'PowerGen', 34.99, 350, 'Ultra-compact Gallium Nitride dual USB-C rapid charger for phone and laptop'),
('P203', 'CAT02', '9H Tempered Glass Screen Protector', 'ArmorShield', 14.99, 500, 'Anti-scratch, fingerprint resistant 2-pack screen protector with easy align tray'),
('P204', 'CAT02', 'Shockproof Slim Silicone Case', 'ArmorShield', 24.99, 400, 'Military-grade drop-tested silicone case with microfiber interior lining'),
('P205', 'CAT02', 'Noise-Cancelling Wireless Earbuds', 'SoundPulse', 149.99, 220, 'Active noise cancelling, 30-hour total battery, and transparency mode'),
('P206', 'CAT02', 'Magnetic 10000mAh Power Bank', 'PowerGen', 45.99, 250, 'Slim wireless portable battery with strong magnetic attachment'),

('P301', 'CAT03', 'Next-Gen Gaming Console', 'PlayCore', 499.99, 120, '1TB SSD 4K gaming system with ray tracing and ultra-high speed loading'),
('P302', 'CAT03', 'Wireless Pro Gamepad Controller', 'PlayCore', 69.99, 300, 'Haptic feedback, adaptive triggers, and textured rubberized grips'),
('P303', 'CAT03', 'Surround Sound Gaming Headset', 'HyperAudio', 79.99, 200, '50mm neodymium drivers, detachable noise-cancelling boom mic, and memory foam pads'),
('P304', 'CAT03', 'Dual Controller Charging Dock', 'PowerGen', 29.99, 250, 'Fast magnetic drop-and-charge cradle with LED charge indicators'),
('P305', 'CAT03', 'Ultra High Speed HDMI 2.1 Cable', 'WirePro', 19.99, 350, 'Braided 8K@60Hz / 4K@120Hz 48Gbps high-bandwidth gaming cable'),
('P306', 'CAT03', 'RGB Extended Gaming Mousepad', 'KeyPro', 24.99, 300, 'Extra large 900x400mm waterproof micro-textured cloth pad with 14 RGB modes'),

('P401', 'CAT04', 'Mirrorless 4K Digital Camera', 'Lumina', 1199.00, 80, '24.2MP full-frame sensor with 4K60p video and in-body 5-axis image stabilization'),
('P402', 'CAT04', '50mm f/1.8 Prime Portrait Lens', 'Lumina', 179.99, 150, 'Fast aperture standard prime lens delivering creamy bokeh and edge-to-edge sharpness'),
('P403', 'CAT04', 'Carbon Fiber Travel Tripod', 'SteadyCam', 89.99, 180, 'Lightweight 1.2kg tripod with 360-degree panoramic ball head and quick-release plate'),
('P404', 'CAT04', '128GB High-Speed V30 SD Card', 'DataPro', 39.99, 450, 'UHS-I U3 Read speeds up to 170MB/s, ideal for 4K video recording'),
('P405', 'CAT04', 'Weatherproof Camera Backpack', 'TrailGear', 69.99, 160, 'Customizable modular dividers with waterproof rain cover and laptop compartment'),
('P406', 'CAT04', 'Rechargeable Bi-Color LED Video Light', 'Lumina', 49.99, 200, 'CRI 96+ dimmable video panel with cold shoe mount and digital display'),

('P501', 'CAT05', 'GPS Smart Sports Watch', 'AeroTrack', 249.99, 190, 'Built-in GPS, heart-rate/SpO2 tracking, 7-day battery, and 50m water resistance'),
('P502', 'CAT05', 'Breathable Silicone Sport Strap', 'AeroTrack', 19.99, 400, 'Sweat-resistant quick release replacement band with stainless pin buckle'),
('P503', 'CAT05', 'Smart Body Composition Scale', 'FitMetrics', 59.99, 210, 'Measures body fat, muscle mass, BMI, and syncs via Bluetooth to mobile app'),
('P504', 'CAT05', '100% Whey Isolate Protein (2kg)', 'NutriPure', 64.99, 280, 'Ultra-filtered vanilla whey isolate powder with 27g protein per scoop'),
('P505', 'CAT05', 'Insulated Stainless Shaker Bottle', 'HydroPro', 22.99, 320, '24oz odor-resistant vacuum insulated shaker cup with silent blender ball'),
('P506', 'CAT05', 'Heavy Duty Resistance Exercise Bands', 'FitMetrics', 25.99, 250, 'Set of 5 color-coded natural latex loop bands with carrying pouch'),

('P601', 'CAT06', 'Dual-Motor Electric Standing Desk', 'ErgoWork', 399.99, 90, 'Height-adjustable 55x28 inch desk with 4 memory presets and anti-collision sensor'),
('P602', 'CAT06', 'Ergonomic High-Back Mesh Chair', 'ErgoWork', 279.99, 110, 'Breathable mesh back with adjustable 3D lumbar support and reclining tilt'),
('P603', 'CAT06', 'Heavy-Duty Dual Monitor Arm Mount', 'ErgoWork', 59.99, 180, 'Gas spring articulating desk clamp mount fitting screens 17 to 32 inches'),
('P604', 'CAT06', 'Merino Wool Felt Desk Mat (90x40cm)', 'CraftDesk', 32.99, 260, 'Anti-slip natural wool felt pad providing wrist cushion and desk protection'),
('P605', 'CAT06', 'ScreenBar Monitor Light Bar', 'LightCraft', 49.99, 220, 'Auto-dimming eye care e-reading LED desk lamp with zero screen glare'),

('P701', 'CAT07', 'Compact 15-Bar Espresso Machine', 'BaristaPro', 299.99, 100, 'Italian pump espresso maker with manual steam wand and thermo-block heating'),
('P702', 'CAT07', 'Electric Conical Burr Coffee Grinder', 'BaristaPro', 89.99, 140, '30 precise grind settings for espresso, drip, and French press'),
('P703', 'CAT07', 'Single-Origin Whole Bean Coffee (1kg)', 'RoastMaster', 18.99, 350, 'Ethically sourced Ethiopian Yirgacheffe medium roast with floral notes'),
('P704', 'CAT07', 'Stainless Steel Milk Frothing Pitcher', 'BaristaPro', 16.99, 300, '12oz 350ml calibrated steaming pitcher with precision pour spout'),
('P705', 'CAT07', 'Digital Precision Coffee Timer Scale', 'BrewLogic', 29.99, 240, '0.1g accuracy scale with built-in auto timer for pourover and espresso'),

('P801', 'CAT08', '10.3-inch Digital Paper E-Reader Tablet', 'PaperLite', 329.99, 130, 'Anti-glare E-Ink notebook for distraction-free reading, note-taking, and PDF annotating'),
('P802', 'CAT08', 'Pressure-Sensitive Digital Stylus', 'PaperLite', 49.99, 260, '4096 pressure levels, tilt recognition, and eraser button without charging needed'),
('P803', 'CAT08', 'Replacement Stylus Felt Nibs (5-Pack)', 'PaperLite', 14.99, 380, 'Paper-like textured friction tips for natural pencil-on-paper feeling'),
('P804', 'CAT08', 'Premium Dotted Hardcover Journal', 'CraftDesk', 19.99, 310, '160gsm bleed-proof bamboo paper notebook with elastic band and inner pocket'),
('P805', 'CAT08', 'Pastel Dual-Tip Highlighters (6-Pack)', 'ColorFlow', 12.99, 450, 'Chisel and fine bullet tip mild aesthetic pastel water-based markers');

-- Seed Showcase Customers
INSERT INTO customers (customer_id, name, email, phone, city) VALUES
('C101', 'Alex Rivera', 'alex.rivera@example.com', '555-0101', 'Seattle'),
('C102', 'Samantha Hayes', 'sam.hayes@example.com', '555-0102', 'San Francisco'),
('C103', 'Marcus Chen', 'marcus.chen@example.com', '555-0103', 'Austin'),
('C104', 'Elena Rostova', 'elena.r@example.com', '555-0104', 'New York'),
('C105', 'David Kim', 'david.kim@example.com', '555-0105', 'Chicago'),
('C106', 'Chloe Bennett', 'chloe.b@example.com', '555-0106', 'Denver'),
('C107', 'Julian Vance', 'julian.v@example.com', '555-0107', 'Portland'),
('C108', 'Aria Patel', 'aria.patel@example.com', '555-0108', 'Boston');

-- Seed initial showcase shopping carts
INSERT INTO shopping_cart (customer_id, product_id, quantity) VALUES
('C101', 'P101', 1),
('C102', 'P201', 1),
('C103', 'P301', 1),
('C104', 'P401', 1),
('C105', 'P501', 1),
('C106', 'P601', 1),
('C107', 'P701', 1),
('C108', 'P801', 1);
