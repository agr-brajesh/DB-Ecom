"""
Content-Based Filtering using Cosine Similarity
Calculates semantic and keyword similarity across product descriptions,
categories, and brands using Term Frequency-Inverse Document Frequency (TF-IDF)
and Cosine Similarity. Serves as recommendation engine for cold-start or search queries.
"""

import sqlite3
import os
import math
import re
from typing import List, Dict, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "ecommerce.db")


class ContentBasedRecommender:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.products: List[Dict] = []
        self.vocabulary: Dict[str, int] = {}
        self.doc_vectors: List[List[float]] = []
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r'\b[a-zA-Z0-9]{2,}\b', text.lower())
        stopwords = {
            'with', 'and', 'the', 'for', 'in', 'of', 'to', 'on', 'a', 'an', 'is', 'it', 'at', 'by',
            'this', 'that', 'from', 'or', 'as', 'your', 'has', 'have', 'are', 'be', 'all'
        }
        return [t for t in tokens if t not in stopwords]

    def _build_index(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.product_id, p.product_name, p.brand, p.price, cat.category_name, p.description
            FROM products p
            JOIN categories cat ON p.category_id = cat.category_id;
        """)
        rows = cursor.fetchall()
        conn.close()

        docs_tokens = []
        df: Dict[str, int] = {}

        for row in rows:
            pid, name, brand, price, cat_name, desc = row
            text = f"{name} {brand or ''} {cat_name} {desc or ''}"
            tokens = self._tokenize(text)
            docs_tokens.append(tokens)

            self.products.append({
                "product_id": pid,
                "product_name": name,
                "brand": brand,
                "price": price,
                "category_name": cat_name,
                "description": desc
            })

            # Update document frequency
            for unique_token in set(tokens):
                df[unique_token] = df.get(unique_token, 0) + 1

        # Build vocabulary
        self.vocabulary = {term: idx for idx, term in enumerate(df.keys())}
        num_docs = len(self.products)

        # Build TF-IDF vectors
        self.doc_vectors = []
        for tokens in docs_tokens:
            vec = [0.0] * len(self.vocabulary)
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            for term, count in tf.items():
                if term in self.vocabulary:
                    term_idx = self.vocabulary[term]
                    idf = math.log((num_docs + 1) / (df[term] + 1)) + 1.0
                    vec[term_idx] = (count / len(tokens)) * idf

            # Normalize vector (L2 norm)
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]

            self.doc_vectors.append(vec)

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        return sum(a * b for a, b in zip(vec_a, vec_b))

    def recommend_similar_products(self, product_id: str, top_n: int = 4) -> List[Dict]:
        """Finds most similar products to a given product using Cosine Similarity."""
        target_idx = None
        for idx, p in enumerate(self.products):
            if p["product_id"] == product_id:
                target_idx = idx
                break

        if target_idx is None:
            return []

        target_vec = self.doc_vectors[target_idx]
        scores = []

        for idx, p in enumerate(self.products):
            if idx == target_idx:
                continue
            sim = self._cosine_similarity(target_vec, self.doc_vectors[idx])
            scores.append((sim, p))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, p in scores[:top_n]:
            item = dict(p)
            item["similarity_score"] = round(sim, 4)
            item["recommendation_type"] = "Content-Based (Cosine Similarity)"
            results.append(item)
        return results

    def search_similar(self, query: str, top_n: int = 4) -> List[Dict]:
        """Recommends products matching an arbitrary search query via Cosine Similarity."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        q_vec = [0.0] * len(self.vocabulary)
        for t in query_tokens:
            if t in self.vocabulary:
                q_vec[self.vocabulary[t]] += 1.0

        norm = math.sqrt(sum(v * v for v in q_vec))
        if norm > 0:
            q_vec = [v / norm for v in q_vec]

        scores = []
        for idx, p in enumerate(self.products):
            sim = self._cosine_similarity(q_vec, self.doc_vectors[idx])
            if sim > 0:
                scores.append((sim, p))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, p in scores[:top_n]:
            item = dict(p)
            item["similarity_score"] = round(sim, 4)
            item["recommendation_type"] = "Search Intent (Cosine Similarity)"
            results.append(item)
        return results


def test_content_based():
    cb = ContentBasedRecommender()
    print("--- Similar products to UltraBook Pro Laptop (P101) ---")
    recs = cb.recommend_similar_products("P101", top_n=3)
    for r in recs:
        print(f"-> {r['product_name']} (Sim: {r['similarity_score']:.4f})")

    print("\n--- Search Query Match for 'wireless noise cancel earbuds' ---")
    search_recs = cb.search_similar("wireless noise cancel earbuds", top_n=2)
    for r in search_recs:
        print(f"-> {r['product_name']} (Sim: {r['similarity_score']:.4f})")


if __name__ == "__main__":
    test_content_based()
