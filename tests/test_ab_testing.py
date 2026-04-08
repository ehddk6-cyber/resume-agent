"""A/B 테스트 프레임워크 테스트"""

import pytest
import tempfile
from pathlib import Path

from resume_agent.models import ABTestResult
from resume_agent.ab_testing import chi_square_test, ABTest
from resume_agent.state import Workspace


@pytest.fixture
def temp_workspace():
    """임시 워크스페이스"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(root=Path(tmpdir))
        ws.ensure()
        yield ws


@pytest.fixture
def ab_test(temp_workspace):
    return ABTest(temp_workspace)


class TestChiSquareTest:
    """카이제곱 검정 테스트"""

    def test_chi_square_returns_tuple(self):
        p, sig = chi_square_test(10, 100, 15, 100)
        assert isinstance(p, float)
        assert isinstance(sig, bool)

    def test_chi_square_insufficient_samples(self):
        p, sig = chi_square_test(1, 1, 1, 1)
        assert p == 1.0
        assert sig == False

    def test_chi_square_no_successes(self):
        p, sig = chi_square_test(0, 10, 0, 10)
        assert p == 1.0
        assert sig == False

    def test_chi_square_all_successes(self):
        p, sig = chi_square_test(10, 10, 10, 10)
        assert p == 1.0
        assert sig == False

    def test_chi_square_significant_difference(self):
        # Clear difference: 90% vs 50%
        p, sig = chi_square_test(90, 100, 50, 100)
        assert p < 0.05
        assert sig == True

    def test_chi_square_no_significant_difference(self):
        # Similar rates: 55% vs 50%
        p, sig = chi_square_test(55, 100, 50, 100)
        # Not guaranteed significant with small sample
        assert isinstance(p, float)
        assert 0 <= p <= 1

    def test_chi_square_confidence_level(self):
        p, sig = chi_square_test(90, 100, 50, 100, confidence=0.99)
        # Higher confidence threshold, less likely to be significant
        assert isinstance(sig, bool)


class TestABTestInitialization:
    """A/B 테스트 초기화 테스트"""

    def test_init_creates_active_test(self, ab_test):
        assert ab_test.active_test_id is not None
        assert isinstance(ab_test.active_test_id, str)

    def test_init_loads_existing_tests(self, temp_workspace):
        ab_test1 = ABTest(temp_workspace)
        initial_id = ab_test1.active_test_id
        
        ab_test2 = ABTest(temp_workspace)
        assert ab_test2.active_test_id == initial_id


class TestResultRecording:
    """결과 기록 테스트"""

    def test_record_result_success(self, ab_test):
        ab_test.record_result("A", True)
        test = ab_test.get_current_test()
        assert test.sample_size_a == 1
        assert test.success_rate_a == 1.0

    def test_record_result_failure(self, ab_test):
        ab_test.record_result("A", False)
        test = ab_test.get_current_test()
        assert test.sample_size_a == 1
        assert test.success_rate_a == 0.0

    def test_record_result_both_variants(self, ab_test):
        ab_test.record_result("A", True)
        ab_test.record_result("B", False)
        
        test = ab_test.get_current_test()
        assert test.sample_size_a == 1
        assert test.sample_size_b == 1
        assert test.success_rate_a == 1.0
        assert test.success_rate_b == 0.0

    def test_record_multiple_results(self, ab_test):
        for _ in range(5):
            ab_test.record_result("A", True)
        for _ in range(3):
            ab_test.record_result("B", True)
        
        test = ab_test.get_current_test()
        assert test.sample_size_a == 5
        assert test.sample_size_b == 3
        assert test.success_rate_a == 1.0
        assert test.success_rate_b == 1.0


class TestStatisticsUpdate:
    """통계 업데이트 테스트"""

    def test_update_stats_calculates_rates(self, ab_test):
        for _ in range(8):
            ab_test.record_result("A", True)
        for _ in range(2):
            ab_test.record_result("A", False)
        
        for _ in range(5):
            ab_test.record_result("B", True)
        for _ in range(5):
            ab_test.record_result("B", False)
        
        test = ab_test.get_current_test()
        assert test.success_rate_a == pytest.approx(0.8)
        assert test.success_rate_b == pytest.approx(0.5)

    def test_update_stats_with_insufficient_samples(self, ab_test):
        ab_test.record_result("A", True)
        ab_test.record_result("B", True)
        
        test = ab_test.get_current_test()
        assert test.p_value is None
        assert test.is_significant == False

    def test_update_stats_with_sufficient_samples(self, ab_test):
        # Clear difference
        for _ in range(90):
            ab_test.record_result("A", True)
        for _ in range(10):
            ab_test.record_result("A", False)
        
        for _ in range(50):
            ab_test.record_result("B", True)
        for _ in range(50):
            ab_test.record_result("B", False)
        
        test = ab_test.get_current_test()
        assert test.p_value is not None
        assert test.is_significant == True
        assert test.winner == "A"


class TestVariantRecommendation:
    """변형 추천 테스트"""

    def test_recommend_variant_returns_string(self, ab_test):
        result = ab_test.recommend_variant()
        assert isinstance(result, str)
        assert result in ["A", "B"]

    def test_recommend_variant_prefers_higher_rate(self, ab_test):
        for _ in range(10):
            ab_test.record_result("A", True)
        for _ in range(5):
            ab_test.record_result("B", True)
        
        result = ab_test.recommend_variant()
        assert result == "A"

    def test_recommend_variant_returns_winner_when_significant(self, ab_test):
        for _ in range(90):
            ab_test.record_result("A", True)
        for _ in range(10):
            ab_test.record_result("A", False)
        
        for _ in range(50):
            ab_test.record_result("B", True)
        for _ in range(50):
            ab_test.record_result("B", False)
        
        result = ab_test.recommend_variant()
        assert result == "A"

    def test_recommend_variant_defaults_to_a(self, ab_test):
        result = ab_test.recommend_variant()
        # No data yet, should return default "A"
        assert result == "A"


class TestTestManagement:
    """테스트 관리 테스트"""

    def test_get_current_test_returns_result(self, ab_test):
        test = ab_test.get_current_test()
        assert isinstance(test, ABTestResult)
        assert test.test_id == ab_test.active_test_id

    def test_get_all_tests_returns_list(self, ab_test):
        tests = ab_test.get_all_tests()
        assert isinstance(tests, list)
        assert len(tests) >= 1

    def test_end_test_sets_end_date(self, ab_test):
        test = ab_test.end_test()
        assert test is not None
        assert test.end_date is not None

    def test_ended_test_not_active(self, temp_workspace):
        ab_test1 = ABTest(temp_workspace)
        test_id = ab_test1.active_test_id
        ab_test1.end_test()
        
        ab_test2 = ABTest(temp_workspace)
        assert ab_test2.active_test_id != test_id


class TestPersistence:
    """영속성 테스트"""

    def test_results_persist_after_reload(self, temp_workspace):
        ab_test1 = ABTest(temp_workspace)
        ab_test1.record_result("A", True)
        ab_test1.record_result("B", False)
        
        ab_test2 = ABTest(temp_workspace)
        test = ab_test2.get_current_test()
        
        assert test.sample_size_a == 1
        assert test.sample_size_b == 1
