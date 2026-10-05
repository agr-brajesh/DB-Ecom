/**
 * NexusAI E-Commerce Application & DBMS Intelligence Platform
 * Frontend Client Controller
 */

const API_BASE = "";

// ==========================================================
// APPLICATION STATE
// ==========================================================
let activeCustomerId = "C101";
let allCustomers = [];
let allProducts = [];
let allCategories = [];
let currentView = "home";
let adminMode = false;
let activeAdminTab = "dashboard";

// Filters & Sorting
let activeCategoryFilter = "";
let activeSearchQuery = "";
let activePriceMax = 1500;
let activeInStockOnly = false;
let activeRatingMin = 0;
let activeSort = "featured";

// Wishlist stored per customer in localStorage
let currentWishlist = new Set();

// ==========================================================
// DOM ELEMENT CACHE
// ==========================================================
const customerSelect = document.getElementById("customerSelect");
const togglePortalModeBtn = document.getElementById("togglePortalModeBtn");
const portalModeBtnText = document.getElementById("portalModeBtnText");
const storefrontHeader = document.getElementById("storefrontHeader");
const storefrontContainer = document.getElementById("storefrontContainer");
const storefrontFooter = document.getElementById("storefrontFooter");
const adminPortalContainer = document.getElementById("adminPortalContainer");

// Nav elements
const globalSearchInput = document.getElementById("globalSearchInput");
const clearSearchBtn = document.getElementById("clearSearchBtn");
const headerCategorySelect = document.getElementById("headerCategorySelect");
const headerSearchBtn = document.getElementById("headerSearchBtn");
const wishlistCountBadge = document.getElementById("wishlistCountBadge");
const cartCountBadge = document.getElementById("cartCountBadge");
const navCartTotal = document.getElementById("navCartTotal");
const navCustomerName = document.getElementById("navCustomerName");
const navCustomerAvatar = document.getElementById("navCustomerAvatar");
const accountMenuBtn = document.getElementById("accountMenuBtn");
const accountDropdown = document.getElementById("accountDropdown");

// Cart Drawer
const cartToggleBtn = document.getElementById("cartToggleBtn");
const cartDrawerOverlay = document.getElementById("cartDrawerOverlay");
const closeCartBtn = document.getElementById("closeCartBtn");
const drawerCartItems = document.getElementById("drawerCartItems");
const drawerSubtotal = document.getElementById("drawerSubtotal");

// Product Modal
const productDetailModal = document.getElementById("productDetailModal");
const productDetailContent = document.getElementById("productDetailContent");
const closeProductDetailBtn = document.getElementById("closeProductDetailBtn");

// ==========================================================
// 1. INITIALIZATION & ROUTING
// ==========================================================
document.addEventListener("DOMContentLoaded", initApp);

async function initApp() {
    setupGlobalEventListeners();
    loadWishlistFromStorage();
    await loadCustomers();
    await loadCatalog();
    await loadRecommendations(activeCustomerId);
    await loadCart(activeCustomerId);
    
    // Route from URL hash if available
    const hash = window.location.hash.replace("#", "");
    if (hash && document.getElementById(`view-${hash}`)) {
        navigateTo(hash);
    } else {
        navigateTo("home");
    }
}

function setupGlobalEventListeners() {
    // Customer / Persona Switcher
    customerSelect.addEventListener("change", async (e) => {
        activeCustomerId = e.target.value;
        const cust = allCustomers.find(c => c.customer_id === activeCustomerId);
        if (cust) {
            updateCustomerIdentityUI(cust);
        }
        loadWishlistFromStorage();
        await loadRecommendations(activeCustomerId);
        await loadCart(activeCustomerId);
        if (currentView === "orders") {
            await loadCustomerOrders(activeCustomerId);
        } else if (currentView === "profile") {
            renderProfileView(cust);
        } else if (currentView === "wishlist") {
            renderWishlistView();
        }
        showToast(`Switched active persona to ${cust ? cust.name : activeCustomerId}`, "success");
    });

    // Account Dropdown Toggle
    accountMenuBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        accountDropdown.classList.toggle("show");
    });

    document.addEventListener("click", (e) => {
        if (!accountDropdown.contains(e.target) && !accountMenuBtn.contains(e.target)) {
            accountDropdown.classList.remove("show");
        }
    });

    // Global Search Bar
    headerSearchBtn.addEventListener("click", executeHeaderSearch);
    globalSearchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") executeHeaderSearch();
    });
    globalSearchInput.addEventListener("input", (e) => {
        clearSearchBtn.style.display = e.target.value.trim() ? "block" : "none";
    });
    clearSearchBtn.addEventListener("click", () => {
        globalSearchInput.value = "";
        clearSearchBtn.style.display = "none";
        activeSearchQuery = "";
        filterAndRenderShopCatalog();
    });

    // Cart Drawer Controls
    cartToggleBtn.addEventListener("click", openCartDrawer);
    closeCartBtn.addEventListener("click", closeCartDrawer);
    cartDrawerOverlay.addEventListener("click", (e) => {
        if (e.target === cartDrawerOverlay) closeCartDrawer();
    });

    // Product Modal Close
    closeProductDetailBtn.addEventListener("click", closeProductModal);
    productDetailModal.addEventListener("click", (e) => {
        if (e.target === productDetailModal) closeProductModal();
    });

    // Admin Portal Toggle Button
    togglePortalModeBtn.addEventListener("click", () => {
        if (adminMode) {
            closeAdminPortal();
        } else {
            openAdminPortal("dashboard");
        }
    });

    // Refresh recommendations button on home
    const refreshHomeRecsBtn = document.getElementById("refreshHomeRecsBtn");
    if (refreshHomeRecsBtn) {
        refreshHomeRecsBtn.addEventListener("click", async () => {
            await loadRecommendations(activeCustomerId);
            showToast("AI recommendations re-computed from market basket view.", "success");
        });
    }

    // Shop Filters
    setupShopFilterListeners();

    // Admin Portal Rules Sliders & SQL Presets
    setupAdminLabListeners();
}

function navigateTo(viewName) {
    currentView = viewName;
    window.location.hash = viewName;

    // Hide all views
    document.querySelectorAll(".page-view").forEach(el => el.classList.remove("active"));
    
    // Show target view
    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) {
        targetView.classList.add("active");
    }

    // Update active nav links
    document.querySelectorAll(".nav-link").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.nav === viewName);
    });

    // Scroll to top
    window.scrollTo({ top: 0, behavior: "smooth" });

    // Page-specific initializers
    if (viewName === "shop") {
        filterAndRenderShopCatalog();
    } else if (viewName === "cart") {
        renderFullCartPage();
    } else if (viewName === "checkout") {
        renderCheckoutPage();
    } else if (viewName === "orders") {
        loadCustomerOrders(activeCustomerId);
    } else if (viewName === "wishlist") {
        renderWishlistView();
    } else if (viewName === "profile") {
        const cust = allCustomers.find(c => c.customer_id === activeCustomerId);
        renderProfileView(cust);
    }
}

