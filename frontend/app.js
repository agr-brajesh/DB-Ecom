/**
 * Frontend Controller for NexusAI E-Commerce DBMS & Recommender System
 */

const API_BASE = "";

// Application State
let activeCustomerId = "C101";
let allCustomers = [];
let allProducts = [];
let allCategories = [];
let currentTab = "recommendations";
let selectedCategoryId = "";

// DOM Elements
const customerSelect = document.getElementById("customerSelect");
const heroCustomerName = document.getElementById("heroCustomerName");
const heroCustomerId = document.getElementById("heroCustomerId");
const heroCustomerMeta = document.getElementById("heroCustomerMeta");
const heroAvatar = document.getElementById("heroAvatar");
const heroOrderCount = document.getElementById("heroOrderCount");
const heroCartCount = document.getElementById("heroCartCount");
const historyList = document.getElementById("historyList");
const activeCartList = document.getElementById("activeCartList");
const recommendationsGrid = document.getElementById("recommendationsGrid");
const refreshRecsBtn = document.getElementById("refreshRecsBtn");

// Catalog Elements
const catalogGrid = document.getElementById("catalogGrid");
const categoryFilterBar = document.getElementById("categoryFilterBar");
const catalogSearchInput = document.getElementById("catalogSearchInput");

// Rules Elements
const rulesTableBody = document.getElementById("rulesTableBody");
const minConfSlider = document.getElementById("minConfSlider");
const minLiftSlider = document.getElementById("minLiftSlider");
const confValueDisplay = document.getElementById("confValueDisplay");
const liftValueDisplay = document.getElementById("liftValueDisplay");
const applyRuleFilterBtn = document.getElementById("applyRuleFilterBtn");

// DBMS & SQL Elements
const dbmsViewHead = document.getElementById("dbmsViewHead");
const dbmsViewBody = document.getElementById("dbmsViewBody");
const sqlQueryInput = document.getElementById("sqlQueryInput");
const runSqlBtn = document.getElementById("runSqlBtn");
const sqlResultWrap = document.getElementById("sqlResultWrap");
const sqlResultHead = document.getElementById("sqlResultHead");
const sqlResultBody = document.getElementById("sqlResultBody");
const sqlErrorMsg = document.getElementById("sqlErrorMsg");

// Cart Elements
const cartToggleBtn = document.getElementById("cartToggleBtn");
const cartDrawerOverlay = document.getElementById("cartDrawerOverlay");
const closeCartBtn = document.getElementById("closeCartBtn");
const drawerCartItems = document.getElementById("drawerCartItems");
const drawerSubtotal = document.getElementById("drawerSubtotal");
const cartCountBadge = document.getElementById("cartCountBadge");
const drawerCustomerName = document.getElementById("drawerCustomerName");
const checkoutSuccessBtn = document.getElementById("checkoutSuccessBtn");
const checkoutFailBtn = document.getElementById("checkoutFailBtn");
const transactionAuditLog = document.getElementById("transactionAuditLog");
const transactionLogText = document.getElementById("transactionLogText");

// Toast Notification
function showToast(message, type = "success") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${type === 'success' ? '✓' : '⚠'}</span> <div>${message}</div>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 4000);
}

// Format Currency
function formatMoney(amount) {
    return "$" + parseFloat(amount).toFixed(2);
}

// ==========================================================
// 1. INITIALIZATION & DATA LOADING
// ==========================================================
async function initApp() {
    setupTabNavigation();
    setupEventListeners();
    await loadCustomers();
    await loadCatalog();
    await loadRecommendations(activeCustomerId);
    await loadCartBadge(activeCustomerId);
    await loadRules();
    await loadDbmsView("v_market_basket");
}

// Tab navigation handler
function setupTabNavigation() {
    const tabs = document.querySelectorAll(".tab-btn");
    tabs.forEach(btn => {
        btn.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            btn.classList.add("active");
            const target = btn.dataset.tab;
            document.querySelectorAll(".tab-content").forEach(content => {
                content.classList.remove("active");
            });
            document.getElementById(`tab-${target}`).classList.add("active");
            currentTab = target;
        });
    });
}

