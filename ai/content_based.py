"""
Content-Based Filtering using Cosine Similarity
Calculates semantic and keyword similarity across product descriptions,
categories, and brands using Term Frequency-Inverse Document Frequency (TF-IDF)
and Cosine Similarity. Serves as recommendation engine for cold-start or search queries.
"""

import sqlite3
import os
import math
from typing import List, Dict, Tuple, Set, Optional
from .utils import tokenize, cosine_similarity

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "ecommerce.db")


class ContentBasedRecommender:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.products: List[Dict] = []
        self.product_index: Dict[str, int] = {}
        self.vocabulary: Dict[str, int] = {}
        self.doc_vectors: List[List[float]] = []
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        return tokenize(text)

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

            idx = len(self.products)
            self.product_index[pid] = idx
            self.products.append({
                "product_id": pid,
                "product_name": name,
                "brand": brand or "Generic",
                "price": price,
                "category_name": cat_name,
                "description": desc or ""
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
        return cosine_similarity(vec_a, vec_b)

    def compute_product_similarity(self, pid_a: str, pid_b: str) -> float:
        """Computes exact cosine similarity between two product TF-IDF document vectors."""
        idx_a = self.product_index.get(pid_a)
        idx_b = self.product_index.get(pid_b)
        if idx_a is None or idx_b is None:
            return 0.0
        return self._cosine_similarity(self.doc_vectors[idx_a], self.doc_vectors[idx_b])

    def score_search_query(self, query: str, product_id: str) -> float:
        """Computes cosine similarity between an arbitrary search query and a product's vector."""
        idx = self.product_index.get(product_id)
        if idx is None:
            return 0.0

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0.0

        q_vec = [0.0] * len(self.vocabulary)
        for t in query_tokens:
            if t in self.vocabulary:
                q_vec[self.vocabulary[t]] += 1.0

        norm = math.sqrt(sum(v * v for v in q_vec))
        if norm > 0:
            q_vec = [v / norm for v in q_vec]

        return self._cosine_similarity(q_vec, self.doc_vectors[idx])

    def get_similar_candidate_ids(self, known_pids: Set[str], top_per_item: int = 3) -> List[str]:
        """Generates candidate product IDs that have high content similarity to any known product."""
        candidates = set()
        for pid in known_pids:
            idx = self.product_index.get(pid)
            if idx is None:
                continue
            sims = []
            target_vec = self.doc_vectors[idx]
            for o_idx, o_prod in enumerate(self.products):
                if o_idx == idx:
                    continue
                score = self._cosine_similarity(target_vec, self.doc_vectors[o_idx])
                sims.append((score, o_prod["product_id"]))
            sims.sort(key=lambda x: x[0], reverse=True)
            for _, cand_id in sims[:top_per_item]:
                candidates.add(cand_id)
        return list(candidates)

    def recommend_similar_products(self, product_id: str, top_n: int = 4) -> List[Dict]:
        """Finds most similar products to a given product using Cosine Similarity (preserved)."""
        idx = self.product_index.get(product_id)
        if idx is None:
            return []

        target_vec = self.doc_vectors[idx]
        scores = []

        for o_idx, p in enumerate(self.products):
            if o_idx == idx:
                continue
            sim = self._cosine_similarity(target_vec, self.doc_vectors[o_idx])
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
        """Recommends products matching an arbitrary search query via Cosine Similarity (preserved)."""
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
