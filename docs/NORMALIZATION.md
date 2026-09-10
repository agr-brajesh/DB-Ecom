# Database Normalization Proof (UNF to 3NF / BCNF)

This document provides the formal academic justification demonstrating that the **NexusAI E-Commerce Database** adheres to Third Normal Form (3NF) and Boyce-Codd Normal Form (BCNF).

---

## 1. Unnormalized Form (UNF) Problem

If the database were stored in a single flat table:
$$\text{UNF}(\text{order\_id}, \text{customer\_id}, \text{customer\_name}, \text{city}, \text{products\_purchased}[\dots], \text{category\_name}, \text{price}, \text{payment\_method})$$

### Anomalies Encountered in UNF:
1. **Insertion Anomaly**: Cannot add a new product unless a customer places an order for it.
2. **Deletion Anomaly**: If the only order containing a rare product is deleted, the product's catalog details are permanently lost.
3. **Update Anomaly**: If a customer changes their city or email, multiple rows must be modified, leading to data inconsistency.

---

## 2. First Normal Form (1NF)

> **Definition**: A relation is in 1NF if and only if all domain values are **atomic** (no repeating groups, multi-valued attributes, or nested tables).

### Decomposition to 1NF:
- The multi-valued attribute `products_purchased` (e.g., `"Laptop, Mouse, Keyboard"`) is atomized.
- Each row represents a single product purchased in a given order.
- Functional candidate key: $\{\text{order\_id}, \text{product\_id}\}$.

$$\text{1NF\_Order}(\underline{\text{order\_id}, \text{product\_id}}, \text{customer\_id}, \text{customer\_name}, \text{city}, \text{product\_name}, \text{category\_id}, \text{category\_name}, \text{unit\_price}, \text{quantity}, \text{payment\_id}, \text{payment\_method})$$

---

## 3. Second Normal Form (2NF)

> **Definition**: A relation is in 2NF if and only if it is in 1NF and **every non-prime attribute is fully functionally dependent on the entire candidate key** (no partial dependencies).

### Identification of Partial Dependencies in 1NF:
Given composite primary key: $\{\underline{\text{order\_id}, \text{product\_id}}\}$:
- $\text{product\_id} \to \text{product\_name}, \text{category\_id}, \text{category\_name}, \text{unit\_price}$ *(Partially dependent only on `product_id`, not `order_id`)*.
- $\text{order\_id} \to \text{customer\_id}, \text{customer\_name}, \text{city}, \text{payment\_id}, \text{payment\_method}$ *(Partially dependent only on `order_id`, not `product_id`)*.
- Only $\{\underline{\text{order\_id}, \text{product\_id}}\} \to \text{quantity}$ is fully dependent on both.

### Decomposition into 2NF:
1. **`order_items`**: $\{\underline{\text{order\_id}, \text{product\_id}}, \text{quantity}, \text{unit\_price}\}$ (Fully functionally dependent).
2. **`products`**: $\{\underline{\text{product\_id}}, \text{product\_name}, \text{category\_id}, \text{category\_name}, \text{price}, \text{stock\_quantity}\}$.
3. **`orders`**: $\{\underline{\text{order\_id}}, \text{customer\_id}, \text{customer\_name}, \text{city}, \text{order\_date}, \text{total\_amount}\}$.
4. **`payments`**: $\{\underline{\text{payment\_id}}, \text{order\_id}, \text{payment\_method}, \text{payment\_status}, \text{amount}\}$.

---

## 4. Third Normal Form (3NF)

> **Definition**: A relation is in 3NF if and only if it is in 2NF and **no non-prime attribute is transitively dependent on the primary key** (i.e., if $X \to Y$ and $Y \to Z$, then $Z$ must be in a separate relation unless $Y$ is a superkey).

### Identification of Transitive Dependencies in 2NF:
1. In `products`:
   - $\text{product\_id} \to \text{category\_id}$
   - $\text{category\_id} \to \text{category\_name}, \text{description}$
   - $\implies \text{product\_id} \to \text{category\_name}$ is a **transitive dependency**.
2. In `orders`:
   - $\text{order\_id} \to \text{customer\_id}$
   - $\text{customer\_id} \to \text{customer\_name}, \text{email}, \text{phone}, \text{city}$
   - $\implies \text{order\_id} \to \text{city}$ is a **transitive dependency**.

### Final 3NF Decomposition (Implemented in `schema.sql`):
1. **`categories`** $(\underline{\text{category\_id}}, \text{category\_name}, \text{description})$
2. **`products`** $(\underline{\text{product\_id}}, \text{category\_id}^*, \text{product\_name}, \text{brand}, \text{price}, \text{stock\_quantity}, \text{description})$
3. **`customers`** $(\underline{\text{customer\_id}}, \text{name}, \text{email}, \text{phone}, \text{city})$
4. **`orders`** $(\underline{\text{order\_id}}, \text{customer\_id}^*, \text{order\_date}, \text{total\_amount}, \text{order\_status})$
5. **`order_items`** $(\underline{\text{order\_item\_id}}, \text{order\_id}^*, \text{product\_id}^*, \text{quantity}, \text{unit\_price})$
6. **`payments`** $(\underline{\text{payment\_id}}, \text{order\_id}^*, \text{payment\_method}, \text{payment\_status}, \text{amount})$
7. **`shopping_cart`** $(\underline{\text{cart\_id}}, \text{customer\_id}^*, \text{product\_id}^*, \text{quantity})$
8. **`reviews`** $(\underline{\text{review\_id}}, \text{customer\_id}^*, \text{product\_id}^*, \text{rating}, \text{comment})$
9. **`search_history`** $(\underline{\text{search\_id}}, \text{customer\_id}^*, \text{search\_query}, \text{searched\_at})$

*(Asterisk $*$ denotes Foreign Key).*

---

## 5. Summary Matrix of Normalization Compliance

| Normal Form | Requirement | Satisfied in Schema? | Justification |
| :--- | :--- | :---: | :--- |
| **1NF** | Atomic column values; no repeating arrays. | **YES** | Multi-item baskets are normalized into individual rows in `order_items`. |
| **2NF** | No partial key dependencies. | **YES** | Composite bridge `order_items(order_id, product_id)` stores only attributes dependent on both. |
| **3NF** | No transitive dependencies ($A \to B \to C$). | **YES** | Category attributes separated from Products; Customer attributes separated from Orders. |
| **BCNF** | For every functional dependency $X \to Y$, $X$ is a superkey. | **YES** | All functional determinants are candidate keys or unique primary keys. |