function setupEventListeners() {
    customerSelect.addEventListener("change", async (e) => {
        activeCustomerId = e.target.value;
        const cust = allCustomers.find(c => c.customer_id === activeCustomerId);
        if (cust) {
            updateHeroHeader(cust);
        }
        await loadRecommendations(activeCustomerId);
        await loadCartBadge(activeCustomerId);
    });

    refreshRecsBtn.addEventListener("click", () => {
        loadRecommendations(activeCustomerId);
        showToast("Recommendations refreshed from database.", "success");
    });

    // Cart Drawer toggles
    cartToggleBtn.addEventListener("click", openCartDrawer);
    closeCartBtn.addEventListener("click", closeCartDrawer);
    cartDrawerOverlay.addEventListener("click", (e) => {
        if (e.target === cartDrawerOverlay) closeCartDrawer();
    });

    // Checkout actions
    checkoutSuccessBtn.addEventListener("click", () => handleCheckout(false));
    checkoutFailBtn.addEventListener("click", () => handleCheckout(true));

    // Rule Filter Sliders
    minConfSlider.addEventListener("input", (e) => {
        confValueDisplay.innerText = `${Math.round(e.target.value * 100)}%`;
    });
    minLiftSlider.addEventListener("input", (e) => {
        liftValueDisplay.innerText = `${parseFloat(e.target.value).toFixed(1)}x`;
    });
    applyRuleFilterBtn.addEventListener("click", loadRules);

    // DBMS View Buttons
    document.querySelectorAll(".view-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".view-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            loadDbmsView(btn.dataset.view);
        });
    });

    // SQL Runner
    runSqlBtn.addEventListener("click", executeUserSql);
    document.querySelectorAll(".sql-preset-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            sqlQueryInput.value = btn.dataset.query;
            executeUserSql();
        });
    });

    // Catalog Search Filter
    catalogSearchInput.addEventListener("input", filterAndRenderCatalog);
}

// ==========================================================
// 2. CUSTOMER PROFILES & RECOMMENDATIONS
// ==========================================================
async function loadCustomers() {
    try {
        const res = await fetch(`${API_BASE}/api/customers`);
        const json = await res.json();
        if (json.status === "success") {
            allCustomers = json.customers;
            customerSelect.innerHTML = allCustomers.map(c => {
                const domainLabel = getDomainLabel(c.customer_id);
                return `<option value="${c.customer_id}">${c.customer_id}: ${c.name} (${domainLabel})</option>`;
            }).join("");

            const defaultCust = allCustomers.find(c => c.customer_id === activeCustomerId) || allCustomers[0];
            activeCustomerId = defaultCust.customer_id;
            customerSelect.value = activeCustomerId;
            updateHeroHeader(defaultCust);
        }
    } catch (err) {
        console.error("Failed to load customers:", err);
    }
}

function getDomainLabel(cid) {
    const labels = {
        "C101": "Computing & Workstation",
        "C102": "Mobile & Audio",
        "C103": "Console Gaming",
        "C104": "Photography & Video",
        "C105": "Fitness & Wearables",
        "C106": "Home Office Ergonomics",
        "C107": "Specialty Coffee Bar",
        "C108": "Student Study Pack"
    };
    return labels[cid] || "General Shopper";
}

function updateHeroHeader(cust) {
    heroCustomerName.innerText = cust.name;
    heroCustomerId.innerText = cust.customer_id;
    heroCustomerMeta.innerHTML = `Customer ID: <strong>${cust.customer_id}</strong> • ${cust.city} • ${cust.email}`;
    drawerCustomerName.innerText = cust.name;
    const initials = cust.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
    heroAvatar.innerText = initials;
}

async function loadRecommendations(customerId) {
    try {
        const res = await fetch(`${API_BASE}/api/recommendations/${customerId}?top_n=4`);
        const json = await res.json();
        if (json.status === "success") {
            const data = json.data;
            renderCustomerContext(data);
            renderRecommendations(data.recommendations);
        }
    } catch (err) {
        console.error("Error loading recommendations:", err);
    }
}

function renderCustomerContext(data) {
    heroOrderCount.innerText = data.history.length;
    heroCartCount.innerText = data.active_cart.length;

    // Render purchase history
    if (data.history.length === 0) {
        historyList.innerHTML = `<div class="compact-item"><span class="item-name" style="color:var(--text-muted);">No prior completed orders found.</span></div>`;
    } else {
        historyList.innerHTML = data.history.map(item => `
            <div class="compact-item">
                <div class="item-left">
                    <span class="item-domain-tag">${item.category}</span>
                    <span class="item-name">${item.name}</span>
                </div>
                <span class="item-price">${formatMoney(item.price)}</span>
            </div>
        `).join("");
    }

    // Render active cart
    if (data.active_cart.length === 0) {
        activeCartList.innerHTML = `<div class="compact-item"><span class="item-name" style="color:var(--text-muted);">Cart is empty. Add products to trigger live antecedent rules.</span></div>`;
    } else {
        activeCartList.innerHTML = data.active_cart.map(item => `
            <div class="compact-item">
                <div class="item-left">
                    <span class="item-domain-tag">${item.category}</span>
                    <span class="item-name">${item.name}</span>
                </div>
                <span class="item-price">${formatMoney(item.price)}</span>
            </div>
        `).join("");
    }
}

