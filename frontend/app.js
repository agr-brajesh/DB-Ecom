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

// Phase 3: Database-backed Wishlist and Search Debounce
let currentWishlist = new Set();
let searchDebounceTimer = null;

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
const searchSuggestionsBox = document.getElementById("searchSuggestionsBox");
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

// Modals
const productDetailModal = document.getElementById("productDetailModal");
const productDetailContent = document.getElementById("productDetailContent");
const closeProductDetailBtn = document.getElementById("closeProductDetailBtn");
const orderConfirmationModal = document.getElementById("orderConfirmationModal");

// ==========================================================
// 1. INITIALIZATION & ROUTING
// ==========================================================
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initApp);
} else {
    initApp();
}

async function initApp() {
    setupGlobalEventListeners();
    await loadWishlistFromDb(activeCustomerId);
    await loadCustomers();
    await loadCatalog();
    await loadHomeDynamicSections();
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
    // Direct click listeners on all navigation links and elements with data-nav
    document.querySelectorAll("[data-nav]").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const nav = btn.getAttribute("data-nav");
            if (nav) {
                e.preventDefault();
                navigateTo(nav);
            }
        });
    });

    // Customer / Persona Switcher
    if (customerSelect) {
        customerSelect.addEventListener("change", async (e) => {
            activeCustomerId = e.target.value;
            const cust = allCustomers.find(c => c.customer_id === activeCustomerId);
            if (cust) {
                updateCustomerIdentityUI(cust);
            }
            await loadWishlistFromDb(activeCustomerId);
            await loadRecommendations(activeCustomerId);
            await loadCart(activeCustomerId);
            if (currentView === "orders") {
                await loadCustomerOrders(activeCustomerId);
            } else if (currentView === "profile") {
                await renderProfileView(cust);
            } else if (currentView === "wishlist") {
                await renderWishlistView();
            }
            showToast(`Switched active persona to ${cust ? cust.name : activeCustomerId}`, "success");
        });
    }

    // Account Dropdown Toggle
    if (accountMenuBtn && accountDropdown) {
        accountMenuBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            accountDropdown.classList.toggle("show");
        });

        document.addEventListener("click", (e) => {
            if (!accountDropdown.contains(e.target) && !accountMenuBtn.contains(e.target)) {
                accountDropdown.classList.remove("show");
            }
            // Click outside search bar hides suggestions
            if (!e.target.closest(".nav-search-bar")) {
                hideSearchSuggestions();
            }
        });
    }

    // Global Live Search Bar
    if (headerSearchBtn) headerSearchBtn.addEventListener("click", executeHeaderSearch);
    if (globalSearchInput) {
        globalSearchInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") executeHeaderSearch();
            else if (e.key === "Escape") hideSearchSuggestions();
        });
        globalSearchInput.addEventListener("input", (e) => {
            const val = e.target.value.trim();
            if (clearSearchBtn) clearSearchBtn.style.display = val ? "block" : "none";
            clearTimeout(searchDebounceTimer);
            if (val.length < 2) {
                hideSearchSuggestions();
                return;
            }
            searchDebounceTimer = setTimeout(() => {
                fetchSearchSuggestions(val);
            }, 220);
        });
    }
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener("click", () => {
            if (globalSearchInput) globalSearchInput.value = "";
            clearSearchBtn.style.display = "none";
            hideSearchSuggestions();
            activeSearchQuery = "";
            filterAndRenderShopCatalog();
        });
    }

    // Payment method radio change in checkout
    document.querySelectorAll("input[name='checkoutPaymentMethod']").forEach(radio => {
        radio.addEventListener("change", updateCheckoutPaymentMethodLabel);
    });

    // Cart Drawer Controls
    if (cartToggleBtn) cartToggleBtn.addEventListener("click", openCartDrawer);
    if (closeCartBtn) closeCartBtn.addEventListener("click", closeCartDrawer);
    if (cartDrawerOverlay) {
        cartDrawerOverlay.addEventListener("click", (e) => {
            if (e.target === cartDrawerOverlay) closeCartDrawer();
        });
    }

    // Product Modal Close
    if (closeProductDetailBtn) closeProductDetailBtn.addEventListener("click", closeProductModal);
    if (productDetailModal) {
        productDetailModal.addEventListener("click", (e) => {
            if (e.target === productDetailModal) closeProductModal();
        });
    }

    // Admin Portal Toggle Button
    if (togglePortalModeBtn) {
        togglePortalModeBtn.addEventListener("click", () => {
            if (adminMode) {
                closeAdminPortal();
            } else {
                openAdminPortal("dashboard");
            }
        });
    }

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
    if (adminMode) {
        closeAdminPortal();
    }
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

// Global window bindings to guarantee accessibility for inline onclick handlers
window.navigateTo = navigateTo;
window.openProductModal = openProductModal;
window.closeProductModal = closeProductModal;
window.filterByCategory = filterByCategory;
window.toggleWishlist = toggleWishlist;
window.addProductToCart = addProductToCart;
window.openCartDrawer = openCartDrawer;
window.closeCartDrawer = closeCartDrawer;
window.openAdminPortal = openAdminPortal;
window.closeAdminPortal = closeAdminPortal;
window.switchAdminTab = switchAdminTab;
window.executeHeaderSearch = executeHeaderSearch;
window.filterAndRenderShopCatalog = filterAndRenderShopCatalog;
window.resetShopFilters = resetShopFilters;
window.executeCustomerOrder = executeCustomerOrder;
window.closeConfirmationModal = closeConfirmationModal;
window.runAdminAcidSimulation = runAdminAcidSimulation;
window.adjustModalQty = adjustModalQty;
window.updateItemQuantity = updateItemQuantity;
window.removeFromCart = removeFromCart;
window.moveWishlistToCart = moveWishlistToCart;
window.quickAddBundle = quickAddBundle;
window.recordSessionEvent = recordSessionEvent;

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

            // Render Home Categories Grid (Initial)
            renderHomeCategories();

            // Render Home Trending Products (Initial fallback)
            renderHomeTrending();

            // Load Dynamic Homepage Sections backed by SQLite views
            await loadHomeDynamicSections();

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

async function loadHomeDynamicSections() {
    try {
        const res = await fetch(`${API_BASE}/api/home/sections`);
        const json = await res.json();
        if (json.status === "success") {
            const sec = json.sections;

            // Popular / Best-sellers from v_product_performance
            const trendGrid = document.getElementById("homeTrendingGrid");
            if (trendGrid && sec.featured && sec.featured.length > 0) {
                trendGrid.innerHTML = sec.featured.map(prod => createProductCardHtml(prod)).join("");
            }

            // Category counts from SQLite
            if (sec.categories && sec.categories.length > 0) {
                const homeCatGrid = document.getElementById("homeCategoriesGrid");
                if (homeCatGrid) {
                    homeCatGrid.innerHTML = sec.categories.map(cat => {
                        const iconSvg = getCategoryIconSvg(cat.category_id);
                        return `
                            <div class="category-card" onclick="filterShopByCategory('${cat.category_id}')">
                                <div>
                                    <div class="cat-icon-wrap">${iconSvg}</div>
                                    <h3>${cat.category_name}</h3>
                                    <p>${cat.description}</p>
                                </div>
                                <div class="cat-footer">
                                    <span>${cat.product_count} Products</span>
                                    <span class="link-btn">Explore &rarr;</span>
                                </div>
                            </div>
                        `;
                    }).join("");
                }
            }

            // Frequent product pair / bundle from v_frequent_product_pairs
            if (sec.bundle) {
                const b = sec.bundle;
                const fbtHeadline = document.getElementById("fbtHeadline");
                const fbtExpl = document.getElementById("fbtExplanation");
                const bundlePriceEl = document.querySelector(".fbt-bundle-price");
                const savingEl = document.querySelector(".fbt-saving-tag");
                const ctaBtn = document.querySelector(".fbt-cta button");

                if (fbtHeadline) fbtHeadline.innerText = `Frequent Co-Purchase Pair: ${b.product1.name} + ${b.product2.name}`;
                if (fbtExpl) fbtExpl.innerHTML = `Identified by SQL analytical view <code>v_frequent_product_pairs</code> (${b.co_purchase_count} co-purchase orders recorded in database). Buy both together and save 10%!`;
                if (bundlePriceEl) bundlePriceEl.innerText = formatMoney(b.bundle_price);
                if (savingEl) savingEl.innerText = `Save ${formatMoney(b.savings)} (Regular: ${formatMoney(b.original_price)})`;
                if (ctaBtn) {
                    ctaBtn.onclick = () => quickAddBundle([b.product1.id, b.product2.id]);
                }
            }
        }
    } catch (err) {
        console.error("Error loading dynamic home sections:", err);
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

// Phase 5: Lightweight session event recorder
async function recordSessionEvent(customerId, productId = null, eventType = "PRODUCT_VIEW") {
    if (!customerId) return;
    try {
        await fetch(`${API_BASE}/api/events/record`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: customerId,
                product_id: productId,
                event_type: eventType
            })
        });
    } catch (e) {
        // Silent fail for non-blocking analytics
    }
}

async function recordSearch(query) {
    if (!query || query.length < 2) return;
    try {
        await fetch(`${API_BASE}/api/search/record`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeCustomerId,
                query: query
            })
        });
        await recordSessionEvent(activeCustomerId, null, "SEARCH");
    } catch (e) {}
}

async function fetchSearchSuggestions(term) {
    if (!searchSuggestionsBox) return;
    try {
        const res = await fetch(`${API_BASE}/api/search/suggestions?q=${encodeURIComponent(term)}`);
        const json = await res.json();
        if (json.status === "success" && json.suggestions && json.suggestions.length > 0) {
            searchSuggestionsBox.innerHTML = json.suggestions.map(s => `
                <div class="search-suggestion-item" onclick="selectSearchSuggestion('${s.type}', '${s.id}', '${escapeHtml(s.title)}')">
                    <div class="suggestion-info">
                        <span class="suggestion-title">${escapeHtml(s.title)}</span>
                        <span class="suggestion-subtitle">${escapeHtml(s.subtitle)}</span>
                    </div>
                    <span class="suggestion-tag ${s.type}">${s.type.toUpperCase()}</span>
                </div>
            `).join("");
            searchSuggestionsBox.style.display = "flex";
        } else {
            hideSearchSuggestions();
        }
    } catch (e) {
        hideSearchSuggestions();
    }
}

function hideSearchSuggestions() {
    if (searchSuggestionsBox) searchSuggestionsBox.style.display = "none";
}

function selectSearchSuggestion(type, id, title) {
    hideSearchSuggestions();
    recordSearch(title);
    if (type === "category") {
        filterShopByCategory(id);
    } else {
        openProductModal(id);
    }
}

