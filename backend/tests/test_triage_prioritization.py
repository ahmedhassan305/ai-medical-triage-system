"""
Comprehensive evaluation test harness for medical triage system.

Evaluates triage accuracy across:
- 70+ test cases covering all medical categories
- Professional and colloquial language types
- Age ranges from newborn to elderly (0.5 - 82 years)
- Urgency levels: LOW, MEDIUM, HIGH
- Specialty accuracy: Cardiology, Neurology, Pulmonology, etc.
- Condition detection quality: 30+ different medical conditions
- Safety: Ensures dangerous cases receive HIGH urgency
"""

import json
import os
from pathlib import Path

import httpx
import pytest

from app.core.config import get_settings
from app.schemas.triage import TriageResponse
from app.services.specialties import canonicalize_specialty
from app.services.triage_service import clear_runtime_state, triage


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _ollama_reachable() -> bool:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    try:
        response = httpx.get(f"{host}/api/tags", timeout=2.0)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return False

    requested_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    models = payload.get("models", [])
    model_names = {
        item.get("name")
        for item in models
        if isinstance(item, dict) and item.get("name")
    }
    return requested_model in model_names or f"{requested_model}:latest" in model_names


def _use_live_llm_tests() -> bool:
    return _env_enabled("RUN_LIVE_LLM_TESTS") and _ollama_reachable()


