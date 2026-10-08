# NexusAI Artificial Intelligence & Analytics Architecture

## Overview

NexusAI utilizes **explainable, deterministic artificial intelligence and machine learning algorithms** designed to operate directly against relational transaction data. The platform avoids opaque external deep learning APIs and LLMs, ensuring mathematical reproducibility, low latency, and zero hallucination.

---

## 1. Apriori Association Rule Mining (Market Basket Analysis)

Implemented in [`ai/apriori.py`](../ai/apriori.py), this module discovers statistically significant co-purchase relationships between product pairs ($X \to Y$) from completed transactions aggregated in `v_market_basket`.

### Core Metrics:
1. **Support ($S$)**: Frequency with which itemset $\{X, Y\}$ appears in all transactions:
   $$\text{Support}(X \to Y) = \frac{|\{T \in D : \{X, Y\} \subseteq T\}|}{|D|}$$
2. **Confidence ($C$)**: Likelihood that $Y$ is purchased given that $X$ was purchased:
   $$\text{Confidence}(X \to Y) = \frac{\text{Support}(X \cup Y)}{\text{Support}(X)}$$
3. **Lift ($L$)**: Strength of the association rule over random co-occurrence:
   $$\text{Lift}(X \to Y) = \frac{\text{Confidence}(X \to Y)}{\text{Support}(Y)}$$
   - $L = 1$: Statistical independence.
   - $L > 1$: Positive association (items complement each other).
4. **Calibrated Affinity Score**:
   $$S_{\text{affinity}} = \min\left(1.0, 0.6 \cdot \text{Confidence} + 0.4 \cdot \frac{\text{Lift} - 1.0}{\text{Lift} + 1.0}\right)$$

---

## 2. Content-Based Filtering (TF-IDF & Cosine Similarity)

Implemented in [`ai/content_based.py`](../ai/content_based.py), this engine analyzes product attributes (brand, title, description, category) to determine metadata proximity.

### Algorithm Steps:
1. **Text Preprocessing**: Tokenization, lowercasing, punctuation stripping, and stopword removal.
2. **Term Frequency-Inverse Document Frequency (TF-IDF)**:
   $$\text{TF}(t, d) = \frac{f_{t,d}}{|d|}, \quad \text{IDF}(t, D) = \ln\left(1 + \frac{|D|}{1 + |\{d \in D : t \in d\}|}\right)$$
   $$\text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \text{IDF}(t, D)$$
3. **Cosine Similarity**:
   $$\text{CosineSimilarity}(\vec{u}, \vec{v}) = \frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\|_2 \|\vec{v}\|_2}$$

---

## 3. Multi-Signal Hybrid Ranker

Implemented in [`ai/ranking.py`](../ai/ranking.py), this ranker synthesizes diverse signals into a single calibrated ranking score bounded between $0.0$ and $1.0$:

$$\text{Final Score} = w_a S_{\text{apriori}} + w_c S_{\text{content}} + w_s S_{\text{search}} + w_p S_{\text{popularity}} + w_i S_{\text{inventory}}$$

| Signal Name | Weight | Primary Data Source | Operational Role |
|---|---|---|---|
| **Apriori Affinity** ($S_a$) | **0.40** | `order_items`, `v_market_basket` | Co-purchase cross-sell complement |
| **Content Similarity** ($S_c$) | **0.25** | `products.description`, `brand` | Feature and specification relevance |
| **Search Intent** ($S_s$) | **0.20** | `search_history` | Active user intention alignment |
| **Popularity Prior** ($S_p$) | **0.10** | `reviews`, `v_product_performance` | Quality and sales velocity assurance |
| **Inventory Availability** ($S_i$) | **0.05** | `products.stock_quantity` | Stock-out exclusion and stock urgency |

---

## 4. Explainable AI (XAI) & Provenance Tracing

Implemented in [`ai/explanations.py`](../ai/explanations.py), the explanation engine produces verifiable reasons for recommendations.

### Algorithmic Safeguards:
- **Zero Fabrication**: A search intent reason is only emitted if the customer has an actual matching query in `search_history`.
- **Truthful Market Basket Proofs**: Co-purchase reasons are only emitted if the Apriori confidence threshold is satisfied.
- **Match Calibration**:
  $$\text{Match Percentage} = \text{round}(50 + 48 \times \text{Final Score})$$
  - Score $\ge 0.75$: *Strong Affinity* (86% - 98%)
  - Score $\ge 0.50$: *Moderate Affinity* (74% - 85%)
  - Score $< 0.50$: *Good Match* (50% - 73%)

---

## 5. RFM Customer Segmentation

Implemented in [`ai/business_intelligence.py`](../ai/business_intelligence.py), customers are segmented into 6 deterministic cohorts based on purchase history:

1. **Recency ($R$)**: Days since last completed transaction relative to reference date.
2. **Frequency ($F$)**: Total number of completed orders.
3. **Monetary ($M$)**: Total gross lifetime expenditure.

| Segment Name | Classification Rule | Recommended Business Action |
|---|---|---|
| `HIGH VALUE` | Spend $\ge \$1,000$ and Orders $\ge 3$ | VIP loyalty rewards & concierge support |
| `FREQUENT SHOPPER`| Orders $\ge 5$ and Spend $< \$1,000$ | Category expansion & bundle cross-sells |
| `ACTIVE SHOPPER` | Orders $\ge 2$ and Recency $\le 30$ days | Regular product engagement & flash deals |
| `NEW CUSTOMER` | Orders $\le 1$ and Recency $\le 14$ days | Onboarding welcome series & guidance |
| `OCCASIONAL` | Orders $2..4$ and Recency $> 30$ days | Re-engagement discounts |
| `AT-RISK / INACTIVE`| Orders $\ge 1$ and Recency $> 60$ days | Win-back promotional discount campaign |

---

## 6. Operational Inventory Intelligence

Calculates dynamic stock risk based on current inventory and run-rate velocities:

$$\text{Daily Sales Velocity} = \frac{\text{Total Units Sold in Active Window}}{\text{Window Days}}$$
$$\text{Estimated Stock Cover (Days)} = \frac{\text{Current Stock Quantity}}{\text{Daily Sales Velocity}}$$

### Risk Categories:
- **OUT OF STOCK**: Stock $= 0$. Immediate supplier reorder required.
- **CRITICAL**: Cover $\le 7$ days or Stock $\le 20$. Urgent supplier purchase order.
- **LOW STOCK**: Cover $\le 15$ days or Stock $\le 50$. Reorder queue notification.
- **HEALTHY**: Cover $> 15$ days. Adequate buffer.

---

## 7. Review Sentiment Intelligence & NLP

Implemented in [`ai/sentiment.py`](../ai/sentiment.py), customer review texts are evaluated using a domain-specific lexicon tailored for consumer hardware and electronics.

### Capabilities:
- **Sentiment Polarity Scoring**: Normalized score between $-1.0$ (strongly negative) and $+1.0$ (strongly positive).
- **Aspect Theme Extraction**: Identifies domain-specific dimensions:
  - *Build Quality* (durability, materials, finish)
  - *Battery Life* (charging, endurance, battery drain)
  - *Performance* (speed, reliability, stability)
  - *Value for Money* (price, worth, expensive)
- **Rating-Review Mismatch Detection**: Flags reviews where numerical rating (e.g., 5 stars) disagrees with text sentiment (e.g., negative complaint text), protecting catalog integrity.