function executeHeaderSearch() {
    const query = globalSearchInput.value.trim();
    const cat = headerCategorySelect.value;
    activeSearchQuery = query.toLowerCase();
    activeCategoryFilter = cat;
    if (query) {
        recordSearch(query);
    }
    hideSearchSuggestions();
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
    } else if (activeSort === "popularity") {
        filtered.sort((a, b) => (b.review_count || 0) - (a.review_count || 0));
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
    let stockStatus = "";
    if (prod.stock_quantity <= 0) {
        stockStatus = `<span class="stock-status-pill out-of-stock">Out of Stock</span>`;
    } else if (prod.stock_quantity < 50) {
        stockStatus = `<span class="stock-status-pill low-stock">Only ${prod.stock_quantity} left</span>`;
    } else {
        stockStatus = `<span class="stock-status-pill in-stock">In Stock (${prod.stock_quantity})</span>`;
    }

    let aiReasonHtml = "";
    if (aiMeta) {
        let pillClass = "apriori";
        let typeBadge = "";
        const recType = aiMeta.recommendation_type || "";
        if (recType === "BASED_ON_RECENT_SEARCH" || (aiMeta.algorithm && aiMeta.algorithm.includes("Search"))) {
            pillClass = "search";
            typeBadge = "&#128269; Based On Recent Search";
        } else if (recType === "COMPLETE_YOUR_SETUP" || recType === "FREQUENTLY_BOUGHT_TOGETHER") {
            pillClass = "setup";
            typeBadge = recType === "COMPLETE_YOUR_SETUP" ? "&#9889; Complete Your Setup" : "&#128279; Frequently Bought Together";
        } else if (recType === "BECAUSE_YOU_VIEWED" || (aiMeta.algorithm && aiMeta.algorithm.includes("Cosine"))) {
            pillClass = "content";
            typeBadge = "&#128065; Because You Viewed This";
        } else if (recType === "BEST_ALTERNATIVES") {
            pillClass = "alternative";
            typeBadge = "&#128260; In-Stock Alternative";
        } else if (recType === "PERSONALIZED_FOR_YOU") {
            pillClass = "personalized";
            typeBadge = "&#127919; Personalized For You";
        } else {
            pillClass = "top-rated";
            typeBadge = "&#11088; Community Top Pick";
        }

        const reasonsList = (aiMeta.reasons && aiMeta.reasons.length ? aiMeta.reasons : [aiMeta.reason || "Recommended for your profile"]).slice(0, 3);
        const matchBadge = aiMeta.ai_match || "AI Match";
        const matchStrength = aiMeta.match_strength || "Strong Match";

        aiReasonHtml = `
            <div class="ai-explanation-card ${pillClass}">
                <div class="ai-explanation-head">
                    <span class="ai-type-pill ${pillClass}">${typeBadge}</span>
                    <span class="ai-match-badge" title="${matchStrength}">${escapeHtml(matchBadge)}</span>
                </div>
                <div class="ai-reasons-preview">
                    ${reasonsList.map(r => `
                        <div class="ai-reason-line">
                            <span class="ai-check-icon">&#10003;</span>
                            <span class="ai-reason-text">${escapeHtml(r)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    const isOutOfStock = prod.stock_quantity <= 0;

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
                ${isOutOfStock ? `
                    <button class="btn-add-cart" style="background:rgba(244,63,94,0.15); color:#fb7185; border:1px solid rgba(244,63,94,0.3); font-size:0.75rem; padding:0.4rem 0.65rem;" onclick="openProductModal('${prod.product_id}')">
                        Find Alternatives
                    </button>
                ` : `
                    <button class="btn-add-cart" onclick="addProductToCart('${prod.product_id}', 1, event)">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                        Add
                    </button>
                `}
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
            const hintEl = document.getElementById("homeRecsHint");
            if (hintEl) {
                const ctxType = data.context_type || "default";
                const cust = allCustomers.find(c => c.customer_id === customerId);
                const custName = cust ? cust.name : customerId;
                if (ctxType === "search_dominant") {
                    hintEl.innerText = `Search Intent Tuned for ${custName}`;
                } else if (ctxType === "cart") {
                    hintEl.innerText = `Cart-Aware Tuning for ${custName}`;
                } else if (ctxType === "cold_start") {
                    hintEl.innerText = `Popularity Baseline for ${custName}`;
                } else {
                    hintEl.innerText = `Personalized for ${custName}`;
                }
            }
            if (recGrid) {
                if (!data.recommendations || data.recommendations.length === 0) {
                    recGrid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 2rem;">No active recommendations for this profile yet.</div>`;
                    return;
                }

                recGrid.innerHTML = data.recommendations.map(rec => {
                    return createProductCardHtml(rec, rec);
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

    // Phase 5: Log session view event for context-aware intelligence
    recordSessionEvent(activeCustomerId, productId, "PRODUCT_VIEW");

    try {
        const res = await fetch(`${API_BASE}/api/product/${productId}`);
        const json = await res.json();
        if (json.status === "success") {
            const prod = json.product;
            await renderProductModalDetails(prod);
        } else {
            productDetailContent.innerHTML = `<p style="color:var(--accent-rose); text-align:center;">Product not found.</p>`;
        }
    } catch (err) {
        productDetailContent.innerHTML = `<p style="color:var(--accent-rose); text-align:center;">Error fetching product details.</p>`;
    }
}

async function renderProductModalDetails(prod) {
    const isWishlisted = currentWishlist.has(prod.product_id);
    const iconSvg = getCategoryIconSvg(prod.category_id);
    const isOutOfStock = prod.stock_quantity <= 0;

    // Out-of-Stock alert
    let oosAlertHtml = "";
    if (isOutOfStock) {
        oosAlertHtml = `
            <div class="out-of-stock-alert">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                <div>
                    <strong>Item Currently Out of Stock</strong>
                    <p>This product is temporarily sold out. Our recommendation engine has automatically selected top in-stock alternatives with matching technical specifications below.</p>
                </div>
            </div>
        `;
    }

    // Customer Reviews
    let reviewsHtml = `
        <div class="detail-extra-section">
            <h4>Verified Customer Reviews (${prod.reviews ? prod.reviews.length : 0})</h4>
            ${!prod.reviews || prod.reviews.length === 0 ? '<p style="color:var(--text-muted); font-size:0.85rem;">No reviews yet for this item.</p>' : `
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

    // Render primary modal shell first
    productDetailContent.innerHTML = `
        ${oosAlertHtml}
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
                    ${isOutOfStock ? 
                        '<span class="stock-status-pill out-of-stock">Out of Stock (0 units)</span>' : 
                        `<span class="stock-status-pill in-stock">In Stock: ${prod.stock_quantity} units</span>`}
                </div>

                <p class="detail-desc">${escapeHtml(prod.description || 'Premium grade hardware engineered for performance and longevity.')}</p>

                <div class="detail-actions-row">
                    ${!isOutOfStock ? `
                        <div class="item-qty-selector">
                            <button class="qty-btn" onclick="adjustModalQty(-1)">&minus;</button>
                            <input type="number" id="modalQtyInput" class="qty-input" value="1" min="1" max="${prod.stock_quantity}" readonly>
                            <button class="qty-btn" onclick="adjustModalQty(1)">&plus;</button>
                        </div>

                        <button class="detail-btn-cart" onclick="addModalProductToCart('${prod.product_id}')">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
                            Add to Cart
                        </button>
                    ` : `
                        <button class="detail-btn-cart btn-disabled" disabled style="opacity:0.5; cursor:not-allowed;">
                            Item Temporarily Unavailable
                        </button>
                    `}

                    <button class="detail-btn-wishlist ${isWishlisted ? 'active' : ''}" onclick="toggleWishlist('${prod.product_id}', event)">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
                        ${isWishlisted ? 'Saved in Wishlist' : 'Add to Wishlist'}
                    </button>
                </div>
            </div>
        </div>

        <div id="modalContextSections">
            <!-- Dynamically loaded contextual intelligence -->
        </div>

        ${reviewsHtml}
    `;

    // Load contextual recommendation sections asynchronously
    const contextBox = document.getElementById("modalContextSections");
    if (!contextBox) return;

    if (isOutOfStock) {
        // Load in-stock alternatives
        try {
            const altRes = await fetch(`${API_BASE}/api/recommendations/alternatives/${prod.product_id}`);
            const altJson = await altRes.json();
            if (altJson.status === "success" && altJson.alternatives && altJson.alternatives.length > 0) {
                contextBox.innerHTML = `
                    <div class="detail-extra-section" style="border-top: 2px solid var(--accent-rose);">
                        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
                            <span class="stock-status-pill out-of-stock">&#9888; OUT OF STOCK ALTERNATIVES</span>
                            <h4 style="margin:0;">Best Available In-Stock Alternatives</h4>
                        </div>
                        <p style="color:var(--text-muted); font-size:0.85rem; margin-bottom:1rem;">
                            Selected based on technical spec similarity, category match, price range, and verified customer ratings:
                        </p>
                        <div class="mini-cards-row">
                            ${altJson.alternatives.map(alt => `
                                <div class="alternative-card">
                                    <div>
                                        <span class="alternative-match-badge">${Math.round(alt.similarity * 100)}% Spec Match</span>
                                        <div style="font-size:0.72rem; color:var(--text-muted);">${alt.category_name || ''}</div>
                                        <h5 style="cursor:pointer;" onclick="openProductModal('${alt.product_id}')">${escapeHtml(alt.product_name)}</h5>
                                        <div class="stars" style="font-size:0.72rem; margin: 0.35rem 0;">${renderStars(alt.avg_rating || 4.7)} <span style="color:var(--text-muted);">(${alt.review_count || 12})</span></div>
                                    </div>
                                    <div>
                                        <div style="display:flex; align-items:baseline; justify-content:space-between; margin-bottom:0.5rem;">
                                            <span style="font-size:1.05rem; font-weight:800; color:var(--text-primary);">${formatMoney(alt.price)}</span>
                                            <span style="font-size:0.75rem; color:var(--accent-emerald);">In Stock (${alt.stock_quantity})</span>
                                        </div>
                                        <button class="btn-primary" style="width:100%; padding:0.4rem; font-size:0.8rem;" onclick="addProductToCart('${alt.product_id}', 1, event); closeProductModal();">
                                            Switch &amp; Add to Cart
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
        } catch (e) {
            console.error("Error loading alternatives:", e);
        }
    } else {
        // In-stock product: fetch Frequently Bought Together bundle and Viewed-Together context
        let sectionsHtml = "";

        // 1. Apriori bundle
        try {
            const bRes = await fetch(`${API_BASE}/api/recommendations/bundle/${prod.product_id}`);
            const bJson = await bRes.json();
            if (bJson.status === "success" && bJson.bundle && bJson.bundle.items.length > 0) {
                const bundle = bJson.bundle;
                const bundleIds = [prod.product_id, ...bundle.items.map(i => i.product_id)];
                sectionsHtml += `
                    <div class="detail-extra-section">
                        <h4>Frequently Bought Together</h4>
                        <div class="fbt-bundle-full">
                            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
                                <span class="stock-status-pill in-stock">&#128293; APRIORI MINED BUNDLE</span>
                                <span style="font-size:0.78rem; color:#a5b4fc;">Frequently purchased together in single checkout transactions</span>
                            </div>
                            <div class="fbt-bundle-items-row">
                                <div class="fbt-bundle-item-chip">
                                    <strong>This Item:</strong> ${escapeHtml(prod.product_name)} (${formatMoney(prod.price)})
                                </div>
                                ${bundle.items.map(item => `
                                    <span class="fbt-plus-symbol">+</span>
                                    <div class="fbt-bundle-item-chip" style="cursor:pointer;" onclick="openProductModal('${item.product_id}')">
                                        <span>${escapeHtml(item.product_name)}</span>
                                        <strong style="color:var(--primary-light);">${formatMoney(item.price)}</strong>
                                    </div>
                                `).join('')}
                            </div>
                            <div class="fbt-bundle-pricing">
                                <div>
                                    <div style="font-size:0.82rem; color:var(--text-muted);">
                                        Regular Total: <span style="text-decoration:line-through;">${formatMoney(bundle.regular_total)}</span>
                                    </div>
                                    <div style="display:flex; align-items:center; gap:0.5rem;">
                                        <span style="font-size:1.3rem; font-weight:800; color:#fff;">Bundle Price: ${formatMoney(bundle.bundle_price)}</span>
                                        <span class="stock-status-pill in-stock">Save 10% (${formatMoney(bundle.savings)})</span>
                                    </div>
                                </div>
                                <div style="display:flex; gap:0.5rem;">
                                    <button class="btn-primary" onclick="quickAddBundle([${bundleIds.map(id => `'${id}'`).join(', ')}])">
                                        Add Complete Bundle (${bundleIds.length} Items)
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
        } catch (e) {
            console.error("Error loading bundle:", e);
        }

        // 2. Viewed-Together / Setup context
        try {
            const ctxRes = await fetch(`${API_BASE}/api/recommendations/${activeCustomerId}?current_product_id=${prod.product_id}&context_type=product_view&top_n=3`);
            const ctxJson = await ctxRes.json();
            if (ctxJson.status === "success" && ctxJson.data && ctxJson.data.recommendations.length > 0) {
                sectionsHtml += `
                    <div class="detail-extra-section">
                        <h4>Because You Viewed This (Context-Aware Matches)</h4>
                        <div class="mini-cards-row">
                            ${ctxJson.data.recommendations.map(r => `
                                <div class="mini-product-card">
                                    <div>
                                        <span style="font-size:0.7rem; color:var(--text-muted);">${r.category_name || ''}</span>
                                        <h5 style="cursor:pointer; margin-top:0.25rem;" onclick="openProductModal('${r.product_id}')">${escapeHtml(r.product_name)}</h5>
                                        <div style="font-size:0.72rem; color:#a5b4fc; margin-bottom:0.35rem;">
                                            ${escapeHtml(r.reason)}
                                        </div>
                                    </div>
                                    <div style="display:flex; align-items:center; justify-content:space-between; margin-top:0.75rem;">
                                        <span style="font-size:0.92rem; font-weight:700;">${formatMoney(r.price)}</span>
                                        <button class="btn-add-cart" style="padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="addProductToCart('${r.product_id}', 1, event)">+ Add</button>
                                    </div>
                                </div>
                            `).join("")}
                        </div>
                    </div>
                `;
            }
        } catch (e) {
            console.error("Error loading product view recs:", e);
        }

        contextBox.innerHTML = sectionsHtml;
    }
}

function adjustModalQty(delta) {
    const input = document.getElementById("modalQtyInput");
    if (!input) return;
    const max = parseInt(input.getAttribute("max") || "9999");
    let val = parseInt(input.value) + delta;
    if (val < 1) val = 1;
    if (val > max) {
        val = max;
        showToast(`Only ${max} units available in stock for this item.`, "error");
    }
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
            recordSessionEvent(activeCustomerId, productId, "ADD_TO_CART");
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
        const drawerSug = document.getElementById("drawerSmartSuggestions");
        if (drawerSug) drawerSug.style.display = "none";
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

    // Phase 5: Smart suggestions inside cart drawer
    loadDrawerSuggestions(activeCustomerId);
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
    const sugSection = document.getElementById("cartSmartSuggestionsSection");

    if (!itemsCol) return;

    if (!cartData.items || cartData.items.length === 0) {
        if (sugSection) sugSection.style.display = "none";
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

    // Phase 5: Complete Your Setup / Smart suggestions on full cart page
    loadCartSuggestions(activeCustomerId);
}

// Phase 5: Fetch context-aware suggestions for current cart
async function loadCartSuggestions(customerId) {
    const sugSection = document.getElementById("cartSmartSuggestionsSection");
    const sugGrid = document.getElementById("cartSmartSuggestionsGrid");
    if (!sugSection || !sugGrid) return;

    try {
        const res = await fetch(`${API_BASE}/api/recommendations/${customerId}?context_type=cart&top_n=3`);
        const json = await res.json();
        if (json.status === "success" && json.data.recommendations && json.data.recommendations.length > 0) {
            sugSection.style.display = "block";
            sugGrid.innerHTML = json.data.recommendations.map(rec => {
                return createProductCardHtml(rec, rec);
            }).join("");
        } else {
            sugSection.style.display = "none";
        }
    } catch (e) {
        sugSection.style.display = "none";
    }
}

// Phase 5: Fetch compact suggestions for cart drawer
async function loadDrawerSuggestions(customerId) {
    const drawerSug = document.getElementById("drawerSmartSuggestions");
    if (!drawerSug) return;

    try {
        const res = await fetch(`${API_BASE}/api/recommendations/${customerId}?context_type=cart&top_n=2`);
        const json = await res.json();
        if (json.status === "success" && json.data.recommendations && json.data.recommendations.length > 0) {
            drawerSug.style.display = "block";
            drawerSug.innerHTML = `
                <h5>&#9889; Frequently Added With Your Cart</h5>
                ${json.data.recommendations.map(rec => `
                    <div class="drawer-rec-row">
                        <div style="flex:1; padding-right:0.5rem;">
                            <div class="drawer-rec-name" onclick="openProductModal('${rec.product_id}')">${escapeHtml(rec.product_name)}</div>
                            <div class="drawer-rec-price">${formatMoney(rec.price)} &bull; <span class="ai-match-badge-sm">${escapeHtml(rec.ai_match || 'Match')}</span></div>
                            <div style="font-size:0.7rem; color:#cbd5e1; margin-top:0.15rem;">✓ ${escapeHtml((rec.reasons && rec.reasons.length) ? rec.reasons[0] : (rec.reason || ''))}</div>
                        </div>
                        <button class="btn-add-cart" style="padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="addProductToCart('${rec.product_id}', 1, event)">+ Add</button>
                    </div>
                `).join("")}
            `;
        } else {
            drawerSug.style.display = "none";
        }
    } catch (e) {
        drawerSug.style.display = "none";
    }
}

async function updateItemQuantity(productId, newQty) {
    if (newQty <= 0) {
        await removeProductFromCart(productId);
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/cart/update`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeCustomerId,
                product_id: productId,
                quantity: newQty
            })
        });
        const json = await res.json();
        if (json.status === "success") {
            await loadCart(activeCustomerId);
        } else {
            showToast(json.message || "Failed to update item quantity.", "error");
        }
    } catch (err) {
        showToast("Error updating cart quantity.", "error");
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
        const reviewShippingTo = document.getElementById("reviewShippingTo");
        if (reviewShippingTo) {
            reviewShippingTo.innerText = `${cust.name} (${cust.city})`;
        }
    }
    updateCheckoutPaymentMethodLabel();
    await loadCart(activeCustomerId);
}

function updateCheckoutPaymentMethodLabel() {
    const selected = document.querySelector("input[name='checkoutPaymentMethod']:checked");
    const labelEl = document.getElementById("reviewPaymentMethodLabel");
    if (selected && labelEl) {
        const labels = {
            "CREDIT_CARD": "Credit / Debit Card",
            "UPI": "Instant UPI / QR",
            "NET_BANKING": "Net Banking",
            "CASH_ON_DELIVERY": "Cash on Delivery (COD)"
        };
        labelEl.innerText = labels[selected.value] || selected.value;
    }
}

function renderCheckoutSummaryContent(cartData) {
    const list = document.getElementById("checkoutItemsList");
    const subtotal = document.getElementById("checkoutSubtotal");
    const total = document.getElementById("checkoutTotal");
    const placeOrderBtn = document.getElementById("checkoutCommitBtn");

    if (!list) return;

    if (!cartData.items || cartData.items.length === 0) {
        list.innerHTML = `<p style="color:var(--text-muted); text-align:center; padding:1.5rem;">Cart is empty. <a href="javascript:void(0)" onclick="navigateTo('shop')" style="color:var(--primary);">Add items</a></p>`;
        if (placeOrderBtn) placeOrderBtn.disabled = true;
        return;
    }

    if (placeOrderBtn) placeOrderBtn.disabled = false;

    list.innerHTML = cartData.items.map(item => `
        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.5rem;">
            <span>${escapeHtml(item.product_name)} &times; ${item.quantity}</span>
            <strong>${formatMoney(item.subtotal)}</strong>
        </div>
    `).join("");

    subtotal.innerText = formatMoney(cartData.total_amount);
    total.innerText = formatMoney(cartData.total_amount);
}

async function executeCustomerOrder() {
    const placeBtn = document.getElementById("checkoutCommitBtn");
    if (placeBtn) placeBtn.disabled = true;

    const paymentMethod = document.querySelector("input[name='checkoutPaymentMethod']:checked")?.value || "CREDIT_CARD";

    try {
        const res = await fetch(`${API_BASE}/api/checkout`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeCustomerId,
                payment_method: paymentMethod,
                simulate_fail: false
            })
        });

        const json = await res.json();
        if (json.status === "success") {
            const resData = json.result;
            showOrderConfirmation(resData.order_id, resData.amount, paymentMethod);
            recordSessionEvent(activeCustomerId, null, "PURCHASE");
            await loadCart(activeCustomerId);
            await loadRecommendations(activeCustomerId);
        } else {
            showToast(json.result?.error || json.message || "Order placement failed.", "error");
        }
    } catch (err) {
        showToast("Error executing order transaction.", "error");
    } finally {
        if (placeBtn) placeBtn.disabled = false;
    }
}

function showOrderConfirmation(orderId, amount, paymentMethod) {
    const idEl = document.getElementById("confOrderId");
    const amtEl = document.getElementById("confTotalAmount");
    const pmEl = document.getElementById("confPaymentMethod");
    if (idEl) idEl.innerText = orderId;
    if (amtEl) amtEl.innerText = formatMoney(amount);
    if (pmEl) pmEl.innerText = paymentMethod;

    if (orderConfirmationModal) {
        orderConfirmationModal.style.display = "flex";
    }
}

function closeConfirmationModal() {
    if (orderConfirmationModal) {
        orderConfirmationModal.style.display = "none";
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
// 9. WISHLIST MANAGEMENT (DATABASE PERSISTENT)
// ==========================================================
async function loadWishlistFromDb(customerId) {
    try {
        const res = await fetch(`${API_BASE}/api/wishlist/${customerId}`);
        const json = await res.json();
        if (json.status === "success") {
            currentWishlist = new Set(json.wishlist.map(w => w.product_id));
            updateWishlistBadge();
        }
    } catch (err) {
        console.error("Error loading wishlist from database:", err);
    }
}

function updateWishlistBadge() {
    if (wishlistCountBadge) {
        wishlistCountBadge.innerText = currentWishlist.size;
    }
    const profileWishlistCount = document.getElementById("profileWishlistCount");
    if (profileWishlistCount) {
        profileWishlistCount.innerText = currentWishlist.size;
    }
}

async function toggleWishlist(productId, event = null) {
    if (event) event.stopPropagation();

    try {
        const res = await fetch(`${API_BASE}/api/wishlist/toggle`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeCustomerId,
                product_id: productId
            })
        });
        const json = await res.json();
        if (json.status === "success") {
            if (json.in_wishlist) {
                currentWishlist.add(productId);
            } else {
                currentWishlist.delete(productId);
            }
            updateWishlistBadge();
            showToast(json.message, "success");

            // Update heart icon states across active cards
            document.querySelectorAll(`.wishlist-toggle-btn[onclick*="${productId}"]`).forEach(btn => {
                btn.classList.toggle("active", json.in_wishlist);
                btn.title = json.in_wishlist ? "Remove from Wishlist" : "Save to Wishlist";
            });

            // Update heart icon in product detail modal if open
            const detailWishlistBtn = document.querySelector(`.detail-btn-wishlist[onclick*="${productId}"]`);
            if (detailWishlistBtn) {
                detailWishlistBtn.classList.toggle("active", json.in_wishlist);
                detailWishlistBtn.innerHTML = json.in_wishlist ? 
                    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg> Saved in Wishlist` :
                    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg> Add to Wishlist`;
            }

            if (currentView === "wishlist") {
                await renderWishlistView();
            }
        }
    } catch (err) {
        showToast("Error updating database wishlist.", "error");
    }
}