function renderRecommendations(recommendations) {
    if (!recommendations || recommendations.length === 0) {
        recommendationsGrid.innerHTML = `
            <div class="glass-panel" style="grid-column: 1 / -1; text-align: center; padding: 2.5rem;">
                <p style="color: var(--text-secondary);">No active recommendation rules found for this customer profile.</p>
            </div>
        `;
        return;
    }

    recommendationsGrid.innerHTML = recommendations.map((rec, index) => {
        let pillClass = "apriori";
        let pillIcon = "⚡";
        if (rec.algorithm.includes("Cosine")) {
            pillClass = "content";
            pillIcon = "🔍";
        } else if (rec.algorithm.includes("Rating")) {
            pillClass = "top-rated";
            pillIcon = "★";
        }

        return `
            <div class="product-card rec-card">
                <div>
                    <div class="card-top">
                        <span class="category-tag">${rec.category_name}</span>
                        <span class="ai-pill ${pillClass}">
                            <span>${pillIcon}</span> ${rec.algorithm.split(' ')[0]}
                        </span>
                    </div>
                    <h3 class="card-title">${index + 1}. ${rec.product_name}</h3>
                    <p class="card-desc">${rec.description || ''}</p>
                    
                    <div class="rec-rationale">
                        <div>${rec.reason}</div>
                        ${rec.confidence ? `
                            <div class="rec-metrics">
                                <span>Confidence: ${(rec.confidence * 100).toFixed(1)}%</span>
                                <span>Lift: ${rec.lift.toFixed(2)}x</span>
                            </div>
                        ` : ''}
                    </div>
                </div>

                <div class="card-bottom">
                    <div class="price-stock">
                        <span class="card-price">${formatMoney(rec.price)}</span>
                        <span class="card-stock">⭐ ${rec.avg_rating || 4.8} rating</span>
                    </div>
                    <button class="btn-add-cart" onclick="addProductToCart('${rec.product_id}', '${escapeHtml(rec.product_name)}')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="12" y1="5" x2="12" y2="19"/>
                            <line x1="5" y1="12" x2="19" y2="12"/>
                        </svg>
                        Add to Cart
                    </button>
                </div>
            </div>
        `;
    }).join("");
}

// ==========================================================
// 3. CATALOG & SEARCH
// ==========================================================
async function loadCatalog() {
    try {
        const res = await fetch(`${API_BASE}/api/products`);
        const json = await res.json();
        if (json.status === "success") {
            allProducts = json.products;
            allCategories = json.categories;

            // Render category filters
            categoryFilterBar.innerHTML = `
                <button class="pill active" data-cat="">All Categories (${allProducts.length})</button>
                ${allCategories.map(c => `
                    <button class="pill" data-cat="${c.category_id}">${c.category_name}</button>
                `).join("")}
            `;

            categoryFilterBar.querySelectorAll(".pill").forEach(pill => {
                pill.addEventListener("click", () => {
                    categoryFilterBar.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
                    pill.classList.add("active");
                    selectedCategoryId = pill.dataset.cat;
                    filterAndRenderCatalog();
                });
            });

            filterAndRenderCatalog();
        }
    } catch (err) {
        console.error("Error loading catalog:", err);
    }
}

function filterAndRenderCatalog() {
    const searchVal = catalogSearchInput.value.toLowerCase().trim();
    const filtered = allProducts.filter(p => {
        const matchCat = !selectedCategoryId || p.category_id === selectedCategoryId;
        const matchSearch = !searchVal || 
            p.product_name.toLowerCase().includes(searchVal) ||
            (p.brand && p.brand.toLowerCase().includes(searchVal)) ||
            (p.description && p.description.toLowerCase().includes(searchVal));
        return matchCat && matchSearch;
    });

    if (filtered.length === 0) {
        catalogGrid.innerHTML = `
            <div class="glass-panel" style="grid-column: 1 / -1; text-align:center; padding: 2rem;">
                <p style="color:var(--text-secondary);">No products match your filter criteria.</p>
            </div>
        `;
        return;
    }

    catalogGrid.innerHTML = filtered.map(p => `
        <div class="product-card">
            <div>
                <div class="card-top">
                    <span class="category-tag">${p.category_name}</span>
                    <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 600;">${p.brand || ''}</span>
                </div>
                <h3 class="card-title">${p.product_name}</h3>
                <p class="card-desc">${p.description || ''}</p>
            </div>

            <div class="card-bottom">
                <div class="price-stock">
                    <span class="card-price">${formatMoney(p.price)}</span>
                    <span class="card-stock">Stock: ${p.stock_quantity} units</span>
                </div>
                <button class="btn-add-cart" onclick="addProductToCart('${p.product_id}', '${escapeHtml(p.product_name)}')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"/>
                        <line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    Add
                </button>
            </div>
        </div>
    `).join("");
}