// ==========================================================
// 2. CUSTOMER PROFILES & IDENTITY
// ==========================================================
async function loadCustomers() {
    try {
        const res = await fetch(`${API_BASE}/api/customers`);
        const json = await res.json();
        if (json.status === "success") {
            allCustomers = json.customers;

            customerSelect.innerHTML = allCustomers.map(c => {
                const domain = getDomainLabel(c.customer_id);
                return `<option value="${c.customer_id}">${c.customer_id}: ${c.name} (${domain})</option>`;
            }).join("");

            customerSelect.value = activeCustomerId;
            const currentCust = allCustomers.find(c => c.customer_id === activeCustomerId) || allCustomers[0];
            updateCustomerIdentityUI(currentCust);
        }
    } catch (err) {
        console.error("Failed to load customers:", err);
    }
}

function updateCustomerIdentityUI(cust) {
    if (!cust) return;
    const initials = cust.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
    
    // Navbar
    navCustomerName.innerText = cust.name.split(" ")[0];
    navCustomerAvatar.innerText = initials;

    // Dropdown
    document.getElementById("dropdownUserName").innerText = cust.name;
    document.getElementById("dropdownUserEmail").innerText = cust.email;
    document.getElementById("dropdownUserDomain").innerText = getDomainLabel(cust.customer_id);

    // Home hint
    const hint = document.getElementById("homeRecsHint");
    if (hint) {
        hint.innerText = `Tuned for ${cust.name} (${getDomainLabel(cust.customer_id)})`;
    }

    // Hero Promo Bundle updates based on persona domain
    updateHeroBundleForCustomer(cust.customer_id);
}

function getDomainLabel(cid) {
    const labels = {
        "C101": "Computing & Laptops",
        "C102": "Mobile & Audio",
        "C103": "Console Gaming",
        "C104": "Photography & Video",
        "C105": "Fitness & Wearables",
        "C106": "Home Office Ergonomics",
        "C107": "Specialty Coffee Bar",
        "C108": "Student Study Pack"
    };
    return labels[cid] || "General Tech Shopper";
}

function updateHeroBundleForCustomer(cid) {
    const titleEl = document.getElementById("heroBundleTitle");
    const descEl = document.getElementById("heroBundleDesc");
    const fbtHeadline = document.getElementById("fbtHeadline");
    const fbtExpl = document.getElementById("fbtExplanation");

    if (!titleEl) return;

    if (cid === "C104") {
        titleEl.innerText = "Photography Studio Kit";
        descEl.innerText = "Mirrorless 4K Camera + 50mm Prime Lens + 128GB High-Speed SD Card";
        if (fbtHeadline) fbtHeadline.innerText = "Creator Photography Bundle";
        if (fbtExpl) fbtExpl.innerHTML = "Customers who bought the <strong>Mirrorless 4K Camera</strong> frequently co-purchased the <strong>50mm Prime Lens</strong> and <strong>Camera Backpack</strong> (Confidence: 96.0%, Lift: 8.7x).";
    } else if (cid === "C107") {
        titleEl.innerText = "Artisan Espresso Suite";
        descEl.innerText = "15-Bar Espresso Brewer + Burr Grinder + Stainless Milk Pitcher";
        if (fbtHeadline) fbtHeadline.innerText = "Home Barista Starter Pack";
        if (fbtExpl) fbtExpl.innerHTML = "Customers who purchased the <strong>Espresso Brewer</strong> co-purchased the <strong>Milk Pitcher</strong> and <strong>Precision Scale</strong> (Confidence: 95.7%, Lift: 13.4x).";
    } else {
        titleEl.innerText = "Computing & Workstation Suite";
        descEl.innerText = "UltraBook Pro 15-inch Laptop + Multi-Port USB-C Hub + Waterproof Sleeve";
        if (fbtHeadline) fbtHeadline.innerText = "Workstation Productivity Bundle";
        if (fbtExpl) fbtExpl.innerHTML = "Customers who bought the <strong>UltraBook Pro Laptop</strong> frequently co-purchased the <strong>USB-C Hub</strong> and <strong>Wireless Mouse</strong> (Confidence: 100.0%, Lift: 23.7x).";
    }
}

// ==========================================================
// 3. CATALOG, CATEGORIES & SHOP SEARCH
// ==========================================================
async function loadCatalog() {
    try {
        const res = await fetch(`${API_BASE}/api/products`);
        const json = await res.json();
        if (json.status === "success") {
            allProducts = json.products;
            allCategories = json.categories;

            // Render Header Category Filter Dropdown
            headerCategorySelect.innerHTML = `<option value="">All Categories (${allProducts.length})</option>` + 
                allCategories.map(c => `<option value="${c.category_id}">${c.category_name}</option>`).join("");

            // Render Home Categories Grid
            renderHomeCategories();

            // Render Home Trending Products (Top Rated from catalog)
            renderHomeTrending();

            // Render Shop Category Sidebar
            renderShopCategoryFilters();

            // Render Full Categories View
            renderFullCategoriesView();

            // Render Shop Catalog
            filterAndRenderShopCatalog();
        }
    } catch (err) {
        console.error("Failed to load catalog:", err);
    }
}

function renderHomeCategories() {
    const grid = document.getElementById("homeCategoriesGrid");
    if (!grid) return;

    grid.innerHTML = allCategories.map(cat => {
        const count = allProducts.filter(p => p.category_id === cat.category_id).length;
        const iconSvg = getCategoryIconSvg(cat.category_id);
        return `
            <div class="category-card" onclick="filterShopByCategory('${cat.category_id}')">
                <div>
                    <div class="cat-icon-wrap">${iconSvg}</div>
                    <h3>${cat.category_name}</h3>
                    <p>${cat.description}</p>
                </div>
                <div class="cat-footer">
                    <span>${count} Products</span>
                    <span class="link-btn">Explore &rarr;</span>
                </div>
            </div>
        `;
    }).join("");
}

function renderFullCategoriesView() {
    const grid = document.getElementById("fullCategoriesGrid");
    if (!grid) return;

    grid.innerHTML = allCategories.map(cat => {
        const prods = allProducts.filter(p => p.category_id === cat.category_id);
        const iconSvg = getCategoryIconSvg(cat.category_id);
        return `
            <div class="category-card" onclick="filterShopByCategory('${cat.category_id}')">
                <div>
                    <div class="cat-icon-wrap">${iconSvg}</div>
                    <h3>${cat.category_name}</h3>
                    <p>${cat.description}</p>
                </div>
                <div class="cat-footer">
                    <span>${prods.length} Products Available</span>
                    <span class="link-btn">View Catalog &rarr;</span>
                </div>
            </div>
        `;
    }).join("");
}

function renderHomeTrending() {
    const grid = document.getElementById("homeTrendingGrid");
    if (!grid) return;

    // Pick top rated products with high stock
    const sorted = [...allProducts].sort((a, b) => (b.avg_rating || 0) - (a.avg_rating || 0));
    const trending = sorted.slice(0, 4);

    grid.innerHTML = trending.map(prod => createProductCardHtml(prod)).join("");
}

function renderShopCategoryFilters() {
    const container = document.getElementById("shopCategoryFilters");
    if (!container) return;

    let html = `
        <div class="category-filter-item ${activeCategoryFilter === '' ? 'active' : ''}" onclick="filterShopByCategory('')">
            <span>All Categories</span>
            <span class="cat-count-badge">${allProducts.length}</span>
        </div>
    `;

    html += allCategories.map(cat => {
        const count = allProducts.filter(p => p.category_id === cat.category_id).length;
        const isActive = activeCategoryFilter === cat.category_id ? "active" : "";
        return `
            <div class="category-filter-item ${isActive}" onclick="filterShopByCategory('${cat.category_id}')">
                <span>${cat.category_name}</span>
                <span class="cat-count-badge">${count}</span>
            </div>
        `;
    }).join("");

    container.innerHTML = html;
}