async function clearWishlist() {
    for (const pid of Array.from(currentWishlist)) {
        await toggleWishlist(pid, null);
    }
    showToast("Wishlist cleared.", "success");
    await renderWishlistView();
}

async function renderWishlistView() {
    const grid = document.getElementById("wishlistCardsGrid");
    if (!grid) return;

    grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 3rem;">Loading saved items from SQLite...</div>`;

    try {
        const res = await fetch(`${API_BASE}/api/wishlist/${activeCustomerId}`);
        const json = await res.json();
        if (json.status === "success") {
            const items = json.wishlist;
            currentWishlist = new Set(items.map(w => w.product_id));
            updateWishlistBadge();

            if (items.length === 0) {
                grid.innerHTML = `
                    <div style="grid-column: 1 / -1; text-align: center; padding: 4rem; background: var(--bg-card); border-radius: var(--radius-lg);">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-muted); margin-bottom:1rem; opacity:0.6;">
                            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                        </svg>
                        <h3 style="font-family:var(--font-heading); margin-bottom:0.5rem;">Your Wishlist is Empty</h3>
                        <p style="color:var(--text-secondary); margin-bottom:1.5rem;">Items saved here are stored in the relational database 'wishlist' table.</p>
                        <button class="btn-primary" onclick="navigateTo('shop')">Explore Shop Now</button>
                    </div>
                `;
                return;
            }

            grid.innerHTML = items.map(item => `
                <div class="product-card" id="card-${item.product_id}">
                    <div>
                        <div class="card-top">
                            <span class="category-badge">${item.category_name}</span>
                            <button class="wishlist-toggle-btn active" onclick="toggleWishlist('${item.product_id}', event)" title="Remove from Wishlist">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                                </svg>
                            </button>
                        </div>
                        <span class="card-brand">${item.brand}</span>
                        <h3 class="card-title" onclick="openProductModal('${item.product_id}')">${escapeHtml(item.product_name)}</h3>
                        <div class="card-rating-row">
                            <span class="stars">${renderStars(item.avg_rating || 4.5)}</span>
                            <span>${item.avg_rating || 4.5}</span>
                        </div>
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.35rem;">
                            Saved on: ${item.added_at ? item.added_at.split(" ")[0] : "Recently"}
                        </div>
                    </div>
                    <div class="card-footer">
                        <div>
                            <span class="card-price">${formatMoney(item.price)}</span>
                            <div>${item.stock_quantity > 0 ? `<span class="stock-status-pill in-stock">In Stock (${item.stock_quantity})</span>` : `<span class="stock-status-pill out-of-stock">Out of Stock</span>`}</div>
                        </div>
                        <button class="btn-primary" style="padding:0.4rem 0.75rem; font-size:0.8rem;" onclick="moveWishlistToCart('${item.product_id}')">
                            Move to Cart
                        </button>
                    </div>
                </div>
            `).join("");
        }
    } catch (err) {
        grid.innerHTML = `<p style="color:var(--accent-rose); text-align:center;">Failed to load wishlist.</p>`;
    }
}

