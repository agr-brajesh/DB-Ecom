"""
Apriori Algorithm from Scratch for E-Commerce Market Basket Analysis
Reads transaction baskets from database view 'v_market_basket',
computes frequent itemsets, and generates association rules with
Support, Confidence, and Lift metrics.
"""

import sqlite3
import os
from itertools import combinations
from typing import List, Dict, Set, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "ecommerce.db")


class AprioriMiner:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.transactions: List[Set[str]] = []
        self.total_transactions: int = 0
        self.product_name_map: Dict[str, str] = {}
        self.product_price_map: Dict[str, float] = {}
        self.product_category_map: Dict[str, str] = {}
        self.frequent_itemsets: Dict[int, Dict[frozenset, int]] = {}
        self.association_rules: List[Dict] = []
        self._load_data()

    def _load_data(self):
        """Loads product catalog and transaction baskets from database views."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load product metadata
        cursor.execute("SELECT product_id, product_name, price, category_id FROM products;")
        for pid, name, price, cat_id in cursor.fetchall():
            self.product_name_map[pid] = name
            self.product_price_map[pid] = price
            self.product_category_map[pid] = cat_id

        # Load market baskets from view v_market_basket
        cursor.execute("SELECT product_ids FROM v_market_basket;")
        rows = cursor.fetchall()
        for row in rows:
            if row[0]:
                items = set(row[0].split(","))
                if len(items) >= 1:
                    self.transactions.append(items)

        self.total_transactions = len(self.transactions)
        conn.close()

    def find_frequent_itemsets(self, min_support: float = 0.04) -> Dict[int, Dict[frozenset, int]]:
        """
        Computes frequent itemsets L1, L2, L3... using Apriori property.
        """
        min_count = max(1, int(min_support * self.total_transactions))
        
        # Step 1: Candidate 1-itemsets (C1)
        item_counts: Dict[frozenset, int] = {}
        for trans in self.transactions:
            for item in trans:
                key = frozenset([item])
                item_counts[key] = item_counts.get(key, 0) + 1

        # L1: Filter by min_count
        l1 = {k: v for k, v in item_counts.items() if v >= min_count}
        self.frequent_itemsets[1] = l1

        k = 2
        current_l = l1
        while current_l:
            # Candidate Generation: Join L_{k-1} with itself
            candidate_k: Set[frozenset] = set()
            prev_itemsets = list(current_l.keys())
            for i in range(len(prev_itemsets)):
                for j in range(i + 1, len(prev_itemsets)):
                    union_set = prev_itemsets[i] | prev_itemsets[j]
                    if len(union_set) == k:
                        candidate_k.add(union_set)

            # Count support of candidates
            candidate_counts: Dict[frozenset, int] = {}
            for trans in self.transactions:
                for cand in candidate_k:
                    if cand.issubset(trans):
                        candidate_counts[cand] = candidate_counts.get(cand, 0) + 1

            # Filter candidates by min_count
            current_l = {k_set: cnt for k_set, cnt in candidate_counts.items() if cnt >= min_count}
            if current_l:
                self.frequent_itemsets[k] = current_l
                k += 1
            else:
                break

        return self.frequent_itemsets

    def generate_rules(self, min_confidence: float = 0.5, min_lift: float = 1.2) -> List[Dict]:
        """
        Generates association rules X -> Y from frequent itemsets.
        Calculates Support, Confidence, and Lift.
        """
        if not self.frequent_itemsets:
            self.find_frequent_itemsets()

        # Item support cache
        itemset_counts: Dict[frozenset, int] = {}
        for k, itemsets in self.frequent_itemsets.items():
            for itemset, cnt in itemsets.items():
                itemset_counts[itemset] = cnt

        self.association_rules = []

        # Iterate itemsets of size >= 2
        for k in range(2, max(self.frequent_itemsets.keys()) + 1):
            if k not in self.frequent_itemsets:
                continue

            for itemset, count_xy in self.frequent_itemsets[k].items():
                support_xy = count_xy / self.total_transactions

                # Generate all non-empty proper subsets as antecedents
                for size in range(1, len(itemset)):
                    for antecedent_tuple in combinations(itemset, size):
                        antecedent = frozenset(antecedent_tuple)
                        consequent = itemset - antecedent

                        count_x = itemset_counts.get(antecedent)
                        if not count_x:
                            continue

                        # Confidence: P(Y | X) = count(XY) / count(X)
                        confidence = count_xy / count_x

                        # Support Y
                        count_y = itemset_counts.get(consequent)
                        if not count_y:
                            # calculate manually if consequent was not in frequent_itemsets
                            count_y = sum(1 for t in self.transactions if consequent.issubset(t))
                            itemset_counts[consequent] = count_y

                        support_y = count_y / self.total_transactions
                        # Lift: P(Y|X) / P(Y)
                        lift = confidence / support_y if support_y > 0 else 0.0

                        if confidence >= min_confidence and lift >= min_lift:
                            ant_list = sorted(list(antecedent))
                            con_list = sorted(list(consequent))

                            ant_names = [self.product_name_map.get(pid, pid) for pid in ant_list]
                            con_names = [self.product_name_map.get(pid, pid) for pid in con_list]

                            self.association_rules.append({
                                "antecedent": ant_list,
                                "consequent": con_list,
                                "antecedent_names": ant_names,
                                "consequent_names": con_names,
                                "support": round(support_xy, 4),
                                "confidence": round(confidence, 4),
                                "lift": round(lift, 4),
                                "rule_string": f"{{{', '.join(ant_names)}}} => {{{', '.join(con_names)}}}"
                            })

        # Sort rules descending by confidence and lift
        self.association_rules.sort(key=lambda r: (r["lift"], r["confidence"]), reverse=True)
        return self.association_rules


def test_apriori():
    miner = AprioriMiner()
    print(f"Total Transactions Loaded from DBMS: {miner.total_transactions}")
    itemsets = miner.find_frequent_itemsets(min_support=0.04)
    for k, sets in itemsets.items():
        print(f"Frequent {k}-itemsets found: {len(sets)}")

    rules = miner.generate_rules(min_confidence=0.55, min_lift=1.5)
    print(f"\nDiscovered {len(rules)} Association Rules with Confidence >= 55% and Lift >= 1.5:\n")
    for i, r in enumerate(rules[:15], 1):
        print(f"{i:2d}. {r['rule_string']}")
        print(f"    Support: {r['support']*100:.1f}% | Confidence: {r['confidence']*100:.1f}% | Lift: {r['lift']:.2f}x\n")


if __name__ == "__main__":
    test_apriori()