function setupShopFilterListeners() {
    const priceSlider = document.getElementById("priceRangeSlider");
    const priceDisplay = document.getElementById("priceRangeDisplay");
    const inStockCheckbox = document.getElementById("inStockOnlyCheckbox");
    const sortSelect = document.getElementById("shopSortSelect");
    const resetBtn = document.getElementById("resetFiltersBtn");

    if (priceSlider) {
        priceSlider.addEventListener("input", (e) => {
            activePriceMax = parseFloat(e.target.value);
            priceDisplay.innerText = `$${activePriceMax}`;
            filterAndRenderShopCatalog();
        });
    }

    if (inStockCheckbox) {
        inStockCheckbox.addEventListener("change", (e) => {
            activeInStockOnly = e.target.checked;
            filterAndRenderShopCatalog();
        });
    }

    document.querySelectorAll("input[name='ratingFilter']").forEach(radio => {
        radio.addEventListener("change", (e) => {
            activeRatingMin = parseFloat(e.target.value);
            filterAndRenderShopCatalog();
        });
    });

    if (sortSelect) {
        sortSelect.addEventListener("change", (e) => {
            activeSort = e.target.value;
            filterAndRenderShopCatalog();
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            activeCategoryFilter = "";
            activeSearchQuery = "";
            activePriceMax = 1500;
            activeInStockOnly = false;
            activeRatingMin = 0;
            activeSort = "featured";

            if (priceSlider) {
                priceSlider.value = 1500;
                priceDisplay.innerText = "$1500";
            }
            if (inStockCheckbox) inStockCheckbox.checked = false;
            if (sortSelect) sortSelect.value = "featured";
            const allRadio = document.querySelector("input[name='ratingFilter'][value='0']");
            if (allRadio) allRadio.checked = true;

            renderShopCategoryFilters();
            filterAndRenderShopCatalog();
            showToast("Filters reset to default.", "success");
        });
    }
}

function filterShopByCategory(catId) {
    activeCategoryFilter = catId;
    renderShopCategoryFilters();
    navigateTo("shop");
    filterAndRenderShopCatalog();
}

function executeHeaderSearch() {
    const query = globalSearchInput.value.trim();
    const cat = headerCategorySelect.value;
    activeSearchQuery = query.toLowerCase();
    activeCategoryFilter = cat;
    renderShopCategoryFilters();
    navigateTo("shop");
    filterAndRenderShopCatalog();
}

function filterAndRenderShopCatalog() {
    const grid = document.getElementById("shopCatalogGrid");
    const countEl = document.getElementById("shopProductCount");
    const filterBadge = document.getElementById("activeFilterBadge");

    if (!grid) return;

    let filtered = allProducts.filter(p => {
        const matchesCategory = !activeCategoryFilter || p.category_id === activeCategoryFilter;
        const matchesSearch = !activeSearchQuery || 
            p.product_name.toLowerCase().includes(activeSearchQuery) ||
            (p.brand && p.brand.toLowerCase().includes(activeSearchQuery)) ||
            (p.description && p.description.toLowerCase().includes(activeSearchQuery));
        const matchesPrice = p.price <= activePriceMax;
        const matchesStock = !activeInStockOnly || p.stock_quantity > 0;
        const matchesRating = (p.avg_rating || 0) >= activeRatingMin;

        return matchesCategory && matchesSearch && matchesPrice && matchesStock && matchesRating;
    });

    // Sorting
    if (activeSort === "price-asc") {
        filtered.sort((a, b) => a.price - b.price);
    } else if (activeSort === "price-desc") {
        filtered.sort((a, b) => b.price - a.price);
    } else if (activeSort === "rating") {
        filtered.sort((a, b) => (b.avg_rating || 0) - (a.avg_rating || 0));
    } else if (activeSort === "name") {
        filtered.sort((a, b) => a.product_name.localeCompare(b.product_name));
    }

    // Active filter badge
    if (activeCategoryFilter || activeSearchQuery) {
        const catObj = allCategories.find(c => c.category_id === activeCategoryFilter);
        const label = catObj ? catObj.category_name : `Search: "${activeSearchQuery}"`;
        filterBadge.innerText = label;
        filterBadge.style.display = "inline-flex";
    } else {
        filterBadge.style.display = "none";
    }

    countEl.innerText = `Showing ${filtered.length} of ${allProducts.length} products`;

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1.5rem; background: var(--bg-card); border-radius: var(--radius-lg);">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-muted); margin-bottom:1rem; opacity:0.6;">
                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <h3 style="font-family:var(--font-heading); margin-bottom:0.5rem;">No products match your criteria</h3>
                <p style="color:var(--text-secondary); margin-bottom:1.5rem;">Try adjusting your search terms or expanding your filter ranges.</p>
                <button class="btn-secondary" onclick="document.getElementById('resetFiltersBtn').click()">Reset All Filters</button>
            </div>
        `;
        return;
    }

    grid.innerHTML = filtered.map(prod => createProductCardHtml(prod)).join("");
}

function createProductCardHtml(prod, aiMeta = null) {
    const isWishlisted = currentWishlist.has(prod.product_id);
    const stockStatus = prod.stock_quantity < 50 ? 
        `<span class="stock-status-pill low-stock">Only ${prod.stock_quantity} left</span>` : 
        `<span class="stock-status-pill in-stock">In Stock</span>`;

    let aiReasonHtml = "";
    if (aiMeta) {
        let pillClass = "apriori";
        if (aiMeta.algorithm && aiMeta.algorithm.includes("Cosine")) pillClass = "content";
        else if (aiMeta.algorithm && aiMeta.algorithm.includes("Rating")) pillClass = "top-rated";

        aiReasonHtml = `
            <div class="ai-reason-pill ${pillClass}">
                ${aiMeta.reason}
                ${aiMeta.confidence ? `<br><strong>Confidence: ${(aiMeta.confidence * 100).toFixed(1)}% &bull; Lift: ${aiMeta.lift.toFixed(2)}x</strong>` : ''}
            </div>
        `;
    }

    return `
        <div class="product-card" id="card-${prod.product_id}">
            <div>
                <div class="card-top">
                    <span class="category-badge">${prod.category_name || ''}</span>
                    <button class="wishlist-toggle-btn ${isWishlisted ? 'active' : ''}" 
                            onclick="toggleWishlist('${prod.product_id}', event)" 
                            title="${isWishlisted ? 'Remove from Wishlist' : 'Save to Wishlist'}">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                        </svg>
                    </button>
                </div>

                <span class="card-brand">${prod.brand || 'Nexus'}</span>
                <h3 class="card-title" onclick="openProductModal('${prod.product_id}')">${escapeHtml(prod.product_name)}</h3>

                <div class="card-rating-row">
                    <span class="stars">${renderStars(prod.avg_rating || 4.8)}</span>
                    <span>${prod.avg_rating || 4.8} (${prod.review_count || 12})</span>
                </div>

                ${aiReasonHtml}
            </div>

            <div class="card-footer">
                <div>
                    <span class="card-price">${formatMoney(prod.price)}</span>
                    <div>${stockStatus}</div>
                </div>
                <button class="btn-add-cart" onclick="addProductToCart('${prod.product_id}', 1, event)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                    Add
                </button>
            </div>
        </div>
    `;
}

// ==========================================================
// 4. AI RECOMMENDATIONS PIPELINE (HOME VIEW)
// ==========================================================
async function loadRecommendations(customerId) {
    try {
        const res = await fetch(`${API_BASE}/api/recommendations/${customerId}?top_n=4`);
        const json = await res.json();
        if (json.status === "success") {
            const data = json.data;
            const recGrid = document.getElementById("homeRecommendationsGrid");
            if (recGrid) {
                if (!data.recommendations || data.recommendations.length === 0) {
                    recGrid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 2rem;">No active recommendations for this profile yet.</div>`;
                    return;
                }

                recGrid.innerHTML = data.recommendations.map(rec => {
                    return createProductCardHtml(rec, {
                        reason: rec.reason,
                        algorithm: rec.algorithm,
                        confidence: rec.confidence,
                        lift: rec.lift
                    });
                }).join("");
            }
        }
    } catch (err) {
        console.error("Error loading recommendations:", err);
    }
}