class TriageEvaluation:
    """Test evaluation framework for triage system."""

    def __init__(self):
        """Initialize evaluation framework."""
        self.test_cases_file = (
            Path(__file__).parent.parent
            / "app"
            / "rag"
            / "eval"
            / "triage_test_cases.json"
        )
        self.test_cases = self._load_test_cases()
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "by_urgency": {
                "HIGH": {"total": 0, "passed": 0},
                "MEDIUM": {"total": 0, "passed": 0},
                "LOW": {"total": 0, "passed": 0},
            },
            "by_category": {},
            "by_language": {
                "professional": {"total": 0, "passed": 0},
                "colloquial": {"total": 0, "passed": 0},
            },
            "failures": [],
        }

    def _load_test_cases(self) -> list[dict]:
        """Load test cases from JSON file."""
        if not self.test_cases_file.exists():
            pytest.skip(f"Test cases file not found: {self.test_cases_file}")

        with open(self.test_cases_file, "r") as f:
            data = json.load(f)

        return data.get("test_cases", [])

    def run_all_evaluations(self):
        """Run all evaluation tests and generate report."""
        if not self.test_cases:
            pytest.skip("No test cases loaded")

        for test_case in self.test_cases:
            self.run_test_case(test_case)

        return self._generate_report()

    def run_test_case(self, test_case: dict) -> dict:
        """Run a single test case and evaluate results."""
        case_id = test_case.get("id")
        name = test_case.get("name")
        query = test_case.get("query")
        age = test_case.get("age")
        expected_urgency = test_case.get("expected_urgency")
        expected_specialty = test_case.get("expected_specialty")
        expected_condition = test_case.get("expected_condition")
        language_type = test_case.get("language_type")
        category = test_case.get("category")

        self.results["total"] += 1

        # Run triage
        response: TriageResponse = triage(query=query, age=age)

        # Evaluate results
        urgency_match = response.urgency_level == expected_urgency.lower()
        specialty_match = self._match_specialty(
            response.recommended_specialty, expected_specialty
        )
        condition_match = self._match_condition(
            response.suspected_condition, expected_condition
        )

        all_match = urgency_match and specialty_match and condition_match

        result = {
            "id": case_id,
            "name": name,
            "passed": all_match,
            "urgency": {
                "expected": expected_urgency,
                "actual": response.urgency_level.upper(),
                "match": urgency_match,
            },
            "specialty": {
                "expected": expected_specialty,
                "actual": response.recommended_specialty,
                "match": specialty_match,
            },
            "condition": {
                "expected": expected_condition,
                "actual": response.suspected_condition,
                "match": condition_match,
            },
            "language_type": language_type,
            "category": category,
            "age": age,
        }

        if all_match:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
            self.results["failures"].append(result)

        # Track by urgency
        if expected_urgency not in self.results["by_urgency"]:
            self.results["by_urgency"][expected_urgency] = {"total": 0, "passed": 0}
        self.results["by_urgency"][expected_urgency]["total"] += 1
        if all_match:
            self.results["by_urgency"][expected_urgency]["passed"] += 1

        # Track by category
        if category not in self.results["by_category"]:
            self.results["by_category"][category] = {"total": 0, "passed": 0}
        self.results["by_category"][category]["total"] += 1
        if all_match:
            self.results["by_category"][category]["passed"] += 1

        # Track by language
        if language_type not in self.results["by_language"]:
            self.results["by_language"][language_type] = {"total": 0, "passed": 0}
        self.results["by_language"][language_type]["total"] += 1
        if all_match:
            self.results["by_language"][language_type]["passed"] += 1

        return result

    def _match_specialty(self, actual: str, expected: str) -> bool:
        """Check if specialty matches (with some flexibility)."""
        if not actual or not expected:
            return False

        actual_lower = actual.lower()
        expected_lower = expected.lower()
        actual_canonical = canonicalize_specialty(actual)
        expected_canonical = canonicalize_specialty(expected)
        if actual_canonical and expected_canonical:
            return actual_canonical == expected_canonical

        # Exact match
        if actual_lower == expected_lower:
            return True

        # Partial match (first word)
        actual_first = actual_lower.split()[0] if actual_lower else ""
        expected_first = expected_lower.split()[0] if expected_lower else ""
        if actual_first and expected_first and actual_first == expected_first:
            return True

        # Common aliases
        aliases = {
            "general medicine": "internal medicine",
            "emergency": "emergency medicine",
            "surgery": "general surgery",
            "otolaryngology": "ent",
            "ent": "otolaryngology",
        }

        actual_alias = aliases.get(actual_lower, actual_lower)
        expected_alias = aliases.get(expected_lower, expected_lower)

        return actual_alias == expected_alias

    def _match_condition(self, actual: str, expected: str) -> bool:
        """Check if condition matches (with some flexibility)."""
        if not actual or not expected:
            return False

        actual_lower = actual.lower()
        expected_lower = expected.lower()

        # Exact match
        if actual_lower == expected_lower:
            return True

        # Check if actual contains any of the expected conditions
        expected_conditions = [c.strip().lower() for c in expected.split("/")]
        for condition in expected_conditions:
            if condition in actual_lower:
                return True

        # Check if any expected condition is in actual
        for condition in expected_conditions:
            if condition.split()[0] in actual_lower:  # Match by first word
                return True

        return False

    def _generate_report(self) -> dict:
        """Generate evaluation report."""
        report = {
            "summary": {
                "total_cases": self.results["total"],
                "passed": self.results["passed"],
                "failed": self.results["failed"],
                "pass_rate": (
                    f"{(self.results['passed'] / self.results['total'] * 100):.1f}%"
                    if self.results["total"] > 0
                    else "0%"
                ),
            },
            "by_urgency": self.results["by_urgency"],
            "by_category": self.results["by_category"],
            "by_language": self.results["by_language"],
            "failed_cases": [
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "urgency": f.get("urgency"),
                    "specialty": f.get("specialty"),
                    "condition": f.get("condition"),
                    "category": f.get("category"),
                    "language_type": f.get("language_type"),
                }
                for f in self.results["failures"][:20]  # Top 20 failures
            ],
        }

        return report


