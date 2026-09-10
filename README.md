# NexusAI: AI-Based E-Commerce Database with Product Recommendation

A full-stack, production-grade DBMS and AI project demonstrating **Relational Database Design (3NF)**, **ACID Transactions**, **Database Views & Triggers**, and **Apriori Association Rule Mining (Market Basket Analysis)** across **8 distinct consumer product domains**.

---

## 🌟 Key Features

### 1. Relational DBMS Layer (Database-First Design)
- **3NF & BCNF Normalized Schema**: 9 tables resolving insertion, deletion, and update anomalies.
- **ACID Transactions**: Atomic checkout procedure demonstrating `BEGIN TRANSACTION`, inventory verification, stock decrements, payment logging, and automatic `ROLLBACK` on failures.
- **Inventory Triggers**: `trg_decrement_product_stock` and `trg_validate_stock_before_order` enforce stock consistency automatically at the database engine level.
- **Analytical Views**:
  - `v_market_basket`: Formats multi-product orders for the Apriori mining engine.
  - `v_customer_purchase_summary`: Aggregates customer order frequency, lifetime spend, and items purchased.
  - `v_product_performance`: Aggregates units sold, gross revenue, and customer review scores.
  - `v_frequent_product_pairs`: Pure-SQL self-join implementation of co-occurrence pairs.
- **B-Tree Performance Indexes**: Optimizes foreign key joins and frequent aggregation lookups.

### 2. The 8 Product Domains & Embedded Datasets
Instead of just 3 items, the database includes **45 products** and **300+ transactions** across 8 rich domains with embedded co-purchase patterns:
1. **Computing & Workstation**: Laptop, Wireless Mouse, Mechanical Keyboard $\to$ USB-C Hub, Laptop Sleeve
2. **Mobile & Audio**: Smartphone, Silicone Case $\to$ 9H Tempered Glass, GaN Fast Charger
3. **Gaming Gear**: Console, Gamepad Controller $\to$ Dual Charging Dock, HDMI 2.1 Cable
4. **Photography & Video**: 4K Camera, 50mm Prime Lens $\to$ 128GB SD Card, Camera Backpack
5. **Fitness & Wearables**: Smart Sports Watch $\to$ Replacement Sport Strap, Smart Body Scale
6. **Home Office Ergonomics**: Standing Desk, Mesh Chair $\to$ Felt Desk Mat, Dual Monitor Arm
7. **Specialty Coffee Bar**: Espresso Machine, Whole Beans $\to$ Milk Frothing Pitcher, Burr Grinder
8. **Student Study Pack**: Digital Paper Tablet, Stylus Pen $\to$ Replacement Nibs, Hardcover Journal

### 3. AI Recommendation Engine
- **Apriori Association Rule Mining**: Pure-Python implementation calculating **Support**, **Confidence**, and **Lift** to discover statistically significant co-purchase rules ($X \to Y$).
- **Content-Based Filtering (Cosine Similarity)**: TF-IDF vectorizer and Cosine Similarity matching product descriptions/metadata for cold-start and search intent.
- **Rule Explanations**: Transparent rationale explaining *why* an item was recommended with live confidence and lift metrics.

### 4. Interactive Web Portal
- **Customer Switcher**: Switch between showcase profiles (`C101` to `C108`) to instantly see personalized recommendations across all 8 domains.
- **Apriori Rule Explorer**: Real-time sliders for Minimum Confidence and Minimum Lift.
- **DBMS View Inspector & SQL Runner**: Live interactive console to run `SELECT` / `EXPLAIN` queries directly against the database.
- **Shopping Cart & ACID Simulator**: Test normal checkout (`COMMIT`) vs simulated gateway failures (`ROLLBACK`).

---

## 🚀 How to Run the Project

### 1. Seed / Re-initialize Database
```bash
python database/seed_data.py
```

### 2. Test ACID Transactions in Terminal
```bash
python database/transactions.py
```

### 3. Test Apriori Algorithm & Recommendations
```bash
python ai/apriori.py
python -m ai.recommender
```

### 4. Start the Web Dashboard
```bash
python backend/app.py
```
Open your web browser at: **`http://127.0.0.1:5000`**

---

## 📂 Project Directory Structure

```
DB Project/
├── database/
│   ├── schema.sql              # DDL: 9 relational tables with constraints & cascades
│   ├── views_triggers.sql      # Analytical views, triggers, and B-Tree indexes
│   ├── seed_data.py            # Generates 8 domains, 45 products, 25 customers, 300+ orders
│   ├── transactions.py         # ACID checkout transaction demonstration
│   └── ecommerce.db            # SQLite database file
├── ai/
│   ├── apriori.py              # Pure-Python Apriori association rule miner
│   ├── content_based.py        # TF-IDF Cosine Similarity recommender
│   └── recommender.py          # Hybrid recommendation engine
├── backend/
│   └── app.py                  # Flask REST API server & Live SQL runner
├── frontend/
│   ├── index.html              # Modern single-page web portal
│   ├── style.css               # Dark-mode glassmorphism design system
│   └── app.js                  # Frontend client controller
├── docs/
│   ├── ER_DIAGRAM.md           # Mermaid ER diagram and schema data dictionary
│   └── NORMALIZATION.md        # Academic proof of 1NF, 2NF, 3NF decomposition
└── README.md                   # Project documentation & execution guide
```