// Quick add bundle for home banner
async function quickAddBundle(productIds) {
    for (const pid of productIds) {
        await addProductToCart(pid, 1, null, false);
    }
    showToast("Added complete recommended bundle to your cart!", "success");
    openCartDrawer();
}

// ==========================================================
// 5. PRODUCT DETAILS MODAL (FULL EXPERIENCE)
// ==========================================================
async function openProductModal(productId) {
    productDetailModal.style.display = "flex";
    productDetailContent.innerHTML = `
        <div style="text-align: center; padding: 4rem; color: var(--text-muted);">
            <div class="pulse-dot" style="margin: 0 auto 1rem auto;"></div>
            Loading product specifications and DBMS reviews...
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/api/product/${productId}`);
        const json = await res.json();
        if (json.status === "success") {
            const prod = json.product;
            renderProductModalDetails(prod);
        } else {
            productDetailContent.innerHTML = `<p style="color:var(--accent-rose); text-align:center;">Product not found.</p>`;
        }
    } catch (err) {
        productDetailContent.innerHTML = `<p style="color:var(--accent-rose); text-align:center;">Error fetching product details.</p>`;
    }
}

function renderProductModalDetails(prod) {
    const isWishlisted = currentWishlist.has(prod.product_id);
    const iconSvg = getCategoryIconSvg(prod.category_id);

    // Frequently bought bundle
    let fbtHtml = "";
    if (prod.frequently_bought && prod.frequently_bought.length > 0) {
        const fbtItem = prod.frequently_bought[0];
        const bundleTotal = formatMoney(prod.price + fbtItem.price);
        fbtHtml = `
            <div class="detail-extra-section">
                <h4>Frequently Bought Together</h4>
                <div class="fbt-banner-card" style="padding: 1.25rem;">
                    <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
                        <div>
                            <p style="font-size:0.88rem; margin-bottom:0.35rem;">
                                <strong>${prod.product_name}</strong> + <strong>${fbtItem.product_name}</strong>
                            </p>
                            <span style="font-size:0.75rem; color:#818cf8;">
                                Apriori Mined Association (Confidence: ${(fbtItem.confidence * 100).toFixed(1)}%, Lift: ${fbtItem.lift.toFixed(2)}x)
                            </span>
                        </div>
                        <div style="display:flex; align-items:center; gap:1rem;">
                            <span style="font-size:1.25rem; font-weight:800;">${bundleTotal}</span>
                            <button class="btn-primary" onclick="quickAddBundle(['${prod.product_id}', '${fbtItem.product_id}'])">
                                Add Both to Cart
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Similar products
    let similarHtml = "";
    if (prod.similar_products && prod.similar_products.length > 0) {
        similarHtml = `
            <div class="detail-extra-section">
                <h4>Similar Items (Content-Based Cosine Match)</h4>
                <div class="mini-cards-row">
                    ${prod.similar_products.map(sim => `
                        <div class="mini-product-card">
                            <div>
                                <span style="font-size:0.7rem; color:var(--text-muted);">${sim.category_name}</span>
                                <h5 style="cursor:pointer;" onclick="openProductModal('${sim.product_id}')">${escapeHtml(sim.product_name)}</h5>
                            </div>
                            <div style="display:flex; align-items:center; justify-content:space-between; margin-top:0.75rem;">
                                <span>${formatMoney(sim.price)}</span>
                                <button class="btn-add-cart" style="padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="addProductToCart('${sim.product_id}', 1, event)">+ Add</button>
                            </div>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    // Customer Reviews
    let reviewsHtml = `
        <div class="detail-extra-section">
            <h4>Verified Customer Reviews (${prod.reviews.length})</h4>
            ${prod.reviews.length === 0 ? '<p style="color:var(--text-muted); font-size:0.85rem;">No reviews yet for this item.</p>' : `
                <div style="display:flex; flex-direction:column; gap:0.85rem;">
                    ${prod.reviews.map(r => `
                        <div style="background:var(--bg-card); padding:0.85rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
                            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.25rem;">
                                <strong style="font-size:0.85rem;">${escapeHtml(r.customer_name)}</strong>
                                <span style="font-size:0.75rem; color:var(--text-muted);">${r.review_date}</span>
                            </div>
                            <div class="stars" style="font-size:0.75rem; margin-bottom:0.35rem;">${renderStars(r.rating)}</div>
                            <p style="font-size:0.85rem; color:var(--text-secondary);">${escapeHtml(r.comment || 'Verified Purchase')}</p>
                        </div>
                    `).join("")}
                </div>
            `}
        </div>
    `;

    productDetailContent.innerHTML = `
        <div class="product-detail-top">
            <div class="detail-img-box">
                <div style="width:72px; height:72px; margin-bottom:1rem;">${iconSvg}</div>
                <span class="category-badge">${prod.category_name}</span>
            </div>

            <div>
                <div class="detail-breadcrumbs">Home &bull; ${prod.category_name} &bull; ${prod.brand || 'Gear'}</div>
                <h2 class="detail-title">${escapeHtml(prod.product_name)}</h2>

                <div class="detail-rating-row">
                    <span class="stars">${renderStars(prod.avg_rating || 4.8)}</span>
                    <span>${prod.avg_rating || 4.8} rating &bull; ${prod.review_count || 12} customer reviews</span>
                </div>

                <div class="detail-price-box">
                    <span class="detail-price">${formatMoney(prod.price)}</span>
                    <span class="stock-status-pill in-stock">In Stock: ${prod.stock_quantity} units</span>
                </div>

                <p class="detail-desc">${escapeHtml(prod.description || 'Premium grade hardware engineered for performance and longevity.')}</p>

                <div class="detail-actions-row">
                    <div class="item-qty-selector">
                        <button class="qty-btn" onclick="adjustModalQty(-1)">&minus;</button>
                        <input type="number" id="modalQtyInput" class="qty-input" value="1" min="1" max="${prod.stock_quantity}" readonly>
                        <button class="qty-btn" onclick="adjustModalQty(1)">&plus;</button>
                    </div>

                    <button class="detail-btn-cart" onclick="addModalProductToCart('${prod.product_id}')">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
                        Add to Cart
                    </button>

                    <button class="detail-btn-wishlist ${isWishlisted ? 'active' : ''}" onclick="toggleWishlist('${prod.product_id}', event)">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
                        ${isWishlisted ? 'Saved in Wishlist' : 'Add to Wishlist'}
                    </button>
                </div>
            </div>
        </div>

        ${fbtHtml}
        ${similarHtml}
        ${reviewsHtml}
    `;
}

function adjustModalQty(delta) {
    const input = document.getElementById("modalQtyInput");
    if (!input) return;
    let val = parseInt(input.value) + delta;
    if (val < 1) val = 1;
    input.value = val;
}

function addModalProductToCart(productId) {
    const input = document.getElementById("modalQtyInput");
    const qty = input ? parseInt(input.value) : 1;
    addProductToCart(productId, qty);
    closeProductModal();
}

function closeProductModal() {
    productDetailModal.style.display = "none";
}

// ==========================================================
// 6. SHOPPING CART OPERATIONS & DRAWER
// ==========================================================
async function loadCart(customerId) {
    try {
        const res = await fetch(`${API_BASE}/api/cart/${customerId}`);
        const json = await res.json();
        if (json.status === "success") {
            const count = json.items.reduce((acc, i) => acc + i.quantity, 0);
            cartCountBadge.innerText = count;
            navCartTotal.innerText = formatMoney(json.total_amount);
            drawerSubtotal.innerText = formatMoney(json.total_amount);

            renderDrawerCartItems(json.items);

            if (currentView === "cart") {
                renderFullCartPageContent(json);
            } else if (currentView === "checkout") {
                renderCheckoutSummaryContent(json);
            }
        }
    } catch (err) {
        console.error("Error loading cart:", err);
    }
}

async function addProductToCart(productId, quantity = 1, event = null, showNotification = true) {
    if (event) event.stopPropagation();

    try {
        const res = await fetch(`${API_BASE}/api/cart/add`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeCustomerId,
                product_id: productId,
                quantity: quantity
            })
        });
        const json = await res.json();
        if (json.status === "success") {
            if (showNotification) {
                const prod = allProducts.find(p => p.product_id === productId);
                const name = prod ? prod.product_name : "Product";
                showToast(`Added ${name} to cart!`, "success");
            }
            await loadCart(activeCustomerId);
            await loadRecommendations(activeCustomerId);
        } else {
            showToast(json.message || "Failed to add product to cart.", "error");
        }
    } catch (err) {
        showToast("Connection error while adding to cart.", "error");
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
            await loadCart(activeCustomerId);
            await loadRecommendations(activeCustomerId);
        }
    } catch (err) {
        showToast("Error removing item.", "error");
    }
}

function openCartDrawer() {
    cartDrawerOverlay.classList.add("open");
}

function closeCartDrawer() {
    cartDrawerOverlay.classList.remove("open");
}

function renderDrawerCartItems(items) {
    if (!drawerCartItems) return;

    if (!items || items.length === 0) {
        drawerCartItems.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); margin-top: 4rem;">
                <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity: 0.5; margin-bottom: 0.75rem;">
                    <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
                </svg>
                <p>Your cart is empty.</p>
            </div>
        `;
        return;
    }

    drawerCartItems.innerHTML = items.map(item => `
        <div class="cart-item-card" style="padding:0.85rem; grid-template-columns: 1fr auto;">
            <div>
                <h4 style="font-size:0.92rem; margin-bottom:0.2rem;">${escapeHtml(item.product_name)}</h4>
                <span style="font-size:0.78rem; color:var(--text-muted);">Qty: ${item.quantity} &bull; ${formatMoney(item.price)} each</span>
            </div>
            <div class="item-right-actions">
                <span class="item-subtotal" style="font-size:0.95rem;">${formatMoney(item.subtotal)}</span>
                <button class="btn-remove-item" onclick="removeProductFromCart('${item.product_id}')">Remove</button>
            </div>
        </div>
    `).join("");
}

// Full Cart Page
async function renderFullCartPage() {
    await loadCart(activeCustomerId);
}

function renderFullCartPageContent(cartData) {
    const itemsCol = document.getElementById("cartPageItems");
    const subtotalEl = document.getElementById("summarySubtotal");
    const taxEl = document.getElementById("summaryTax");
    const grandTotalEl = document.getElementById("summaryGrandTotal");
    const checkoutBtn = document.getElementById("proceedToCheckoutBtn");
    const meterText = document.getElementById("shippingMeterText");
    const meterFill = document.getElementById("shippingMeterFill");

    if (!itemsCol) return;

    if (!cartData.items || cartData.items.length === 0) {
        itemsCol.innerHTML = `
            <div style="background: var(--bg-card); border-radius: var(--radius-lg); padding: 4rem; text-align: center;">
                <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-muted); margin-bottom:1rem; opacity:0.5;">
                    <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
                </svg>
                <h3 style="font-family:var(--font-heading); margin-bottom:0.5rem;">Your cart is empty</h3>
                <p style="color:var(--text-secondary); margin-bottom:1.5rem;">Explore our 8 curated tech domains to add products.</p>
                <button class="btn-primary" onclick="navigateTo('shop')">Explore Shop Now</button>
            </div>
        `;
        if (checkoutBtn) checkoutBtn.disabled = true;
        subtotalEl.innerText = "$0.00";
        taxEl.innerText = "$0.00";
        grandTotalEl.innerText = "$0.00";
        return;
    }

    if (checkoutBtn) checkoutBtn.disabled = false;

    // Free shipping progress calculation (Threshold: $50)
    const threshold = 50.0;
    const currentTotal = cartData.total_amount;
    if (currentTotal >= threshold) {
        meterText.innerText = "You have unlocked FREE Express Shipping!";
        meterFill.style.width = "100%";
    } else {
        const remaining = (threshold - currentTotal).toFixed(2);
        const percent = Math.min(100, Math.round((currentTotal / threshold) * 100));
        meterText.innerText = `Add $${remaining} more for FREE Express Shipping`;
        meterFill.style.width = `${percent}%`;
    }

    const tax = roundMoney(cartData.total_amount * 0.08);
    const grandTotal = roundMoney(cartData.total_amount + tax);

    subtotalEl.innerText = formatMoney(cartData.total_amount);
    taxEl.innerText = formatMoney(tax);
    grandTotalEl.innerText = formatMoney(grandTotal);

    itemsCol.innerHTML = cartData.items.map(item => `
        <div class="cart-item-card">
            <div class="item-main-details">
                <h4>${escapeHtml(item.product_name)}</h4>
                <div class="item-unit-price">${formatMoney(item.price)} each &bull; Stock Available: ${item.stock_quantity}</div>
            </div>

            <div class="item-qty-selector">
                <button class="qty-btn" onclick="updateItemQuantity('${item.product_id}', ${item.quantity - 1})">&minus;</button>
                <input type="text" class="qty-input" value="${item.quantity}" readonly>
                <button class="qty-btn" onclick="updateItemQuantity('${item.product_id}', ${item.quantity + 1})">&plus;</button>
            </div>

            <div class="item-right-actions">
                <span class="item-subtotal">${formatMoney(item.subtotal)}</span>
                <button class="btn-remove-item" onclick="removeProductFromCart('${item.product_id}')">Remove</button>
            </div>
        </div>
    `).join("");
}

async function updateItemQuantity(productId, newQty) {
    if (newQty <= 0) {
        await removeProductFromCart(productId);
    } else {
        await addProductToCart(productId, newQty - 1, null, false);
        await loadCart(activeCustomerId);
    }
}

// ==========================================================
// 7. CHECKOUT & ACID TRANSACTION FLOW
// ==========================================================
async function renderCheckoutPage() {
    const cust = allCustomers.find(c => c.customer_id === activeCustomerId);
    if (cust) {
        document.getElementById("checkoutCustName").value = cust.name;
        document.getElementById("checkoutCustEmail").value = cust.email;
        document.getElementById("checkoutCustCity").value = `${cust.city}, United States`;
    }
    await loadCart(activeCustomerId);
}

function renderCheckoutSummaryContent(cartData) {
    const list = document.getElementById("checkoutItemsList");
    const subtotal = document.getElementById("checkoutSubtotal");
    const total = document.getElementById("checkoutTotal");

    if (!list) return;

    if (!cartData.items || cartData.items.length === 0) {
        list.innerHTML = `<p style="color:var(--text-muted); text-align:center; padding:1.5rem;">Cart is empty. <a href="javascript:void(0)" onclick="navigateTo('shop')" style="color:var(--primary);">Add items</a></p>`;
        document.getElementById("checkoutCommitBtn").disabled = true;
        document.getElementById("checkoutRollbackBtn").disabled = true;
        return;
    }

    document.getElementById("checkoutCommitBtn").disabled = false;
    document.getElementById("checkoutRollbackBtn").disabled = false;

    list.innerHTML = cartData.items.map(item => `
        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.5rem;">
            <span>${escapeHtml(item.product_name)} &times; ${item.quantity}</span>
            <strong>${formatMoney(item.subtotal)}</strong>
        </div>
    `).join("");

    subtotal.innerText = formatMoney(cartData.total_amount);
    total.innerText = formatMoney(cartData.total_amount);
}

async function executeCheckoutFlow(simulateFail = false) {
    const auditLog = document.getElementById("checkoutAuditLog");
    const auditConsole = document.getElementById("checkoutLogConsole");
    const statusPill = document.getElementById("auditStatusPill");

    auditLog.style.display = "block";
    statusPill.innerText = "Executing Transaction";
    statusPill.className = "audit-status";
    auditConsole.innerText = `[1] BEGIN TRANSACTION;\n[*] Customer: ${activeCustomerId}\n[*] Verifying inventory triggers and stock constraints...`;

    const paymentMethod = document.querySelector("input[name='checkoutPaymentMethod']:checked")?.value || "CREDIT_CARD";

    try {
        const res = await fetch(`${API_BASE}/api/checkout`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeCustomerId,
                payment_method: paymentMethod,
                simulate_fail: simulateFail
            })
        });

        const json = await res.json();
        if (json.status === "success") {
            statusPill.innerText = "COMMITTED";
            statusPill.className = "audit-status success";
            auditConsole.innerText = 
`[1] BEGIN TRANSACTION;
[2] Validated stock availability for all cart items.
[3] INSERT INTO orders (order_id: ${json.result.order_id}, amount: $${json.result.amount})
[4] INSERT INTO order_items (Trigger trg_decrement_product_stock fired)
[5] INSERT INTO payments (Method: ${paymentMethod}, Status: SUCCESS)
[6] DELETE FROM shopping_cart (Active cart cleared)
[7] [COMMIT] Transaction successfully committed! Inventory and orders persisted.`;

            showToast("Order placed successfully! ACID Transaction committed.", "success");
            await loadCart(activeCustomerId);
            await loadRecommendations(activeCustomerId);
            
            setTimeout(() => {
                navigateTo("orders");
            }, 2500);
        } else {
            statusPill.innerText = "ROLLED BACK";
            statusPill.className = "audit-status error";
            auditConsole.innerText = 
`[1] BEGIN TRANSACTION;
[2] Order header and items queued.
[!] ${json.result ? json.result.error : json.message}
[!] [ROLLBACK] Transaction rolled back completely!
[✓] Product inventory stock was restored to original values.
[✓] Shopping cart preserved without data loss. Partial writes aborted.`;

            showToast("Transaction rolled back! Stock and cart preserved.", "error");
        }
    } catch (err) {
        statusPill.innerText = "ERROR";
        auditConsole.innerText += "\n[!] Network or server communication error.";
        showToast("Error processing checkout transaction.", "error");
    }
}

