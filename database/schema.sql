-- ==========================================================
-- E-COMMERCE DATABASE SCHEMA (3NF NORMALIZED)
-- Features: 9 Core Tables, Foreign Keys, CHECK constraints,
--           Cascade deletes, and Unique constraints.
-- ==========================================================

PRAGMA foreign_keys = ON;

-- 1. Product Categories Table
CREATE TABLE IF NOT EXISTS categories (
    category_id VARCHAR(10) PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Products Table
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(10) PRIMARY KEY,
    category_id VARCHAR(10) NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    brand VARCHAR(100),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE RESTRICT
);

-- 3. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20),
    city VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Orders Table
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(15) PRIMARY KEY,
    customer_id VARCHAR(10) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (total_amount >= 0),
    order_status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED' 
        CHECK (order_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'CANCELLED')),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- 5. Order Items Table (M:N Bridge resolving Order <-> Product)
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id VARCHAR(15) NOT NULL,
    product_id VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT,
    UNIQUE(order_id, product_id)
);

-- 6. Payments Table
CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(15) PRIMARY KEY,
    order_id VARCHAR(15) NOT NULL UNIQUE,
    payment_method VARCHAR(50) NOT NULL 
        CHECK (payment_method IN ('CREDIT_CARD', 'DEBIT_CARD', 'UPI', 'NET_BANKING', 'CASH_ON_DELIVERY')),
    payment_status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS' 
        CHECK (payment_status IN ('SUCCESS', 'PENDING', 'FAILED')),
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount >= 0),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- 7. Shopping Cart Table
CREATE TABLE IF NOT EXISTS shopping_cart (
    cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(10) NOT NULL,
    product_id VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    UNIQUE(customer_id, product_id)
);

-- 8. Product Reviews Table (Ratings for Collaborative Filtering)
CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(10) NOT NULL,
    product_id VARCHAR(10) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    UNIQUE(customer_id, product_id)
);

-- 9. Search History Table (Search Queries for Content/Intent Matching)
CREATE TABLE IF NOT EXISTS search_history (
    search_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(10) NOT NULL,
    search_query VARCHAR(200) NOT NULL,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- 10. Wishlist Table (Customer Saved Products for Later)
CREATE TABLE IF NOT EXISTS wishlist (
    wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(10) NOT NULL,
    product_id VARCHAR(10) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    UNIQUE(customer_id, product_id)
);

-- 11. Session Events Table (Phase 5 Context-Aware Real-Time Interactions)
CREATE TABLE IF NOT EXISTS session_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(10) NOT NULL,
    product_id VARCHAR(10),
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('PRODUCT_VIEW', 'SEARCH', 'ADD_TO_CART', 'PURCHASE', 'WISHLIST_ADD')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