class TestTriagePrioritization:
    """Test suite for triage system accuracy and safety."""

    @pytest.fixture
    def evaluator(self, monkeypatch) -> TriageEvaluation:
        """Create evaluation framework; live LLM only when explicitly enabled."""
        if _use_live_llm_tests():
            monkeypatch.setenv("REASONER_MODE", "ollama")
        else:
            monkeypatch.setenv("REASONER_MODE", "stub")
        monkeypatch.setenv("RAG_RETRIEVER", "stub")
        monkeypatch.setenv("STRICT_REASONER", "false")

        # Clear caches to ensure new settings are loaded
        get_settings.cache_clear()
        clear_runtime_state()

        return TriageEvaluation()

    def test_all_cases_loaded(self, evaluator):
        """Verify test cases are loaded."""
        assert (
            len(evaluator.test_cases) >= 70
        ), f"Expected at least 70 test cases, got {len(evaluator.test_cases)}"

    def test_high_urgency_cases_detected_correctly(self, evaluator):
        """Verify HIGH urgency cases are correctly classified."""
        if os.getenv("REASONER_MODE") == "stub":
            pytest.skip(
                "Urgency classification requires live LLM. Set "
                "RUN_LIVE_LLM_TESTS=true with Ollama/model available."
            )

        high_cases = [
            tc for tc in evaluator.test_cases if tc.get("expected_urgency") == "HIGH"
        ]

        passed = 0
        for case in high_cases:
            result = evaluator.run_test_case(case)
            if result["urgency"]["match"]:
                passed += 1

        pass_rate = (passed / len(high_cases)) * 100 if high_cases else 0
        assert (
            pass_rate >= 80
        ), f"HIGH urgency detection rate: {pass_rate}% (target: >=80%)"

    def test_emergency_red_flag_detection(self, evaluator):
        """
        Verify emergency red flag cases (meningitis, stroke, appendicitis)
        are HIGH urgency.

        Note: In stub mode, this test is skipped because the stub reasoner
        returns dummy responses for testing infrastructure only.
        """
        if os.getenv("REASONER_MODE") == "stub":
            pytest.skip(
                "Emergency detection requires live LLM. Set RUN_LIVE_LLM_TESTS=true "
                "with Ollama/model available."
            )

        emergency_cases = [
            tc
            for tc in evaluator.test_cases
            if tc.get("category") == "emergency_red_flag"
        ]

        for case in emergency_cases:
            response = triage(query=case.get("query"), age=case.get("age"))
            case_name = case.get("name")
            urgency = response.urgency_level
            condition = response.suspected_condition
            assert urgency == "high", (
                f"Emergency case '{case_name}' not HIGH urgency. "
                f"Got: {urgency}, Condition: {condition}"
            )

    def test_pediatric_cases_age_aware(self, evaluator):
        """Verify pediatric cases (age < 13) receive age-appropriate classification."""
        if os.getenv("REASONER_MODE") == "stub":
            pytest.skip(
                "Age-aware classification requires live LLM. Set "
                "RUN_LIVE_LLM_TESTS=true with Ollama/model available."
            )

        pediatric_cases = [
            tc
            for tc in evaluator.test_cases
            if tc.get("category") == "pediatrics" and tc.get("age", 0) < 13
        ]

        passed = 0
        for case in pediatric_cases:
            result = evaluator.run_test_case(case)
            if result["urgency"]["match"]:
                passed += 1

        pass_rate = (passed / len(pediatric_cases)) * 100 if pediatric_cases else 0
        assert (
            pass_rate >= 70
        ), f"Pediatric urgency detection: {pass_rate}% (target: >=70%)"

    def test_colloquial_language_understanding(self, evaluator):
        """Verify system understands colloquial patient language."""
        if os.getenv("REASONER_MODE") == "stub":
            pytest.skip(
                "Language understanding requires live LLM. Set "
                "RUN_LIVE_LLM_TESTS=true with Ollama/model available."
            )

        colloquial_cases = [
            tc for tc in evaluator.test_cases if tc.get("language_type") == "colloquial"
        ]

        passed = 0
        for case in colloquial_cases:
            result = evaluator.run_test_case(case)
            if result["condition"]["match"]:
                passed += 1

        pass_rate = (passed / len(colloquial_cases)) * 100 if colloquial_cases else 0
        assert (
            pass_rate >= 70
        ), f"Colloquial condition detection: {pass_rate}% (target: >=70%)"

    def test_professional_language_accuracy(self, evaluator):
        """Verify system handles professional medical language accurately."""
        if os.getenv("REASONER_MODE") == "stub":
            pytest.skip(
                "Language accuracy requires live LLM. Set RUN_LIVE_LLM_TESTS=true "
                "with Ollama/model available."
            )

        professional_cases = [
            tc
            for tc in evaluator.test_cases
            if tc.get("language_type") == "professional"
        ]

        passed = 0
        for case in professional_cases:
            result = evaluator.run_test_case(case)
            if result["condition"]["match"]:
                passed += 1

        pass_rate = (
            (passed / len(professional_cases)) * 100 if professional_cases else 0
        )
        assert (
            pass_rate >= 85
        ), f"Professional condition detection: {pass_rate}% (target: >=85%)"

    def test_chest_disease_specialty_detection(self, evaluator):
        """Verify chest disease cases recommend Cardiology or Pulmonology."""
        if os.getenv("REASONER_MODE") == "stub":
            pytest.skip(
                "Specialty detection requires live LLM. Set RUN_LIVE_LLM_TESTS=true "
                "with Ollama/model available."
            )

        chest_cases = [
            tc for tc in evaluator.test_cases if tc.get("category") == "chest_disease"
        ]

        for case in chest_cases:
            response = triage(query=case.get("query"), age=case.get("age"))
            valid_specialties = ["cardiology", "pulmonology"]
            case_name = case.get("name")
            spec = response.recommended_specialty
            assert any(
                sp in response.recommended_specialty.lower() for sp in valid_specialties
            ), (
                f"Chest disease case '{case_name}' recommended {spec}. "
                f"Expected Cardiology or Pulmonology."
            )

    def test_routine_low_risk_cases(self, evaluator):
        """Verify routine low-risk cases don't escalate urgency unnecessarily."""
        if os.getenv("REASONER_MODE") == "stub":
            pytest.skip(
                "Low-risk detection requires live LLM. Set RUN_LIVE_LLM_TESTS=true "
                "with Ollama/model available."
            )

        low_risk_cases = [
            tc
            for tc in evaluator.test_cases
            if tc.get("category") == "routine_low_risk"
            and tc.get("expected_urgency") == "LOW"
        ]

        passed = 0
        for case in low_risk_cases:
            result = evaluator.run_test_case(case)
            if result["urgency"]["match"]:
                passed += 1

        pass_rate = (passed / len(low_risk_cases)) * 100 if low_risk_cases else 0
        assert (
            pass_rate >= 70
        ), f"Low-risk cases correctly detected: {pass_rate}% (target: >=70%)"

    def test_comprehensive_evaluation(self, evaluator):
        """
        Run comprehensive evaluation across all 70+ test cases.

        Note: In stub mode, this test is skipped because the stub reasoner
        returns dummy responses for testing infrastructure only.
        """
        if os.getenv("REASONER_MODE") == "stub":
            pytest.skip(
                "Comprehensive evaluation requires live LLM. Set "
                "RUN_LIVE_LLM_TESTS=true with Ollama/model available."
            )

        report = evaluator.run_all_evaluations()

        # Print report
        print("\n" + "=" * 80)
        print("TRIAGE SYSTEM EVALUATION REPORT")
        print("=" * 80)
        print("\nSummary:")
        print(f"  Total Cases: {report['summary']['total_cases']}")
        print(f"  Passed: {report['summary']['passed']}")
        print(f"  Failed: {report['summary']['failed']}")
        print(f"  Pass Rate: {report['summary']['pass_rate']}")

        print("\nBy Urgency Level:")
        for level, stats in report["by_urgency"].items():
            pass_rate = (
                (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            print(f"  {level}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)")

        print("\nBy Category:")
        for category, stats in report["by_category"].items():
            pass_rate = (
                (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            print(
                f"  {category}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)"
            )

        print("\nBy Language Type:")
        for lang_type, stats in report["by_language"].items():
            pass_rate = (
                (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            print(
                f"  {lang_type}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)"
            )

        if report["failed_cases"]:
            print("\nTop Failed Cases:")
            for i, failure in enumerate(report["failed_cases"][:5], 1):
                name = failure["name"]
                fid = failure["id"]
                cat = failure["category"]
                print(f"\n  {i}. {name} (ID: {fid}, Category: {cat})")
                urgency_exp = failure["urgency"]["expected"]
                urgency_act = failure["urgency"]["actual"]
                print(f"     Urgency - Expected: {urgency_exp}, Got: {urgency_act}")
                spec_exp = failure["specialty"]["expected"]
                spec_act = failure["specialty"]["actual"]
                print(f"     Specialty - Expected: {spec_exp}, Got: {spec_act}")
                cond_exp = failure["condition"]["expected"]
                cond_act = failure["condition"]["actual"]
                print(f"     Condition - Expected: {cond_exp}, Got: {cond_act}")

        print("\n" + "=" * 80)

        # Assert minimum overall pass rate
        overall_pass_rate = (
            report["summary"]["passed"] / report["summary"]["total_cases"]
        ) * 100
        assert overall_pass_rate >= 70, (
            f"Overall system pass rate is {overall_pass_rate:.1f}% (target: >=70%). "
            f"See report above for detailed failures."
        )


if __name__ == "__main__":
    """Run evaluation directly."""
    evaluator = TriageEvaluation()
    report = evaluator.run_all_evaluations()

    print(json.dumps(report, indent=2))