// ==========================================================
// 8. ORDER HISTORY VIEW
// ==========================================================
async function loadCustomerOrders(customerId) {
    const container = document.getElementById("ordersListContainer");
    if (!container) return;

    container.innerHTML = `<div style="text-align:center; padding:3rem; color:var(--text-muted);">Loading purchase history from database...</div>`;

    try {
        const res = await fetch(`${API_BASE}/api/orders/${customerId}`);
        const json = await res.json();
        if (json.status === "success") {
            const orders = json.orders;
            if (!orders || orders.length === 0) {
                container.innerHTML = `
                    <div style="background:var(--bg-card); border-radius:var(--radius-lg); padding:3.5rem; text-align:center;">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-muted); margin-bottom:1rem; opacity:0.6;">
                            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
                        </svg>
                        <h3 style="font-family:var(--font-heading); margin-bottom:0.5rem;">No Completed Orders Yet</h3>
                        <p style="color:var(--text-secondary); margin-bottom:1.5rem;">Orders placed via checkout will appear here with full transaction records.</p>
                        <button class="btn-primary" onclick="navigateTo('shop')">Start Shopping</button>
                    </div>
                `;
                return;
            }

            container.innerHTML = orders.map(ord => `
                <div class="order-history-card">
                    <div class="order-card-header">
                        <div class="order-id-group">
                            <strong>${ord.order_id}</strong>
                            <span class="order-date-text">&bull; ${ord.order_date}</span>
                        </div>
                        <span class="order-status-badge">${ord.order_status}</span>
                    </div>

                    <div class="table-responsive">
                        <table class="order-items-table">
                            <thead>
                                <tr>
                                    <th>Item</th>
                                    <th>Category</th>
                                    <th>Unit Price</th>
                                    <th>Qty</th>
                                    <th style="text-align:right;">Subtotal</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${ord.items.map(item => `
                                    <tr>
                                        <td><strong>${escapeHtml(item.product_name)}</strong></td>
                                        <td><span class="category-badge">${item.category_name}</span></td>
                                        <td>${formatMoney(item.unit_price)}</td>
                                        <td>${item.quantity}</td>
                                        <td style="text-align:right;"><strong>${formatMoney(item.subtotal)}</strong></td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>

                    <div class="order-card-footer">
                        <span>Paid via <strong>${ord.payment_method}</strong></span>
                        <div>Total: <strong style="font-size:1.15rem; color:var(--text-primary);">${formatMoney(ord.total_amount)}</strong></div>
                    </div>
                </div>
            `).join("");
        }
    } catch (err) {
        container.innerHTML = `<p style="color:var(--accent-rose); text-align:center;">Failed to load order history.</p>`;
    }
}

// ==========================================================
// 9. WISHLIST MANAGEMENT (CLIENT-SIDE PERSISTENCE)
// ==========================================================
function loadWishlistFromStorage() {
    try {
        const stored = localStorage.getItem(`nexus_wishlist_${activeCustomerId}`);
        if (stored) {
            currentWishlist = new Set(JSON.parse(stored));
        } else {
            currentWishlist = new Set();
        }
    } catch (e) {
        currentWishlist = new Set();
    }
    updateWishlistBadge();
}

function saveWishlistToStorage() {
    try {
        localStorage.setItem(`nexus_wishlist_${activeCustomerId}`, JSON.stringify(Array.from(currentWishlist)));
    } catch (e) {}
    updateWishlistBadge();
}

function updateWishlistBadge() {
    if (wishlistCountBadge) {
        wishlistCountBadge.innerText = currentWishlist.size;
    }
}

function toggleWishlist(productId, event = null) {
    if (event) event.stopPropagation();

    const prod = allProducts.find(p => p.product_id === productId);
    const name = prod ? prod.product_name : "Product";

    if (currentWishlist.has(productId)) {
        currentWishlist.delete(productId);
        showToast(`Removed ${name} from your wishlist.`, "success");
    } else {
        currentWishlist.add(productId);
        showToast(`Saved ${name} to your wishlist!`, "success");
    }

    saveWishlistToStorage();

    // Re-render card toggles if visible
    document.querySelectorAll(`.wishlist-toggle-btn[onclick*="${productId}"]`).forEach(btn => {
        btn.classList.toggle("active", currentWishlist.has(productId));
    });

    if (currentView === "wishlist") {
        renderWishlistView();
    }
}

function clearWishlist() {
    currentWishlist.clear();
    saveWishlistToStorage();
    renderWishlistView();
    showToast("Wishlist cleared.", "success");
}

function renderWishlistView() {
    const grid = document.getElementById("wishlistCardsGrid");
    if (!grid) return;

    if (currentWishlist.size === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 4rem; background: var(--bg-card); border-radius: var(--radius-lg);">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-muted); margin-bottom:1rem; opacity:0.6;">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                </svg>
                <h3 style="font-family:var(--font-heading); margin-bottom:0.5rem;">Your Wishlist is Empty</h3>
                <p style="color:var(--text-secondary); margin-bottom:1.5rem;">Click the heart icon on any product to save it here for later.</p>
                <button class="btn-primary" onclick="navigateTo('shop')">Browse Products</button>
            </div>
        `;
        return;
    }

    const savedProducts = allProducts.filter(p => currentWishlist.has(p.product_id));
    grid.innerHTML = savedProducts.map(p => createProductCardHtml(p)).join("");
}

// ==========================================================
// 10. CUSTOMER PROFILE VIEW
// ==========================================================
function renderProfileView(cust) {
    if (!cust) return;
    const initials = cust.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();

    document.getElementById("profileAvatarLarge").innerText = initials;
    document.getElementById("profileCustomerName").innerText = cust.name;
    document.getElementById("profileDomainPill").innerText = `${getDomainLabel(cust.customer_id)} Persona`;
    document.getElementById("profileMetaLine").innerHTML = `Customer ID: <strong>${cust.customer_id}</strong> &bull; ${cust.city} &bull; ${cust.email}`;

    document.getElementById("profileTotalOrders").innerText = cust.total_orders || 0;
    document.getElementById("profileLifetimeSpend").innerText = formatMoney(cust.lifetime_spend || 0);
    document.getElementById("profileCartCount").innerText = cartCountBadge.innerText || 0;
    document.getElementById("profileWishlistCount").innerText = currentWishlist.size || 0;
}

// ==========================================================
// 11. ADMIN & INTELLIGENCE LAB PORTAL
// ==========================================================
function openAdminPortal(tabName = "dashboard") {
    adminMode = true;
    adminPortalContainer.style.display = "flex";
    portalModeBtnText.innerText = "Exit Admin Lab";
    togglePortalModeBtn.classList.add("active");
    switchAdminTab(tabName);
}

function closeAdminPortal() {
    adminMode = false;
    adminPortalContainer.style.display = "none";
    portalModeBtnText.innerText = "Admin & Database Lab";
    togglePortalModeBtn.classList.remove("active");
}

function switchAdminTab(tabName) {
    activeAdminTab = tabName;

    // Update active nav button
    document.querySelectorAll(".admin-nav-item").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.adminTab === tabName);
    });

    // Update active content pane
    document.querySelectorAll(".admin-tab-pane").forEach(pane => {
        pane.classList.remove("active");
    });
    const targetPane = document.getElementById(`admin-tab-${tabName}`);
    if (targetPane) targetPane.classList.add("active");

    // Load data for the selected admin tab
    if (tabName === "dashboard") {
        loadAdminOverview();
    } else if (tabName === "inventory") {
        renderAdminInventory();
    } else if (tabName === "orders") {
        loadAdminOrders();
    } else if (tabName === "customers") {
        renderAdminCustomers();
    } else if (tabName === "rules") {
        loadRules();
    } else if (tabName === "dbms") {
        loadDbmsView("v_market_basket");
    }
}