async function moveWishlistToCart(productId) {
    await addProductToCart(productId, 1, null, false);
    await toggleWishlist(productId, null);
    showToast("Moved item from wishlist to your cart!", "success");
    openCartDrawer();
}

// ==========================================================
// 10. CUSTOMER PROFILE VIEW
// ==========================================================
async function renderProfileView(cust) {
    if (!cust) return;
    const initials = cust.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();

    document.getElementById("profileAvatarLarge").innerText = initials;
    document.getElementById("profileCustomerName").innerText = cust.name;
    document.getElementById("profileDomainPill").innerText = `${getDomainLabel(cust.customer_id)} Persona`;

    try {
        const res = await fetch(`${API_BASE}/api/profile/${cust.customer_id}`);
        const json = await res.json();
        if (json.status === "success") {
            const p = json.profile;
            document.getElementById("profileMetaLine").innerHTML = 
                `Customer ID: <strong>${p.customer_id}</strong> &bull; ${p.city} &bull; ${p.email} &bull; Phone: ${p.phone} &bull; Registered: ${p.registered_at ? p.registered_at.split(" ")[0] : "Active"}`;

            document.getElementById("profileTotalOrders").innerText = p.total_orders;
            document.getElementById("profileLifetimeSpend").innerText = formatMoney(p.lifetime_spend);
            const aovEl = document.getElementById("profileAvgOrderValue");
            if (aovEl) aovEl.innerText = formatMoney(p.avg_order_value);
            document.getElementById("profileWishlistCount").innerText = p.wishlist_count;

            // Render Top Categories
            const catContainer = document.getElementById("profileTopCategories");
            if (catContainer) {
                if (p.top_categories && p.top_categories.length > 0) {
                    catContainer.innerHTML = p.top_categories.map(c => `
                        <div class="profile-cat-item">
                            <div>
                                <strong>${escapeHtml(c.category_name)}</strong>
                                <span style="display:block; font-size:0.75rem; color:var(--text-muted);">${c.items_count} items bought</span>
                            </div>
                            <span style="font-weight:700; color:#818cf8;">${formatMoney(c.total_spent)}</span>
                        </div>
                    `).join("");
                } else {
                    catContainer.innerHTML = `<p style="color:var(--text-muted); font-size:0.85rem;">No completed purchases recorded yet.</p>`;
                }
            }

            // Render Recent Searches
            const searchContainer = document.getElementById("profileRecentSearches");
            if (searchContainer) {
                if (p.recent_searches && p.recent_searches.length > 0) {
                    searchContainer.innerHTML = p.recent_searches.map(s => `
                        <button class="search-pill-item" onclick="applyProfileSearch('${escapeHtml(s.query)}')">
                            <span>🔍 ${escapeHtml(s.query)}</span>
                            <span style="font-size:0.68rem; color:var(--text-muted);">${s.searched_at ? s.searched_at.split(" ")[0] : ""}</span>
                        </button>
                    `).join("");
                } else {
                    searchContainer.innerHTML = `<p style="color:var(--text-muted); font-size:0.85rem;">No recent searches recorded.</p>`;
                }
            }

            // Render Recent Orders Table
            const ordersBody = document.getElementById("profileRecentOrdersBody");
            if (ordersBody) {
                if (p.recent_orders && p.recent_orders.length > 0) {
                    ordersBody.innerHTML = p.recent_orders.map(o => `
                        <tr>
                            <td><strong>${o.order_id}</strong></td>
                            <td>${o.order_date}</td>
                            <td><strong>${formatMoney(o.total_amount)}</strong></td>
                            <td>${o.payment_method}</td>
                            <td><span class="stock-status-pill in-stock">${o.order_status}</span></td>
                        </tr>
                    `).join("");
                } else {
                    ordersBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No orders placed yet.</td></tr>`;
                }
            }
        }
    } catch (err) {
        console.error("Error loading profile:", err);
    }
}

function applyProfileSearch(query) {
    globalSearchInput.value = query;
    clearSearchBtn.style.display = "block";
    executeHeaderSearch();
}

// ==========================================================
// 11. ADMIN & INTELLIGENCE LAB PORTAL
// ==========================================================
function openAdminPortal(tabName = "dashboard") {
    adminMode = true;
    adminPortalContainer.style.display = "flex";
    portalModeBtnText.innerText = "Exit Admin Lab";
    togglePortalModeBtn.classList.add("active");
    setupAdminSimCustomerSelect();
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
    } else if (tabName === "customer-intelligence") {
        loadAdminCustomerIntelligence();
    } else if (tabName === "inventory-intelligence") {
        loadAdminInventoryIntelligence();
    } else if (tabName === "product-intelligence") {
        loadAdminProductIntelligence();
    } else if (tabName === "ai-insights") {
        loadAdminAiInsights();
    } else if (tabName === "inventory") {
        renderAdminInventory();
    } else if (tabName === "orders") {
        loadAdminOrders();
    } else if (tabName === "customers") {
        loadAdminCustomerIntelligence();
    } else if (tabName === "rules") {
        initXaiAuditorControls();
        runXaiAudit();
        loadRules();
    } else if (tabName === "dbms") {
        loadDbmsView("v_market_basket");
        setupAdminSimCustomerSelect();
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
// 11.B ACID TRANSACTION SIMULATOR (ADMIN LAB)
// ==========================================================
function setupAdminSimCustomerSelect() {
    const select = document.getElementById("adminSimCustomerSelect");
    if (!select) return;
    select.innerHTML = allCustomers.map(c => 
        `<option value="${c.customer_id}">${c.customer_id}: ${c.name} (${c.city})</option>`
    ).join("");
    select.value = activeCustomerId;
}

async function runAdminAcidSimulation() {
    const simCustSelect = document.getElementById("adminSimCustomerSelect");
    if (!simCustSelect) return;
    const simCustId = simCustSelect.value;
    const simFail = document.querySelector("input[name='adminSimFailMode']:checked")?.value === "true";
    const auditLog = document.getElementById("adminSimAuditLog");
    const auditConsole = document.getElementById("adminSimLogConsole");
    const statusPill = document.getElementById("adminSimAuditStatusPill");
    const runBtn = document.getElementById("runAdminAcidSimBtn");

    if (runBtn) runBtn.disabled = true;
    auditLog.style.display = "block";
    statusPill.innerText = "EXECUTING";
    statusPill.className = "audit-status";
    auditConsole.innerText = `[1] BEGIN TRANSACTION;\n[*] Customer: ${simCustId}\n[*] Mode: ${simFail ? "SIMULATED FAILURE TEST (ROLLBACK)" : "NORMAL TRANSACTION (COMMIT)"}\n[*] Validating shopping cart entries and inventory integrity triggers...`;

    try {
        const res = await fetch(`${API_BASE}/api/checkout`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: simCustId,
                payment_method: "CREDIT_CARD",
                simulate_fail: simFail
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
[5] INSERT INTO payments (Method: CREDIT_CARD, Status: SUCCESS)
[6] DELETE FROM shopping_cart (Cart entries cleared)
[7] [COMMIT] Transaction successfully committed! All changes persisted in SQLite.`;
            showToast("Simulation COMMIT succeeded! Inventory decremented.", "success");
            await loadAdminOverview();
            renderAdminInventory();
        } else {
            statusPill.innerText = "ROLLED BACK";
            statusPill.className = "audit-status error";
            auditConsole.innerText = 
`[1] BEGIN TRANSACTION;
[2] Order header and items staged.
[!] ${json.result?.error || json.message}
[!] [ROLLBACK] Transaction rolled back completely!
[✓] Trigger modifications undone: Product inventory stock was restored.
[✓] Shopping cart preserved without data corruption. Partial writes aborted.`;
            showToast("Simulation ROLLBACK verified: Database integrity preserved.", "error");
            renderAdminInventory();
        }
    } catch (err) {
        statusPill.innerText = "ERROR";
        statusPill.className = "audit-status error";
        auditConsole.innerText += "\n[!] Execution failed due to communication error.";
    } finally {
        if (runBtn) runBtn.disabled = false;
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

// ==========================================================
// PHASE 6: EXPLAINABLE AI (XAI) & AUDITOR CONTROLLER
// ==========================================================

function handleXaiContextChange() {
    const ctxSelect = document.getElementById("xaiContextSelect");
    const wrap = document.getElementById("xaiProductPickerWrap");
    if (!ctxSelect || !wrap) return;
    const val = ctxSelect.value;
    if (val === "product_view" || val === "alternatives") {
        wrap.style.display = "flex";
    } else {
        wrap.style.display = "none";
    }
    runXaiAudit();
}

function initXaiAuditorControls() {
    const prodSelect = document.getElementById("xaiProductSelect");
    if (!prodSelect) return;
    if (prodSelect.options.length <= 1 && allProducts && allProducts.length > 0) {
        prodSelect.innerHTML = allProducts.map(p => 
            `<option value="${p.product_id}">${p.product_id} &bull; ${escapeHtml(p.product_name)} (${formatMoney(p.price)})</option>`
        ).join("");
    }
}

async function runXaiAudit() {
    const custSelect = document.getElementById("xaiCustomerSelect");
    const ctxSelect = document.getElementById("xaiContextSelect");
    const prodSelect = document.getElementById("xaiProductSelect");
    const topNSelect = document.getElementById("xaiTopNSelect");
    const out = document.getElementById("xaiAuditResults");
    if (!out) return;

    initXaiAuditorControls();

    const custId = custSelect ? custSelect.value : "C101";
    const ctxType = ctxSelect ? ctxSelect.value : "default";
    const currentPid = (prodSelect && (ctxType === "product_view" || ctxType === "alternatives")) ? prodSelect.value : "";
    const topN = topNSelect ? parseInt(topNSelect.value) : 4;

    out.innerHTML = `
        <div style="text-align:center; padding:2rem; color:var(--text-muted);">
            <div class="skeleton-shimmer" style="height:32px; width:240px; margin:0 auto 1rem auto; border-radius:8px;"></div>
            Computing multi-signal hybrid recommendation audit...
        </div>
    `;

    try {
        let url = `${API_BASE}/api/recommendations/audit/${custId}?context_type=${encodeURIComponent(ctxType)}&top_n=${topN}`;
        if (currentPid) {
            url += `&current_product_id=${encodeURIComponent(currentPid)}`;
        }
        const res = await fetch(url);
        const json = await res.json();

        if (json.status !== "success" || !json.audit) {
            out.innerHTML = `<div style="text-align:center; color:var(--accent-rose); padding:2rem;">Failed to audit recommendations for ${escapeHtml(custId)}.</div>`;
            return;
        }

        const audit = json.audit;
        const ctx = audit.context || {};
        const recs = audit.recommendations || [];
        const weights = ctx.active_weights || { apriori: 0.4, search: 0.25, similarity: 0.2, popularity: 0.15 };

        // 1. Meta KPI Banner
        let metaHtml = `
            <div class="xai-meta-banner">
                <div class="xai-meta-kpi">
                    <div class="xai-meta-kpi-label">Resolved Profile</div>
                    <div class="xai-meta-kpi-val" style="color:#818cf8; text-transform:uppercase; font-size:0.95rem;">${escapeHtml(ctx.resolved_profile || ctxType)}</div>
                </div>
                <div class="xai-meta-kpi">
                    <div class="xai-meta-kpi-label">Active Weight Profile</div>
                    <div style="font-size:0.75rem; color:var(--text-secondary); line-height:1.4;">
                        <span style="color:#818cf8;">Apr: ${Math.round((weights.apriori||0)*100)}%</span> &bull; 
                        <span style="color:#06b6d4;">Srch: ${Math.round((weights.search||0)*100)}%</span> &bull; 
                        <span style="color:#38bdf8;">Sim: ${Math.round((weights.similarity||0)*100)}%</span> &bull; 
                        <span style="color:#f59e0b;">Pop: ${Math.round((weights.popularity||0)*100)}%</span>
                    </div>
                </div>
                <div class="xai-meta-kpi">
                    <div class="xai-meta-kpi-label">Customer Activity State</div>
                    <div style="font-size:0.75rem; color:var(--text-secondary); line-height:1.4;">
                        <strong>${audit.history_count || 0}</strong> Orders &bull; 
                        <strong>${audit.cart_count || 0}</strong> In Cart &bull; 
                        <strong>${audit.search_count || 0}</strong> Searches
                    </div>
                </div>
                <div class="xai-meta-kpi">
                    <div class="xai-meta-kpi-label">Audited Items</div>
                    <div class="xai-meta-kpi-val" style="color:#34d399;">${recs.length} Candidates</div>
                </div>
            </div>
        `;

        if (recs.length === 0) {
            out.innerHTML = metaHtml + `<div style="text-align:center; padding:2rem; color:var(--text-muted);">No candidates met criteria for this context.</div>`;
            return;
        }

        // 2. Candidate Inspection Cards
        const cardsHtml = recs.map((rec, idx) => {
            const signals = rec.signals || {};
            const tech = rec.technical_explanation || {};
            const aprDetails = tech.apriori_details || {};
            const srchDetails = tech.search_details || {};
            const simDetails = tech.similarity_details || {};
            const invDetails = tech.inventory_details || {};
            const provSources = rec.source || rec.provenance || tech.provenance_sources || [];

            const aprScore = signals.apriori !== undefined ? signals.apriori : (signals.apriori_score || 0);
            const srchScore = signals.search_intent !== undefined ? signals.search_intent : (signals.search_score || 0);
            const simScore = signals.content_similarity !== undefined ? signals.content_similarity : (signals.similarity_score || 0);
            const popScore = signals.popularity !== undefined ? signals.popularity : (signals.popularity_score || 0);
            const invScore = signals.inventory !== undefined ? signals.inventory : (signals.inventory_score || 1.0);

            const aprWeight = weights.apriori || 0.40;
            const srchWeight = weights.search || 0.25;
            const simWeight = weights.similarity || 0.20;
            const popWeight = weights.popularity || 0.15;

            const aprPoints = (aprScore * aprWeight).toFixed(3);
            const srchPoints = (srchScore * srchWeight).toFixed(3);
            const simPoints = (simScore * simWeight).toFixed(3);
            const popPoints = (popScore * popWeight).toFixed(3);

            const ruleProof = aprDetails.rule_statement 
                ? `Rule: ${escapeHtml(aprDetails.rule_statement)}\nSupport: ${((aprDetails.support||0)*100).toFixed(1)}% | Confidence: ${((aprDetails.confidence||0)*100).toFixed(1)}% | Lift: ${(aprDetails.lift||0).toFixed(2)}x`
                : (aprDetails.affinity_score > 0 ? `Historical co-purchase affinity score: ${aprDetails.affinity_score.toFixed(3)}` : `No active co-purchase rule fired for this item.`);

            const searchProof = srchDetails.matched_query
                ? `Query match: '${escapeHtml(srchDetails.matched_query)}' (TF-IDF Decay: ${(srchScore*100).toFixed(1)}%)`
                : (srchScore > 0 ? `Lexical match score: ${(srchScore*100).toFixed(1)}%` : `No search intent match.`);

            const simProof = simDetails.reference_product
                ? `Cosine match with '${escapeHtml(simDetails.reference_product)}': ${(simScore*100).toFixed(1)}%`
                : (simScore > 0 ? `Catalog TF-IDF similarity: ${(simScore*100).toFixed(1)}%` : `Baseline catalog similarity.`);

            return `
                <div class="xai-candidate-card">
                    <div class="xai-rank-badge">RANK #${idx + 1}</div>
                    
                    <!-- Left Column: Product Info & Customer Explanation -->
                    <div>
                        <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em;">${escapeHtml(rec.category_name || '')}</div>
                        <h4 style="margin:0.25rem 0 0.5rem 0; font-size:1.15rem; color:var(--text-primary); cursor:pointer;" onclick="openProductModal('${rec.product_id}')">
                            ${escapeHtml(rec.product_name)} <span style="font-size:0.75rem; font-family:var(--font-mono); color:var(--text-muted);">(${rec.product_id})</span>
                        </h4>
                        
                        <div style="display:flex; align-items:baseline; gap:0.75rem; margin-bottom:0.75rem;">
                            <span style="font-size:1.25rem; font-weight:800; color:var(--text-primary);">${formatMoney(rec.price)}</span>
                            <span style="font-size:0.8rem; color:${rec.stock_quantity > 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; font-weight:600;">
                                ${rec.stock_quantity > 0 ? `In Stock (${rec.stock_quantity})` : 'Out of Stock'}
                            </span>
                            <span style="font-size:0.8rem; color:#f59e0b;">★ ${rec.avg_rating || 4.5} (${rec.review_count || 0})</span>
                        </div>

                        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.85rem; flex-wrap:wrap;">
                            <span class="badge-pill-academic" style="font-size:0.7rem; padding:0.2rem 0.5rem;">${escapeHtml(rec.recommendation_type)}</span>
                            <span class="ai-match-badge">${escapeHtml(rec.ai_match || 'Match')}</span>
                            <span style="font-size:0.72rem; color:var(--text-muted);">${escapeHtml(rec.match_strength || '')}</span>
                        </div>

                        <!-- Customer-Facing Reasons Block -->
                        <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:var(--radius-sm); padding:0.75rem; margin-bottom:0.75rem;">
                            <div style="font-size:0.7rem; font-weight:700; color:#c7d2fe; text-transform:uppercase; margin-bottom:0.4rem; letter-spacing:0.04em;">
                                What Customer Sees ("Why Recommended?")
                            </div>
                            <div class="ai-reasons-preview">
                                ${(rec.reasons || [rec.reason || 'Recommended']).map(r => `
                                    <div class="ai-reason-line">
                                        <span class="ai-check-icon">&#10003;</span>
                                        <span class="ai-reason-text">${escapeHtml(r)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <!-- Provenance / Contributing Source Pills -->
                        <div>
                            <div style="font-size:0.68rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.03em;">Contributing Subsystems (Provenance)</div>
                            <div class="xai-tag-group">
                                ${provSources.map(s => `<span class="xai-source-tag">${escapeHtml(s)}</span>`).join('')}
                            </div>
                        </div>
                    </div>

                    <!-- Right Column: Multi-Signal Breakdown & Viva Proof -->
                    <div>
                        <div style="display:flex; align-items:baseline; justify-content:space-between; margin-bottom:0.75rem; padding-bottom:0.5rem; border-bottom:1px solid rgba(255,255,255,0.08);">
                            <span style="font-size:0.75rem; font-weight:700; color:var(--text-secondary); text-transform:uppercase;">Composite Ranking Score</span>
                            <span style="font-size:1.4rem; font-family:var(--font-mono); font-weight:800; color:#818cf8;">
                                ${(rec.score || 0).toFixed(4)}
                            </span>
                        </div>

                        <!-- 5-Signal Breakdown Bars -->
                        <div class="xai-signal-bar-row">
                            <span class="xai-signal-name" style="color:#818cf8;">Apriori Rule (${Math.round(aprWeight*100)}%)</span>
                            <div class="xai-meter-bg">
                                <div class="xai-meter-fill" style="width:${Math.round(aprScore*100)}%; background:#818cf8;"></div>
                            </div>
                            <span class="xai-meter-num">${aprScore.toFixed(2)} &rarr; +${aprPoints}</span>
                        </div>

                        <div class="xai-signal-bar-row">
                            <span class="xai-signal-name" style="color:#06b6d4;">Search Intent (${Math.round(srchWeight*100)}%)</span>
                            <div class="xai-meter-bg">
                                <div class="xai-meter-fill" style="width:${Math.round(srchScore*100)}%; background:#06b6d4;"></div>
                            </div>
                            <span class="xai-meter-num">${srchScore.toFixed(2)} &rarr; +${srchPoints}</span>
                        </div>

                        <div class="xai-signal-bar-row">
                            <span class="xai-signal-name" style="color:#38bdf8;">Similarity (${Math.round(simWeight*100)}%)</span>
                            <div class="xai-meter-bg">
                                <div class="xai-meter-fill" style="width:${Math.round(simScore*100)}%; background:#38bdf8;"></div>
                            </div>
                            <span class="xai-meter-num">${simScore.toFixed(2)} &rarr; +${simPoints}</span>
                        </div>

                        <div class="xai-signal-bar-row">
                            <span class="xai-signal-name" style="color:#f59e0b;">Popularity (${Math.round(popWeight*100)}%)</span>
                            <div class="xai-meter-bg">
                                <div class="xai-meter-fill" style="width:${Math.round(popScore*100)}%; background:#f59e0b;"></div>
                            </div>
                            <span class="xai-meter-num">${popScore.toFixed(2)} &rarr; +${popPoints}</span>
                        </div>

                        <div class="xai-signal-bar-row">
                            <span class="xai-signal-name" style="color:#10b981;">Inventory Gate</span>
                            <div class="xai-meter-bg">
                                <div class="xai-meter-fill" style="width:${invScore > 0 ? '100' : '0'}%; background:#10b981;"></div>
                            </div>
                            <span class="xai-meter-num">${invScore > 0 ? '1.00 (Pass)' : '0.00 (Block)'}</span>
                        </div>

                        <!-- Technical Viva Evidence Box -->
                        <div class="xai-viva-box">
                            <div style="color:#38bdf8; font-weight:700; margin-bottom:0.25rem;">[MATHEMATICAL &amp; SYMBOLIC PROOF]</div>
                            <div style="margin-bottom:0.25rem;">&bull; <strong>Association Evidence:</strong> ${ruleProof}</div>
                            <div style="margin-bottom:0.25rem;">&bull; <strong>Search Evidence:</strong> ${searchProof}</div>
                            <div>&bull; <strong>Content Similarity:</strong> ${simProof}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join("");

        out.innerHTML = metaHtml + `<div class="xai-cards-grid">${cardsHtml}</div>`;

    } catch (err) {
        console.error("Error running XAI audit:", err);
        out.innerHTML = `<div style="text-align:center; color:var(--accent-rose); padding:2rem;">Error executing recommendation audit: ${escapeHtml(err.message)}</div>`;
    }
}

// =============================================================================
// PHASE 7: BUSINESS INTELLIGENCE (CUSTOMER, INVENTORY, PRODUCT & AI INSIGHTS)
// =============================================================================

// State Variables for Phase 7
let ciData = null;
let activeCiSegmentFilter = "ALL";
let ciSearchTerm = "";

let invData = null;
let activeInvRiskFilter = "ALL";
let invSearchTerm = "";

let prodData = null;
let activeProdCategoryFilter = "ALL";
let prodSearchTerm = "";

let aiInsightsData = null;
let activeInsightCategoryFilter = "ALL";

// Helper color palette for segments
const segmentColorMap = {
    "HIGH VALUE": "#8b5cf6",
    "FREQUENT SHOPPER": "#0ea5e9",
    "ACTIVE SHOPPER": "#10b981",
    "OCCASIONAL SHOPPER": "#f59e0b",
    "NEW CUSTOMER": "#3b82f6",
    "AT-RISK / INACTIVE": "#f43f5e"
};

// -----------------------------------------------------------------------------
// 1. CUSTOMER INTELLIGENCE & RFM SEGMENTATION
// -----------------------------------------------------------------------------

async function loadAdminCustomerIntelligence() {
    try {
        const res = await fetch(`${API_BASE}/api/admin/customer-segments`);
        const json = await res.json();
        if (json.status !== "success") return;

        ciData = json;
        const ov = json.overall_metrics;

        // Populate KPIs
        const elTotal = document.getElementById("ciKpiTotalCustomers");
        const elActive = document.getElementById("ciKpiActiveShoppers");
        const elAvgSpend = document.getElementById("ciKpiAvgSpend");
        const elAov = document.getElementById("ciKpiStoreAov");
        const elFreq = document.getElementById("ciKpiAvgFreq");

        if (elTotal) elTotal.innerText = ov.total_customers || 0;
        if (elActive) elActive.innerText = ov.active_shoppers || 0;
        if (elAvgSpend) elAvgSpend.innerText = formatMoney(ov.avg_spend_per_customer || 0);
        if (elAov) elAov.innerText = formatMoney(ov.overall_aov || 0);
        if (elFreq) elFreq.innerText = `${ov.avg_order_frequency || 0} orders`;

        // Render Visual Distribution Bar & Pills
        renderCiVisualBarAndPills();

        // Render Segment Breakdown Cards
        renderCiSegmentCards();

        // Populate Customer Inspector Dropdown
        const sel = document.getElementById("ciCustomerSelect");
        if (sel) {
            sel.innerHTML = json.customers.map(c => `
                <option value="${c.customer_id}">${c.customer_id} &bull; ${escapeHtml(c.name)} (${c.segment})</option>
            `).join("");

            // Inspect first customer automatically
            if (json.customers.length > 0) {
                inspectCustomerBi(json.customers[0].customer_id);
            }
        }

        // Render Customers Table
        renderCiCustomerTable();

    } catch (err) {
        console.error("Error loading Customer Intelligence:", err);
    }
}

function renderCiVisualBarAndPills() {
    if (!ciData) return;
    const barWrap = document.getElementById("ciSegmentVisualBar");
    const pillsWrap = document.getElementById("ciSegmentFilterPills");

    // Visual Distribution Bar
    if (barWrap) {
        barWrap.innerHTML = ciData.segment_breakdown.map(s => {
            if (s.count === 0) return "";
            const color = segmentColorMap[s.segment] || "#6366f1";
            return `
                <div class="segment-bar-slice" 
                     style="width:${s.percentage}%; background-color:${color};" 
                     title="${s.segment}: ${s.count} customers (${s.percentage}%)"
                     onclick="filterCiCustomersBySegment('${s.segment}')"></div>
            `;
        }).join("");
    }

    // Segment Filter Pills
    if (pillsWrap) {
        let pillsHtml = `
            <button class="seg-pill ${activeCiSegmentFilter === 'ALL' ? 'active' : ''}" 
                    onclick="filterCiCustomersBySegment('ALL')">
                All Customers (${ciData.customers.length})
            </button>
        `;
        pillsHtml += ciData.segment_breakdown.map(s => `
            <button class="seg-pill ${activeCiSegmentFilter === s.segment ? 'active' : ''}" 
                    onclick="filterCiCustomersBySegment('${s.segment}')">
                ${s.segment} (${s.count})
            </button>
        `).join("");
        pillsWrap.innerHTML = pillsHtml;
    }
}

function renderCiSegmentCards() {
    if (!ciData) return;
    const grid = document.getElementById("ciSegmentCardsGrid");
    if (!grid) return;

    grid.innerHTML = ciData.segment_breakdown.map(s => {
        const color = segmentColorMap[s.segment] || "#6366f1";
        const isActive = activeCiSegmentFilter === s.segment ? "active" : "";
        return `
            <div class="segment-card ${isActive}" onclick="filterCiCustomersBySegment('${s.segment}')">
                <div class="segment-card-header">
                    <span class="segment-card-title" style="color:${color};">${s.segment}</span>
                    <span class="${s.badge_class}">${s.percentage}%</span>
                </div>
                <div class="segment-card-count">${s.count}</div>
                <div class="segment-card-sub">
                    <span>Avg Spend: <strong>${formatMoney(s.avg_spend)}</strong></span>
                    <span>Avg Orders: <strong>${s.avg_orders}</strong> &bull; AOV: <strong>${formatMoney(s.aov)}</strong></span>
                </div>
            </div>
        `;
    }).join("");
}

function filterCiCustomersBySegment(segmentName) {
    activeCiSegmentFilter = segmentName;
    renderCiVisualBarAndPills();
    renderCiSegmentCards();
    renderCiCustomerTable();
}

function handleCiSearchInput() {
    const input = document.getElementById("ciCustomerSearchInput");
    ciSearchTerm = input ? input.value.trim().toLowerCase() : "";
    renderCiCustomerTable();
}

function renderCiCustomerTable() {
    if (!ciData) return;
    const tbody = document.getElementById("ciCustomerTableBody");
    if (!tbody) return;

    let filtered = ciData.customers.filter(c => {
        const matchesSeg = (activeCiSegmentFilter === "ALL" || c.segment === activeCiSegmentFilter);
        const matchesSearch = !ciSearchTerm || 
            c.name.toLowerCase().includes(ciSearchTerm) ||
            c.customer_id.toLowerCase().includes(ciSearchTerm) ||
            (c.city && c.city.toLowerCase().includes(ciSearchTerm));
        return matchesSeg && matchesSearch;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:2rem; color:var(--text-muted);">No customers match the active segment or search filter.</td></tr>`;
        return;
    }

    const badgeMap = {
        "HIGH VALUE": "badge-high-value",
        "FREQUENT SHOPPER": "badge-frequent",
        "ACTIVE SHOPPER": "badge-active",
        "OCCASIONAL SHOPPER": "badge-occasional",
        "NEW CUSTOMER": "badge-new",
        "AT-RISK / INACTIVE": "badge-inactive"
    };

    tbody.innerHTML = filtered.map(c => {
        const bClass = badgeMap[c.segment] || "badge-default";
        const recText = c.recency_days !== null ? `${c.recency_days}d ago` : "Never";
        return `
            <tr>
                <td><strong>${c.customer_id}</strong></td>
                <td>
                    <div style="font-weight:600; color:var(--text-primary);">${escapeHtml(c.name)}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(c.email)}</div>
                </td>
                <td>${escapeHtml(c.city || 'Seattle')}</td>
                <td><span class="${bClass}">${c.segment}</span></td>
                <td><strong>${c.total_orders}</strong></td>
                <td><strong>${formatMoney(c.lifetime_spend)}</strong></td>
                <td>${formatMoney(c.aov)}</td>
                <td>${recText}</td>
                <td><span style="font-family:monospace; font-weight:700; color:#818cf8;">${c.rfm_scores.rfm_tier}</span></td>
                <td>
                    <button class="btn-secondary" style="padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="inspectCustomerBi('${c.customer_id}')">
                        Inspect &rarr;
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

function handleCiCustomerSelectChange() {
    const sel = document.getElementById("ciCustomerSelect");
    if (sel && sel.value) {
        inspectCustomerBi(sel.value);
    }
}

async function inspectCustomerBi(customerId) {
    const container = document.getElementById("ciCustomerDetailContent");
    if (!container) return;

    container.innerHTML = `<div style="text-align:center; padding:2rem; color:var(--text-muted);">Loading customer insights for ${customerId}...</div>`;

    // Sync select element if needed
    const sel = document.getElementById("ciCustomerSelect");
    if (sel && sel.value !== customerId) {
        sel.value = customerId;
    }

    try {
        const res = await fetch(`${API_BASE}/api/admin/customer/${customerId}/insights`);
        const json = await res.json();
        if (json.status !== "success") {
            container.innerHTML = `<div style="color:var(--accent-rose); padding:1rem;">Error: ${json.message || 'Could not fetch customer details'}</div>`;
            return;
        }

        const c = json.customer;
        const initials = c.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase();
        const badgeMap = {
            "HIGH VALUE": "badge-high-value",
            "FREQUENT SHOPPER": "badge-frequent",
            "ACTIVE SHOPPER": "badge-active",
            "OCCASIONAL SHOPPER": "badge-occasional",
            "NEW CUSTOMER": "badge-new",
            "AT-RISK / INACTIVE": "badge-inactive"
        };
        const bClass = badgeMap[c.segment] || "badge-default";
        const recText = c.recency_days !== null ? `${c.recency_days} days ago` : "Never ordered";

        container.innerHTML = `
            <div class="ci-detail-grid">
                <!-- Left: Profile & Key Scores -->
                <div class="ci-profile-card">
                    <div class="ci-profile-top">
                        <div class="ci-avatar">${initials}</div>
                        <div>
                            <h3 style="font-size:1.1rem; font-weight:700; color:var(--text-primary);">${escapeHtml(c.name)}</h3>
                            <div style="font-size:0.78rem; color:var(--text-muted);">${c.customer_id} &bull; ${escapeHtml(c.city || 'Seattle')}</div>
                        </div>
                    </div>

                    <div style="margin-bottom:0.85rem;">
                        <span class="${bClass}" style="font-size:0.85rem; padding:0.35rem 0.75rem;">${c.segment}</span>
                    </div>

                    <div class="ci-rfm-chip-row">
                        <div class="ci-rfm-chip">
                            <span>Recency (R)</span>
                            <strong>${c.rfm_scores.recency_score}/5</strong>
                        </div>
                        <div class="ci-rfm-chip">
                            <span>Frequency (F)</span>
                            <strong>${c.rfm_scores.frequency_score}/5</strong>
                        </div>
                        <div class="ci-rfm-chip">
                            <span>Monetary (M)</span>
                            <strong>${c.rfm_scores.monetary_score}/5</strong>
                        </div>
                        <div class="ci-rfm-chip" style="border-color:#818cf8;">
                            <span>Composite</span>
                            <strong>${c.rfm_scores.composite_score}</strong>
                        </div>
                    </div>

                    <div style="font-size:0.82rem; display:flex; flex-direction:column; gap:0.4rem; padding-top:0.5rem; border-top:1px solid var(--border-subtle);">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:var(--text-muted);">Lifetime Spend:</span>
                            <strong>${formatMoney(c.lifetime_spend)}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:var(--text-muted);">Completed Orders:</span>
                            <strong>${c.total_orders} orders</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:var(--text-muted);">Average Order Value:</span>
                            <strong>${formatMoney(c.aov)}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:var(--text-muted);">Last Purchase:</span>
                            <strong>${recText}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:var(--text-muted);">Cart / Wishlist:</span>
                            <span>${c.cart_items_count} in cart / ${c.wishlist_items_count} saved</span>
                        </div>
                    </div>

                    <div class="ci-action-callout">
                        <h4>Recommended Business Action</h4>
                        <p>${escapeHtml(c.suggested_action)}</p>
                    </div>
                </div>

                <!-- Right: Proof Explanations & Commerce Activity -->
                <div>
                    <!-- Why Classified Here -->
                    <div class="ci-proofs-card">
                        <h4>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                            Why Classified in "${c.segment}":
                        </h4>
                        <div class="ci-proof-list">
                            ${c.reasons.map(r => `
                                <div class="ci-proof-item">
                                    <span class="ci-proof-check">&#10003;</span>
                                    <span>${escapeHtml(r)}</span>
                                </div>
                            `).join("")}
                        </div>
                    </div>

                    <!-- Mini Grid: Top Categories & Top Products -->
                    <div class="ci-mini-card-grid">
                        <div class="ci-mini-box">
                            <h4>Top Categories</h4>
                            ${c.top_categories.length === 0 ? '<p style="color:var(--text-muted); font-size:0.78rem;">No purchase history.</p>' : 
                                c.top_categories.map(cat => `
                                    <div class="ci-mini-row">
                                        <span>${escapeHtml(cat.category_name)}</span>
                                        <strong>${formatMoney(cat.category_spend)}</strong>
                                    </div>
                                `).join("")}
                        </div>

                        <div class="ci-mini-box">
                            <h4>Top Purchased Products</h4>
                            ${c.top_products.length === 0 ? '<p style="color:var(--text-muted); font-size:0.78rem;">No purchase history.</p>' : 
                                c.top_products.map(p => `
                                    <div class="ci-mini-row">
                                        <span style="max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(p.product_name)}">${escapeHtml(p.product_name)}</span>
                                        <strong>${p.total_quantity}x (${formatMoney(p.total_spend)})</strong>
                                    </div>
                                `).join("")}
                        </div>
                    </div>
                </div>
            </div>
        `;

    } catch (err) {
        console.error("Error inspecting customer:", err);
        container.innerHTML = `<div style="color:var(--accent-rose); padding:1rem;">Failed to load customer profile: ${escapeHtml(err.message)}</div>`;
    }
}

// -----------------------------------------------------------------------------
// 2. INVENTORY INTELLIGENCE & RESTOCK FORECASTS
// -----------------------------------------------------------------------------

async function loadAdminInventoryIntelligence() {
    try {
        const res = await fetch(`${API_BASE}/api/admin/inventory-intelligence?recent_days=30`);
        const json = await res.json();
        if (json.status !== "success") return;

        invData = json;
        const k = json.kpis;

        // Populate KPIs
        const elSkus = document.getElementById("invKpiTotalSkus");
        const elCrit = document.getElementById("invKpiCritical");
        const elLow = document.getElementById("invKpiLowStock");
        const elHealthy = document.getElementById("invKpiHealthy");
        const elVal = document.getElementById("invKpiValuation");

        if (elSkus) elSkus.innerText = k.total_skus || 0;
        if (elCrit) elCrit.innerText = k.critical_count || 0;
        if (elLow) elLow.innerText = k.low_stock_count || 0;
        if (elHealthy) elHealthy.innerText = k.healthy_count || 0;
        if (elVal) elVal.innerText = formatMoney(k.inventory_valuation || 0);

        // Render Restock Priority Grid
        renderInvRestockGrid();

        // Render Matrix Table
        renderInvMatrixTable();

    } catch (err) {
        console.error("Error loading Inventory Intelligence:", err);
    }
}

function renderInvRestockGrid() {
    if (!invData) return;
    const grid = document.getElementById("invRestockGrid");
    const countBadge = document.getElementById("invRestockCountBadge");
    if (!grid) return;

    const recs = invData.restock_recommendations || [];
    if (countBadge) {
        countBadge.innerText = `${recs.length} Action Items`;
    }

    if (recs.length === 0) {
        grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:2rem; color:var(--text-muted); background:var(--bg-surface-elevated); border-radius:var(--radius-md);">All product inventory levels are currently in a healthy state.</div>`;
        return;
    }

    grid.innerHTML = recs.slice(0, 6).map(r => {
        const cardClass = r.risk_state === "CRITICAL" || r.risk_state === "OUT OF STOCK" ? "critical" : "low";
        const coverStr = r.estimated_stock_cover_days !== null ? `~${Math.round(r.estimated_stock_cover_days)} days` : "0 days";
        return `
            <div class="restock-card ${cardClass}">
                <div>
                    <div class="restock-card-top">
                        <div>
                            <span class="restock-card-category">${escapeHtml(r.category_name)} &bull; SKU: ${r.product_id}</span>
                            <h4 class="restock-card-title">${escapeHtml(r.product_name)}</h4>
                        </div>
                        <span class="risk-badge risk-${r.risk_state.toLowerCase().replace(/ /g, '-')}">${r.risk_label}</span>
                    </div>

                    <div class="restock-metrics-row">
                        <div class="restock-metric-item">
                            <span>Stock</span>
                            <strong>${r.stock_quantity}</strong>
                        </div>
                        <div class="restock-metric-item">
                            <span>Velocity</span>
                            <strong>${r.avg_daily_sales}/day</strong>
                        </div>
                        <div class="restock-metric-item">
                            <span>Est. Cover</span>
                            <strong style="color:${r.risk_state === 'CRITICAL' ? '#f43f5e' : '#f59e0b'};">${coverStr}</strong>
                        </div>
                    </div>
                </div>

                <div class="restock-action-box">
                    <div style="font-weight:700; color:#e2e8f0; margin-bottom:0.25rem;">Suggested Action:</div>
                    <div>${escapeHtml(r.suggested_action)}</div>
                </div>
            </div>
        `;
    }).join("");
}

function handleInvRiskFilterChange() {
    const sel = document.getElementById("invRiskFilterSelect");
    activeInvRiskFilter = sel ? sel.value : "ALL";
    renderInvMatrixTable();
}

function handleInvSearchInput() {
    const input = document.getElementById("invSearchInput");
    invSearchTerm = input ? input.value.trim().toLowerCase() : "";
    renderInvMatrixTable();
}

function renderInvMatrixTable() {
    if (!invData) return;
    const tbody = document.getElementById("invMatrixTableBody");
    if (!tbody) return;

    let filtered = invData.inventory_matrix.filter(p => {
        const matchesRisk = (activeInvRiskFilter === "ALL" || p.risk_state === activeInvRiskFilter);
        const matchesSearch = !invSearchTerm ||
            p.product_name.toLowerCase().includes(invSearchTerm) ||
            p.product_id.toLowerCase().includes(invSearchTerm) ||
            p.category_name.toLowerCase().includes(invSearchTerm);
        return matchesRisk && matchesSearch;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:2rem; color:var(--text-muted);">No products match the active inventory filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(p => {
        const riskClass = `risk-${p.risk_state.toLowerCase().replace(/ /g, '-')}`;
        const coverStr = p.estimated_stock_cover_days !== null ? `~${Math.round(p.estimated_stock_cover_days)} days` : "N/A";
        return `
            <tr>
                <td><strong>${p.product_id}</strong></td>
                <td>
                    <div style="font-weight:600; color:var(--text-primary);">${escapeHtml(p.product_name)}</div>
                    <div style="font-size:0.72rem; color:var(--text-muted);">${escapeHtml(p.brand || '')}</div>
                </td>
                <td>${escapeHtml(p.category_name)}</td>
                <td><strong>${formatMoney(p.price)}</strong></td>
                <td><strong style="font-size:0.95rem;">${p.stock_quantity}</strong></td>
                <td>${p.units_sold} units</td>
                <td><strong>${p.avg_daily_sales}</strong> /day</td>
                <td><span style="color:#818cf8; font-weight:600;">${coverStr}</span></td>
                <td><span class="risk-badge ${riskClass}">${p.risk_state}</span></td>
                <td style="font-size:0.78rem; max-width:240px; color:var(--text-secondary);">${escapeHtml(p.suggested_action)}</td>
            </tr>
        `;
    }).join("");
}

// -----------------------------------------------------------------------------
// 3. PRODUCT INTELLIGENCE & MATRIX
// -----------------------------------------------------------------------------

async function loadAdminProductIntelligence() {
    try {
        const res = await fetch(`${API_BASE}/api/admin/product-intelligence`);
        const json = await res.json();
        if (json.status !== "success") return;

        prodData = json;
        const prods = json.products;

        // KPI calculations
        if (prods.length > 0) {
            const topRev = [...prods].sort((a, b) => b.revenue - a.revenue)[0];
            const topVol = [...prods].sort((a, b) => b.units_sold - a.units_sold)[0];
            const topRat = [...prods].sort((a, b) => (b.avg_rating || 0) - (a.avg_rating || 0))[0];

            const elRev = document.getElementById("prodKpiTopRevenue");
            const elRevVal = document.getElementById("prodKpiTopRevenueVal");
            const elVol = document.getElementById("prodKpiTopVolume");
            const elVolVal = document.getElementById("prodKpiTopVolumeVal");
            const elRat = document.getElementById("prodKpiTopRating");
            const elRatVal = document.getElementById("prodKpiTopRatingVal");
            const elPair = document.getElementById("prodKpiTopPair");
            const elPairVal = document.getElementById("prodKpiTopPairVal");

            if (elRev && topRev) {
                elRev.innerText = topRev.product_name;
                if (elRevVal) elRevVal.innerText = `${formatMoney(topRev.revenue)} gross sales`;
            }
            if (elVol && topVol) {
                elVol.innerText = topVol.product_name;
                if (elVolVal) elVolVal.innerText = `${topVol.units_sold} units sold`;
            }
            if (elRat && topRat) {
                elRat.innerText = topRat.product_name;
                if (elRatVal) elRatVal.innerText = `⭐ ${topRat.avg_rating} (${topRat.review_count} reviews)`;
            }

            // Find top companion pair
            const withCompanion = prods.filter(p => p.top_companion);
            if (withCompanion.length > 0 && elPair) {
                const topP = withCompanion.sort((a, b) => (b.top_companion.co_purchases || 0) - (a.top_companion.co_purchases || 0))[0];
                elPair.innerText = `${topP.product_id} & ${topP.top_companion.companion_id}`;
                if (elPairVal) elPairVal.innerText = `${topP.top_companion.co_purchases} co-purchases`;
            }
        }

        // Category filter dropdown
        const catSelect = document.getElementById("prodCategoryFilterSelect");
        if (catSelect) {
            const uniqueCats = Array.from(new Set(prods.map(p => p.category_name)));
            catSelect.innerHTML = `<option value="ALL">All Categories (${prods.length})</option>` +
                uniqueCats.map(c => `<option value="${c}">${c}</option>`).join("");
        }

        // Render Matrix Table
        renderProdMatrixTable();

    } catch (err) {
        console.error("Error loading Product Intelligence:", err);
    }
}

function handleProdFilterChange() {
    const catSelect = document.getElementById("prodCategoryFilterSelect");
    const searchInput = document.getElementById("prodSearchInput");

    activeProdCategoryFilter = catSelect ? catSelect.value : "ALL";
    prodSearchTerm = searchInput ? searchInput.value.trim().toLowerCase() : "";

    renderProdMatrixTable();
}

function renderProdMatrixTable() {
    if (!prodData) return;
    const tbody = document.getElementById("prodMatrixTableBody");
    if (!tbody) return;

    let filtered = prodData.products.filter(p => {
        const matchesCat = (activeProdCategoryFilter === "ALL" || p.category_name === activeProdCategoryFilter);
        const matchesSearch = !prodSearchTerm ||
            p.product_name.toLowerCase().includes(prodSearchTerm) ||
            p.product_id.toLowerCase().includes(prodSearchTerm) ||
            p.brand.toLowerCase().includes(prodSearchTerm);
        return matchesCat && matchesSearch;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="13" style="text-align:center; padding:2rem; color:var(--text-muted);">No products match the filter criteria.</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(p => {
        const riskClass = `risk-${p.risk_state.toLowerCase().replace(/ /g, '-')}`;
        const companionHtml = p.top_companion ? 
            `<span style="color:#38bdf8; font-size:0.75rem;" title="${escapeHtml(p.top_companion.companion_name)}">${p.top_companion.companion_id} (${p.top_companion.co_purchases}x)</span>` : 
            `<span style="color:var(--text-muted); font-size:0.75rem;">None</span>`;

        return `
            <tr>
                <td><strong style="color:#818cf8;">#${p.revenue_rank || '-'}</strong></td>
                <td><span style="color:var(--text-muted);">#${p.volume_rank || '-'}</span></td>
                <td><strong>${p.product_id}</strong></td>
                <td>
                    <div style="font-weight:600; color:var(--text-primary); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(p.product_name)}">${escapeHtml(p.product_name)}</div>
                    <div style="font-size:0.72rem; color:var(--text-muted);">${escapeHtml(p.brand || '')}</div>
                </td>
                <td>${escapeHtml(p.category_name)}</td>
                <td><strong>${formatMoney(p.price)}</strong></td>
                <td>${p.stock_quantity}</td>
                <td><strong>${p.units_sold}</strong></td>
                <td><strong style="color:#34d399;">${formatMoney(p.revenue)}</strong></td>
                <td>${p.avg_daily_sales}/day</td>
                <td>⭐ ${p.avg_rating} <span style="color:var(--text-muted); font-size:0.72rem;">(${p.review_count})</span></td>
                <td><span class="risk-badge ${riskClass}">${p.risk_state}</span></td>
                <td>${companionHtml}</td>
            </tr>
        `;
    }).join("");
}

// -----------------------------------------------------------------------------
// 4. AI BUSINESS INSIGHTS
// -----------------------------------------------------------------------------

async function loadAdminAiInsights() {
    try {
        const res = await fetch(`${API_BASE}/api/admin/ai-insights`);
        const json = await res.json();
        if (json.status !== "success") return;

        aiInsightsData = json;
        renderAiInsightsGrid();

    } catch (err) {
        console.error("Error loading AI Business Insights:", err);
    }
}

function filterAiInsights(cat) {
    activeInsightCategoryFilter = cat;
    document.querySelectorAll(".insight-filter-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.insightCat === cat);
    });
    renderAiInsightsGrid();
}

function renderAiInsightsGrid() {
    if (!aiInsightsData) return;
    const grid = document.getElementById("aiInsightsGrid");
    if (!grid) return;

    let filtered = aiInsightsData.insights.filter(i => {
        return activeInsightCategoryFilter === "ALL" || i.category === activeInsightCategoryFilter;
    });

    if (filtered.length === 0) {
        grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:2.5rem; color:var(--text-muted); background:var(--bg-surface-elevated); border-radius:var(--radius-md);">No insights available under the "${activeInsightCategoryFilter}" category.</div>`;
        return;
    }

    grid.innerHTML = filtered.map(item => {
        const typeClass = `type-${item.type.toLowerCase()}`;

        // Render metrics pills
        let pillsHtml = "";
        if (item.metrics) {
            pillsHtml = Object.entries(item.metrics).map(([k, v]) => {
                const label = k.replace(/_/g, ' ');
                const valFormatted = typeof v === 'number' && v > 1000 ? formatMoney(v) : v;
                return `<div class="metric-pill">${label}: <strong>${valFormatted}</strong></div>`;
            }).join("");
        }

        return `
            <div class="insight-card ${typeClass}">
                <div>
                    <div class="insight-card-header">
                        <span class="insight-badge">${item.badge}</span>
                        <span style="font-size:0.72rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.04em;">${item.category.replace(/_/g, ' ')}</span>
                    </div>

                    <h3 class="insight-title">${escapeHtml(item.title)}</h3>
                    <p class="insight-desc">${escapeHtml(item.description)}</p>

                    ${pillsHtml ? `<div class="insight-metrics-pills">${pillsHtml}</div>` : ''}
                </div>

                <div class="insight-action-box">
                    <span class="insight-action-label">Actionable Strategic Next Step</span>
                    <p class="insight-action-text">${escapeHtml(item.action)}</p>
                </div>
            </div>
        `;
    }).join("");
}

// Window bindings for Phase 7 functions
window.loadAdminCustomerIntelligence = loadAdminCustomerIntelligence;
window.filterCiCustomersBySegment = filterCiCustomersBySegment;
window.handleCiSearchInput = handleCiSearchInput;
window.handleCiCustomerSelectChange = handleCiCustomerSelectChange;
window.inspectCustomerBi = inspectCustomerBi;

window.loadAdminInventoryIntelligence = loadAdminInventoryIntelligence;
window.handleInvRiskFilterChange = handleInvRiskFilterChange;
window.handleInvSearchInput = handleInvSearchInput;

window.loadAdminProductIntelligence = loadAdminProductIntelligence;
window.handleProdFilterChange = handleProdFilterChange;

window.loadAdminAiInsights = loadAdminAiInsights;
window.filterAiInsights = filterAiInsights;

// Previous window bindings
window.handleXaiContextChange = handleXaiContextChange;
window.initXaiAuditorControls = initXaiAuditorControls;
window.runXaiAudit = runXaiAudit;