// ==========================================================
// 4. CART & ACID TRANSACTIONS
// ==========================================================
async function addProductToCart(productId, productName) {
    try {
        const res = await fetch(`${API_BASE}/api/cart/add`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeCustomerId,
                product_id: productId,
                quantity: 1
            })
        });
        const json = await res.json();
        if (json.status === "success") {
            showToast(`Added ${productName} to active cart!`, "success");
            await loadCartBadge(activeCustomerId);
            await loadRecommendations(activeCustomerId);
            if (cartDrawerOverlay.classList.contains("open")) {
                await renderCartDrawerItems();
            }
        } else {
            showToast(json.message || "Failed to add to cart.", "error");
        }
    } catch (err) {
        showToast("Error adding item to cart.", "error");
    }
}

async function removeProductFromCart(productId) {
    try {
        const res = await fetch(`${API_BASE}/api/cart/remove`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeCustomerId,
                product_id: productId
            })
        });
        const json = await res.json();
        if (json.status === "success") {
            showToast("Item removed from cart.", "success");
            await loadCartBadge(activeCustomerId);
            await loadRecommendations(activeCustomerId);
            await renderCartDrawerItems();
        }
    } catch (err) {
        showToast("Error removing item.", "error");
    }
}

async function loadCartBadge(customerId) {
    try {
        const res = await fetch(`${API_BASE}/api/cart/${customerId}`);
        const json = await res.json();
        if (json.status === "success") {
            const count = json.items.reduce((acc, i) => acc + i.quantity, 0);
            cartCountBadge.innerText = count;
        }
    } catch (err) {
        console.error("Error loading cart count:", err);
    }
}

async function openCartDrawer() {
    cartDrawerOverlay.classList.add("open");
    transactionAuditLog.style.display = "none";
    await renderCartDrawerItems();
}

function closeCartDrawer() {
    cartDrawerOverlay.classList.remove("open");
}

async function renderCartDrawerItems() {
    try {
        const res = await fetch(`${API_BASE}/api/cart/${activeCustomerId}`);
        const json = await res.json();
        if (json.status === "success") {
            drawerSubtotal.innerText = formatMoney(json.total_amount);
            if (json.items.length === 0) {
                drawerCartItems.innerHTML = `
                    <div style="text-align: center; color: var(--text-muted); margin-top: 3rem;">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 0.75rem; opacity: 0.5;">
                            <circle cx="9" cy="21" r="1"/>
                            <circle cx="20" cy="21" r="1"/>
                            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
                        </svg>
                        <p>Your shopping cart is currently empty.</p>
                    </div>
                `;
                checkoutSuccessBtn.disabled = true;
                checkoutFailBtn.disabled = true;
            } else {
                checkoutSuccessBtn.disabled = false;
                checkoutFailBtn.disabled = false;
                drawerCartItems.innerHTML = json.items.map(item => `
                    <div class="cart-item-row">
                        <div class="cart-item-info">
                            <h4>${item.product_name}</h4>
                            <span>Qty: ${item.quantity} × ${formatMoney(item.price)} • Stock: ${item.stock_quantity}</span>
                        </div>
                        <div class="cart-item-action">
                            <strong>${formatMoney(item.subtotal)}</strong>
                            <button class="btn-remove-item" onclick="removeProductFromCart('${item.product_id}')">Remove</button>
                        </div>
                    </div>
                `).join("");
            }
        }
    } catch (err) {
        console.error("Error rendering cart drawer:", err);
    }
}

