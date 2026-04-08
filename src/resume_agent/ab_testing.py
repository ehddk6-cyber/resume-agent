"""A/B 테스트 프레임워크 - 전략 비교 및 최적화"""

from typing import Dict, List, Optional
import json

from .models import ABTestResult
from .state import Workspace


def chi_square_test(
    success_a: int, total_a: int,
    success_b: int, total_b: int,
    confidence: float = 0.95
):
    """카이제곱 검정"""
    if total_a < 2 or total_b < 2:
        return 1.0, False
    
    total = total_a + total_b
    success_total = success_a + success_b
    fail_total = (total_a - success_a) + (total_b - success_b)
    
    if success_total == 0 or fail_total == 0:
        return 1.0, False
    
    expected_a_success = success_total * total_a / total
    expected_a_fail = fail_total * total_a / total
    expected_b_success = success_total * total_b / total
    expected_b_fail = fail_total * total_b / total
    
    chi_sq = 0.0
    for obs, exp in [(success_a, expected_a_success), (total_a - success_a, expected_a_fail),
                     (success_b, expected_b_success), (total_b - success_b, expected_b_fail)]:
        if exp > 0:
            chi_sq += (obs - exp) ** 2 / exp
    
    # chi_sq > 3.841 for p < 0.05 (df=1)
    p_value = 1.0 if chi_sq == 0 else max(0.0, 1.0 - min(chi_sq / 10.0, 0.999))
    is_significant = p_value < (1 - confidence)
    
    return p_value, is_significant


class ABTest:
    """A/B 테스트 관리"""
    
    def __init__(self, ws: Workspace, test_id: Optional[str] = None):
        self.ws = ws
        self.tests_file = ws.state_dir / "ab_tests.json"
        self._tests: Dict[str, ABTestResult] = {}
        self._variants: Dict[str, Dict[str, List[str]]] = {}
        self._load()
        self.active_test_id = test_id or self._get_or_create_active_test()
    
    def _load(self):
        if self.tests_file.exists():
            with open(self.tests_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._tests = {k: ABTestResult(**v) for k, v in data.get("tests", {}).items()}
                self._variants = data.get("variants", {})
    
    def _save(self):
        self.tests_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tests_file, "w", encoding="utf-8") as f:
            json.dump({"tests": {k: v.model_dump() for k, v in self._tests.items()}, "variants": self._variants}, f, ensure_ascii=False, indent=2)
    
    def _get_or_create_active_test(self) -> str:
        for test_id, test in self._tests.items():
            if test.end_date is None:
                return test_id
        
        test_id = f"test_{len(self._tests) + 1}"
        self._tests[test_id] = ABTestResult(test_id=test_id, test_name=f"Strategy Test {len(self._tests) + 1}", strategy_a="default", strategy_b="alternative", start_date="")
        self._variants[test_id] = {"A": [], "B": []}
        self._save()
        return test_id
    
    def record_result(self, variant: str, success: bool):
        if self.active_test_id not in self._variants:
            self._variants[self.active_test_id] = {"A": [], "B": []}
        self._variants[self.active_test_id][variant].append("success" if success else "fail")
        self._update_stats()
        self._save()
    
    def _update_stats(self):
        test = self._tests.get(self.active_test_id)
        if not test:
            return
        
        variants = self._variants.get(self.active_test_id, {})
        res_a, res_b = variants.get("A", []), variants.get("B", [])
        success_a = res_a.count("success")
        success_b = res_b.count("success")
        
        test.sample_size_a = len(res_a)
        test.sample_size_b = len(res_b)
        test.success_rate_a = success_a / len(res_a) if res_a else 0.0
        test.success_rate_b = success_b / len(res_b) if res_b else 0.0
        
        if test.sample_size_a >= 5 and test.sample_size_b >= 5:
            p, sig = chi_square_test(success_a, test.sample_size_a, success_b, test.sample_size_b)
            test.p_value = p
            test.is_significant = sig
            if sig:
                test.winner = "A" if test.success_rate_a > test.success_rate_b else "B"
    
    def get_current_test(self) -> Optional[ABTestResult]:
        return self._tests.get(self.active_test_id)
    
    def get_all_tests(self) -> List[ABTestResult]:
        return list(self._tests.values())
    
    def recommend_variant(self) -> str:
        test = self.get_current_test()
        if not test:
            return "A"
        if test.is_significant and test.winner:
            return test.winner
        if test.sample_size_a > 0 and test.sample_size_b > 0:
            return "A" if test.success_rate_a >= test.success_rate_b else "B"
        return "A"
    
    def end_test(self) -> Optional[ABTestResult]:
        test = self._tests.get(self.active_test_id)
        if test:
            test.end_date = ""
            self._tests[self.active_test_id] = test
            self._save()
        return test
