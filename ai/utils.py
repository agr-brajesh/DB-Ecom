"""
AI Utility Functions & Common Data Structures for NexusAI Recommendation Engine
Provides text tokenization, vector math (cosine similarity), normalization helpers,
and shared catalog metadata caching to prevent redundant database queries.
"""

import math
import re
import sqlite3
from typing import List, Dict, Set, Optional

# Standard English stopwords
STOPWORDS = {
    'with', 'and', 'the', 'for', 'in', 'of', 'to', 'on', 'a', 'an', 'is', 'it', 'at', 'by',
    'this', 'that', 'from', 'or', 'as', 'your', 'has', 'have', 'are', 'be', 'all', 'more',
    'than', 'most', 'very', 'can', 'will', 'just', 'should', 'would', 'any', 'into'
}


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase alphanumeric tokens of length >= 2 without stopwords."""
    if not text:
        return []
    tokens = re.findall(r'\b[a-zA-Z0-9]{2,}\b', text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two vectors (assumes L2 normalized vectors)."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    return max(0.0, min(1.0, float(sum(a * b for a, b in zip(vec_a, vec_b)))))


def min_max_scale(val: float, min_val: float, max_val: float) -> float:
    """Scales a value linearly to the range [0.0, 1.0]."""
    if max_val <= min_val:
        return 1.0 if val >= max_val else 0.0
    scaled = (val - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, float(scaled)))


def log_scale(val: float, max_val: float) -> float:
    """Logarithmic scaling to compress high-variance counts into [0.0, 1.0]."""
    if val <= 0:
        return 0.0
    if max_val <= 0:
        return 0.0
    return max(0.0, min(1.0, float(math.log1p(val) / math.log1p(max_val))))


class CatalogMetadata:
    """
    In-memory cache for product metadata, inventory, ratings, and performance metrics.
    Avoids opening new database connections or querying SQLite in tight recommendation loops.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.products: Dict[str, Dict] = {}
        self.categories: Dict[str, str] = {}
        self.max_units_sold: int = 1
        self.max_reviews: int = 1
        self.load()

    def load(self):
        """Loads product catalog, categories, and aggregated performance views into memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load categories
        cursor.execute("SELECT category_id, category_name FROM categories;")
        self.categories = {row[0]: row[1] for row in cursor.fetchall()}

        # Load product details with reviews summary
        cursor.execute("""
            SELECT p.product_id, p.product_name, p.brand, p.price, p.stock_quantity,
                   p.category_id, cat.category_name, p.description,
                   ROUND(AVG(r.rating), 2) as avg_rating, COUNT(r.review_id) as review_count
            FROM products p
            JOIN categories cat ON p.category_id = cat.category_id
            LEFT JOIN reviews r ON p.product_id = r.product_id
            GROUP BY p.product_id;
        """)
        for r in cursor.fetchall():
            pid = r[0]
            self.products[pid] = {
                "product_id": pid,
                "product_name": r[1],
                "brand": r[2] or "Generic",
                "price": float(r[3]),
                "stock_quantity": int(r[4]),
                "category_id": r[5],
                "category_name": r[6],
                "description": r[7] or "",
                "avg_rating": float(r[8]) if r[8] is not None else 4.5,
                "review_count": int(r[9]),
                "units_sold": 0  # Will be populated from v_product_performance
            }

        # Load units_sold from view v_product_performance
        try:
            cursor.execute("SELECT product_id, units_sold FROM v_product_performance;")
            for pid, sold in cursor.fetchall():
                if pid in self.products:
                    self.products[pid]["units_sold"] = int(sold or 0)
        except Exception:
            pass

        conn.close()

        # Compute maximums for normalization
        if self.products:
            self.max_units_sold = max(p["units_sold"] for p in self.products.values()) or 1
            self.max_reviews = max(p["review_count"] for p in self.products.values()) or 1

    def get(self, product_id: str) -> Optional[Dict]:
        return self.products.get(product_id)

    def all_products(self) -> List[Dict]:
        return list(self.products.values())
