"""
Master Regression Test Runner for NexusAI E-Commerce Platform.
Executes the comprehensive suite of database, AI, security, and API tests
across all project phases and produces an executive verification report.
"""

import unittest
import sys
import os
import time

# Add root directory to sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

# Import unittest suites
from tests.test_data_consistency import TestDataConsistencyAudit
from tests.test_acid_transactions import TestAcidTransactions
from tests.test_security_audit import TestSecurityAudit
from test_phase7_bi import TestPhase7BusinessIntelligence
from test_phase8_reviews import TestPhase8ReviewIntelligence
from test_phase9_admin import TestPhase9AdminAnalytics


class TestAiRecommenderEngine(unittest.TestCase):
    """Wraps test_ai_verification functions into unittest cases."""
    def test_01_apriori_mining(self):
        from test_ai_verification import test_apriori_math
        test_apriori_math()

    def test_02_content_based(self):
        from test_ai_verification import test_content_based_engine
        test_content_based_engine()

    def test_03_multi_signal_ranker(self):
        from test_ai_verification import test_multi_signal_ranker
        test_multi_signal_ranker()

    def test_04_hybrid_pipeline(self):
        from test_ai_verification import test_hybrid_recommender
        test_hybrid_recommender()


class TestPhase6Explainability(unittest.TestCase):
    """Wraps Phase 6 Explainable AI 10-scenario verification suite."""
    def test_all_10_xai_scenarios(self):
        from test_phase6_explainability import main
        main()


class TestEndToEndCustomerJourney(unittest.TestCase):
    """Wraps full customer journey test suite."""
    def test_complete_customer_lifecycle(self):
        from test_customer_journey import test_full_customer_journey
        test_full_customer_journey()


def run_master_suite():
    print("=" * 70)
    print(" NEXUSAI E-COMMERCE INTELLIGENCE PLATFORM: MASTER TEST RUNNER")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suites_to_run = [
        ("Database Data Consistency Audit", TestDataConsistencyAudit),
        ("ACID Transactions & Rollback", TestAcidTransactions),
        ("Security & Input Validation Audit", TestSecurityAudit),
        ("Core AI Recommender Engine", TestAiRecommenderEngine),
        ("Phase 6: Explainable AI (XAI)", TestPhase6Explainability),
        ("Phase 7: RFM Customer & Inventory BI", TestPhase7BusinessIntelligence),
        ("Phase 8: NLP Review Intelligence", TestPhase8ReviewIntelligence),
        ("Phase 9: Admin Analytics & Operations", TestPhase9AdminAnalytics),
        ("End-to-End Customer Lifecycle", TestEndToEndCustomerJourney),
    ]

    for name, test_class in suites_to_run:
        s = loader.loadTestsFromTestCase(test_class)
        suite.addTests(s)
        print(f"[*] Loaded {s.countTestCases()} test(s) from {name}")

    total_tests = suite.countTestCases()
    print("-" * 70)
    print(f"Starting execution of {total_tests} automated regression tests...")
    print("-" * 70)

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print(" MASTER REGRESSION TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests Run   : {result.testsRun}")
    print(f"Passed            : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures          : {len(result.failures)}")
    print(f"Errors            : {len(result.errors)}")
    print(f"Elapsed Time      : {elapsed:.2f}s")
    print("=" * 70)

    if result.wasSuccessful():
        print("[SUCCESS] ALL SYSTEM MODULES & REGRESSION INVARIANTS 100% VERIFIED!")
        return 0
    else:
        print("[FAIL] Some tests failed. Please inspect logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_master_suite())