async function loadAdminOverview() {
    try {
        const res = await fetch(`${API_BASE}/api/admin/overview`);
        const json = await res.json();
        if (json.status === "success") {
            const ov = json.overview;
            document.getElementById("adminKpiRevenue").innerText = formatMoney(ov.gross_revenue);
            document.getElementById("adminKpiOrders").innerText = ov.total_orders;
            document.getElementById("adminKpiCustomers").innerText = ov.total_customers;
            document.getElementById("adminKpiRules").innerText = ov.total_rules;

            // Domain sales
            const salesBody = document.getElementById("adminDomainSalesBody");
            salesBody.innerHTML = ov.category_sales.map(s => `
                <tr>
                    <td><strong>${escapeHtml(s.category_name)}</strong></td>
                    <td>${s.items_sold} items</td>
                    <td><strong>${formatMoney(s.revenue)}</strong></td>
                </tr>
            `).join("");

            // Recent orders
            const recBody = document.getElementById("adminRecentOrdersBody");
            recBody.innerHTML = ov.recent_orders.map(o => `
                <tr>
                    <td><strong>${o.order_id}</strong></td>
                    <td>${escapeHtml(o.customer_name)}</td>
                    <td>${o.order_date}</td>
                    <td>${formatMoney(o.total_amount)}</td>
                    <td>${o.payment_method}</td>
                    <td><span class="stock-status-pill in-stock">${o.order_status}</span></td>
                </tr>
            `).join("");
        }
    } catch (err) {
        console.error("Error loading admin overview:", err);
    }
}