async function handleCheckout(simulateFail = false) {
    transactionAuditLog.style.display = "block";
    transactionLogText.innerText = "Initiating ACID transaction...\n[1] BEGIN TRANSACTION;";

    try {
        const res = await fetch(`${API_BASE}/api/checkout`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeCustomerId,
                payment_method: "CREDIT_CARD",
                simulate_fail: simulateFail
            })
        });

        const json = await res.json();
        if (json.status === "success") {
            transactionLogText.innerText = 
`[1] BEGIN TRANSACTION;
[2] Validated stock availability for all cart items.
[3] INSERT INTO orders (order_id: ${json.result.order_id}, amount: $${json.result.amount})
[4] INSERT INTO order_items (Auto-decremented inventory via DB Trigger)
[5] INSERT INTO payments (Status: SUCCESS)
[6] DELETE FROM shopping_cart (Cart cleared)
[7] [COMMIT] Transaction successfully committed! All changes persisted.`;

            showToast("Order placed successfully! ACID Transaction committed.", "success");
            await loadCartBadge(activeCustomerId);
            await renderCartDrawerItems();
            await loadRecommendations(activeCustomerId);
            await loadDbmsView("v_customer_purchase_summary");
        } else {
            transactionLogText.innerText = 
`[1] BEGIN TRANSACTION;
[2] Validated cart items.
[!] Error: ${json.result ? json.result.error : json.message}
[!] [ROLLBACK] Transaction rolled back!
[✓] Stock was preserved.
[✓] Shopping cart remains intact. Partial writes prevented.`;
            showToast("Transaction rolled back! No changes saved.", "error");
        }
    } catch (err) {
        transactionLogText.innerText += "\n[!] Connection failure.";
        showToast("Error executing transaction.", "error");
    }
}

// ==========================================================
// 5. APRIORI RULES EXPLORER
// ==========================================================
async function loadRules() {
    const minConf = minConfSlider.value;
    const minLift = minLiftSlider.value;

    try {
        const res = await fetch(`${API_BASE}/api/analytics/rules?min_confidence=${minConf}&min_lift=${minLift}&limit=40`);
        const json = await res.json();
        if (json.status === "success") {
            if (json.rules.length === 0) {
                rulesTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No association rules match these thresholds. Lower confidence or lift.</td></tr>`;
                return;
            }

            rulesTableBody.innerHTML = json.rules.map((rule, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td><strong>${rule.antecedent_names.join(" + ")}</strong></td>
                    <td class="rule-arrow">&rarr;</td>
                    <td><strong style="color:#a5b4fc;">${rule.consequent_names.join(" + ")}</strong></td>
                    <td><span class="badge-metric support">${(rule.support * 100).toFixed(1)}%</span></td>
                    <td><span class="badge-metric confidence">${(rule.confidence * 100).toFixed(1)}%</span></td>
                    <td><span class="badge-metric lift">${rule.lift.toFixed(2)}x</span></td>
                </tr>
            `).join("");
        }
    } catch (err) {
        console.error("Error loading rules:", err);
    }
}

// ==========================================================
// 6. DBMS VIEWS & SQL CONSOLE
// ==========================================================
async function loadDbmsView(viewName) {
    try {
        const res = await fetch(`${API_BASE}/api/analytics/view/${viewName}`);
        const json = await res.json();
        if (json.status === "success") {
            dbmsViewHead.innerHTML = `<tr>${json.columns.map(c => `<th>${c}</th>`).join("")}</tr>`;
            dbmsViewBody.innerHTML = json.data.map(row => `
                <tr>${json.columns.map(c => `<td>${row[c] !== null ? row[c] : '<em>null</em>'}</td>`).join("")}</tr>
            `).join("");
        }
    } catch (err) {
        console.error("Error loading DBMS view:", err);
    }
}

async function executeUserSql() {
    const query = sqlQueryInput.value.trim();
    sqlErrorMsg.style.display = "none";
    sqlResultWrap.style.display = "none";

    try {
        const res = await fetch(`${API_BASE}/api/sql/execute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query })
        });
        const json = await res.json();
        if (json.status === "success") {
            sqlResultWrap.style.display = "block";
            sqlResultHead.innerHTML = `<tr>${json.columns.map(c => `<th>${c}</th>`).join("")}</tr>`;
            sqlResultBody.innerHTML = json.rows.map(row => `
                <tr>${json.columns.map(c => `<td>${row[c] !== null ? row[c] : '<em>null</em>'}</td>`).join("")}</tr>
            `).join("");
            showToast(`Query executed: returned ${json.row_count} rows.`, "success");
        } else {
            sqlErrorMsg.style.display = "block";
            sqlErrorMsg.innerText = json.message || "SQL syntax or execution error.";
        }
    } catch (err) {
        sqlErrorMsg.style.display = "block";
        sqlErrorMsg.innerText = "Failed to connect to backend SQL runner.";
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/'/g, "&#39;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

// Kickoff
document.addEventListener("DOMContentLoaded", initApp);