function renderAdminInventory() {
    const tbody = document.getElementById("adminInventoryBody");
    if (!tbody) return;

    tbody.innerHTML = allProducts.map(p => {
        const isLow = p.stock_quantity < 50;
        const status = isLow ? 
            `<span class="stock-status-pill low-stock">Low Stock (${p.stock_quantity})</span>` :
            `<span class="stock-status-pill in-stock">Adequate (${p.stock_quantity})</span>`;
        return `
            <tr>
                <td><strong>${p.product_id}</strong></td>
                <td>${escapeHtml(p.product_name)}</td>
                <td><span class="category-badge">${p.category_name}</span></td>
                <td>${formatMoney(p.price)}</td>
                <td><strong>${p.stock_quantity}</strong> units</td>
                <td>${status}</td>
            </tr>
        `;
    }).join("");
}

async function loadAdminOrders() {
    const tbody = document.getElementById("adminAllOrdersBody");
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/api/analytics/view/v_market_basket`);
        const json = await res.json();
        if (json.status === "success") {
            tbody.innerHTML = json.data.map(o => `
                <tr>
                    <td><strong>${o.order_id}</strong></td>
                    <td>Customer: ${o.customer_id}</td>
                    <td>${o.order_date}</td>
                    <td><strong>${formatMoney(o.order_total)}</strong></td>
                    <td>CREDIT_CARD</td>
                    <td><span class="stock-status-pill in-stock">COMPLETED</span></td>
                </tr>
            `).join("");
        }
    } catch (err) {
        console.error("Error loading all orders:", err);
    }
}

function renderAdminCustomers() {
    const tbody = document.getElementById("adminCustomersBody");
    if (!tbody) return;

    tbody.innerHTML = allCustomers.map(c => `
        <tr>
            <td><strong>${c.customer_id}</strong></td>
            <td>${escapeHtml(c.name)}</td>
            <td>${escapeHtml(c.city || 'Seattle')}</td>
            <td>${c.total_orders || 0} orders</td>
            <td><strong>${formatMoney(c.lifetime_spend || 0)}</strong></td>
        </tr>
    `).join("");
}

// Apriori Rules Explorer in Admin
function setupAdminLabListeners() {
    const minConfSlider = document.getElementById("minConfSlider");
    const minLiftSlider = document.getElementById("minLiftSlider");
    const confVal = document.getElementById("confValueDisplay");
    const liftVal = document.getElementById("liftValueDisplay");
    const applyBtn = document.getElementById("applyRuleFilterBtn");

    if (minConfSlider) {
        minConfSlider.addEventListener("input", (e) => {
            confVal.innerText = `${Math.round(e.target.value * 100)}%`;
        });
    }

    if (minLiftSlider) {
        minLiftSlider.addEventListener("input", (e) => {
            liftVal.innerText = `${parseFloat(e.target.value).toFixed(1)}x`;
        });
    }

    if (applyBtn) {
        applyBtn.addEventListener("click", loadRules);
    }

    // DBMS View buttons
    document.querySelectorAll(".view-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".view-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            loadDbmsView(btn.dataset.view);
        });
    });

    // SQL Runner
    const runSqlBtn = document.getElementById("runSqlBtn");
    if (runSqlBtn) runSqlBtn.addEventListener("click", executeUserSql);

    document.querySelectorAll(".sql-preset-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const sqlInput = document.getElementById("sqlQueryInput");
            if (sqlInput) {
                sqlInput.value = btn.dataset.query;
                executeUserSql();
            }
        });
    });
}

async function loadRules() {
    const minConf = document.getElementById("minConfSlider")?.value || 0.5;
    const minLift = document.getElementById("minLiftSlider")?.value || 1.2;
    const tbody = document.getElementById("rulesTableBody");

    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:var(--text-muted);">Mining association rules...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/api/analytics/rules?min_confidence=${minConf}&min_lift=${minLift}&limit=50`);
        const json = await res.json();
        if (json.status === "success") {
            if (json.rules.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:2rem;">No rules meet these confidence/lift constraints.</td></tr>`;
                return;
            }

            tbody.innerHTML = json.rules.map((r, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td><strong>${escapeHtml(r.antecedent_names.join(" + "))}</strong></td>
                    <td style="color:#818cf8; font-weight:700;">&rarr;</td>
                    <td><strong style="color:#38bdf8;">${escapeHtml(r.consequent_names.join(" + "))}</strong></td>
                    <td>${(r.support * 100).toFixed(1)}%</td>
                    <td><strong>${(r.confidence * 100).toFixed(1)}%</strong></td>
                    <td><span style="color:#34d399; font-weight:700;">${r.lift.toFixed(2)}x</span></td>
                </tr>
            `).join("");
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--accent-rose);">Failed to mine rules.</td></tr>`;
    }
}

async function loadDbmsView(viewName) {
    const thead = document.getElementById("dbmsViewHead");
    const tbody = document.getElementById("dbmsViewBody");

    if (!thead || !tbody) return;

    try {
        const res = await fetch(`${API_BASE}/api/analytics/view/${viewName}`);
        const json = await res.json();
        if (json.status === "success") {
            thead.innerHTML = `<tr>${json.columns.map(c => `<th>${c}</th>`).join("")}</tr>`;
            tbody.innerHTML = json.data.map(row => `
                <tr>${json.columns.map(c => `<td>${row[c] !== null ? escapeHtml(String(row[c])) : '<em>null</em>'}</td>`).join("")}</tr>
            `).join("");
        }
    } catch (err) {
        console.error("Error loading view:", err);
    }
}

async function executeUserSql() {
    const sqlInput = document.getElementById("sqlQueryInput");
    const errorMsg = document.getElementById("sqlErrorMsg");
    const resultWrap = document.getElementById("sqlResultWrap");
    const resultHead = document.getElementById("sqlResultHead");
    const resultBody = document.getElementById("sqlResultBody");

    const query = sqlInput.value.trim();
    errorMsg.style.display = "none";
    resultWrap.style.display = "none";

    try {
        const res = await fetch(`${API_BASE}/api/sql/execute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query })
        });
        const json = await res.json();
        if (json.status === "success") {
            resultWrap.style.display = "block";
            resultHead.innerHTML = `<tr>${json.columns.map(c => `<th>${c}</th>`).join("")}</tr>`;
            resultBody.innerHTML = json.rows.map(row => `
                <tr>${json.columns.map(c => `<td>${row[c] !== null ? escapeHtml(String(row[c])) : '<em>null</em>'}</td>`).join("")}</tr>
            `).join("");
            showToast(`Query executed: returned ${json.row_count} rows.`, "success");
        } else {
            errorMsg.style.display = "block";
            errorMsg.innerText = json.message || "SQL syntax or execution error.";
        }
    } catch (err) {
        errorMsg.style.display = "block";
        errorMsg.innerText = "Failed to connect to backend SQL runner.";
    }
}

// ==========================================================
// 12. HELPER UTILITIES
// ==========================================================
function formatMoney(amount) {
    return "$" + parseFloat(amount || 0).toFixed(2);
}

function roundMoney(amount) {
    return Math.round((parseFloat(amount || 0) + Number.EPSILON) * 100) / 100;
}

function renderStars(rating) {
    const r = Math.round(rating || 5);
    return "★".repeat(r) + "☆".repeat(5 - r);
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

function showToast(message, type = "success") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span style="font-weight:700; color:${type === 'success' ? '#10b981' : '#f43f5e'};">
            ${type === 'success' ? '✓' : '⚠'}
        </span>
        <div>${escapeHtml(message)}</div>
    `;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3500);
}

function scrollToSection(sectionId) {
    const el = document.getElementById(sectionId);
    if (el) {
        el.scrollIntoView({ behavior: "smooth" });
    }
}

function getCategoryIconSvg(catId) {
    const icons = {
        "CAT01": `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`,
        "CAT02": `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>`,
        "CAT03": `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="8" cy="12" r="2"/><line x1="14" y1="10" x2="18" y2="10"/><line x1="16" y1="8" x2="16" y2="12"/></svg>`,
        "CAT04": `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>`,
        "CAT05": `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><polyline points="12 9 12 12 13.5 13.5"/><path d="M16.51 17.35l-.35 3.83a2 2 0 0 1-2 1.82H9.83a2 2 0 0 1-2-1.82l-.35-3.83m.01-10.7l.35-3.83A2 2 0 0 1 9.83 1h4.35a2 2 0 0 1 2 1.82l.35 3.83"/></svg>`,
        "CAT06": `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
        "CAT07": `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/></svg>`,
        "CAT08": `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>`
    };
    return icons[catId] || `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>`;
}
