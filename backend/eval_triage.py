#!/usr/bin/env python
"""Quick standalone evaluation runner script."""

import sys
import json
import os
from pathlib import Path

# Setup path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))
os.chdir(backend_path)

# Import the triage service
from app.services.triage_service import triage


class QuickEvaluator:
    """Quick evaluation without pytest dependency."""
    
    def __init__(self):
        self.test_cases_file = backend_path / "app" / "rag" / "eval" / "triage_test_cases.json"
        with open(self.test_cases_file, "r") as f:
            self.test_cases = json.load(f).get("test_cases", [])
        self.results = {"passed": 0, "failed": 0, "total": 0, "failures": []}
    
    def match_specialty(self, actual: str, expected: str) -> bool:
        """Check if specialty matches."""
        if not actual or not expected:
            return False
        actual_lower = actual.lower()
        expected_lower = expected.lower()
        if actual_lower == expected_lower:
            return True
        actual_first = actual_lower.split()[0] if actual_lower else ""
        expected_first = expected_lower.split()[0] if expected_lower else ""
        return actual_first and expected_first and actual_first == expected_first
    
    def match_condition(self, actual: str, expected: str) -> bool:
        """Check if condition matches."""
        if not actual or not expected:
            return False
        actual_lower = actual.lower()
        expected_lower = expected.lower()
        if actual_lower == expected_lower:
            return True
        expected_conditions = [c.strip().lower() for c in expected.split("/")]
        for condition in expected_conditions:
            if condition in actual_lower:
                return True
        return False
    
    def evaluate_all(self):
        """Evaluate all test cases."""
        passed_by_urgency = {"HIGH": {"passed": 0, "total": 0}, 
                            "MEDIUM": {"passed": 0, "total": 0}, 
                            "LOW": {"passed": 0, "total": 0}}
        passed_by_category = {}
        passed_by_language = {"professional": {"passed": 0, "total": 0},
                             "colloquial": {"passed": 0, "total": 0}}
        
        print("Evaluating triage system...")
        print(f"Total test cases: {len(self.test_cases)}\n")
        
        for i, test_case in enumerate(self.test_cases, 1):
            query = test_case.get("query")
            age = test_case.get("age")
            expected_urgency = test_case.get("expected_urgency")
            expected_specialty = test_case.get("expected_specialty")
            expected_condition = test_case.get("expected_condition")
            language_type = test_case.get("language_type")
            category = test_case.get("category")
            
            try:
                response = triage(query=query, age=age)
                
                urgency_match = response.urgency == expected_urgency.lower()
                specialty_match = self.match_specialty(response.specialty, expected_specialty)
                condition_match = self.match_condition(response.suspected_condition, expected_condition)
                
                all_match = urgency_match and specialty_match and condition_match
                self.results["total"] += 1
                
                if all_match:
                    self.results["passed"] += 1
                else:
                    self.results["failed"] += 1
                    self.results["failures"].append({
                        "id": test_case.get("id"),
                        "name": test_case.get("name"),
                        "category": category,
                        "language": language_type,
                        "urgency": (expected_urgency, response.urgency.upper()),
                        "specialty": (expected_specialty, response.specialty),
                        "condition": (expected_condition, response.suspected_condition),
                    })
                
                # Track by urgency
                passed_by_urgency[expected_urgency]["total"] += 1
                if all_match:
                    passed_by_urgency[expected_urgency]["passed"] += 1
                
                # Track by category
                if category not in passed_by_category:
                    passed_by_category[category] = {"passed": 0, "total": 0}
                passed_by_category[category]["total"] += 1
                if all_match:
                    passed_by_category[category]["passed"] += 1
                
                # Track by language
                passed_by_language[language_type]["total"] += 1
                if all_match:
                    passed_by_language[language_type]["passed"] += 1
                
                # Progress indicator
                if i % 10 == 0:
                    print(f"  Processed {i}/{len(self.test_cases)} cases... ({self.results['passed']}/{self.results['total']} passed)")
            
            except Exception as e:
                print(f"  ERROR on case {i}: {str(e)}")
                self.results["failed"] += 1
                self.results["total"] += 1
        
        return {
            "summary": {
                "total": self.results["total"],
                "passed": self.results["passed"],
                "failed": self.results["failed"],
                "pass_rate": f"{(self.results['passed'] / self.results['total'] * 100):.1f}%" if self.results['total'] > 0 else "0%"
            },
            "by_urgency": passed_by_urgency,
            "by_category": passed_by_category,
            "by_language": passed_by_language,
            "failures": self.results["failures"][:20]  # Top 20 failures
        }


def main():
    """Run evaluation."""
    try:
        evaluator = QuickEvaluator()
        report = evaluator.evaluate_all()
        
        print('\n' + '='*80)
        print('TRIAGE SYSTEM EVALUATION REPORT')
        print('='*80)
        
        print(f'\nSummary:')
        print(f'  Total Cases: {report["summary"]["total"]}')
        print(f'  Passed: {report["summary"]["passed"]}')
        print(f'  Failed: {report["summary"]["failed"]}')
        print(f'  Pass Rate: {report["summary"]["pass_rate"]}')
        
        print(f'\nBy Urgency Level:')
        for level in ["HIGH", "MEDIUM", "LOW"]:
            stats = report["by_urgency"][level]
            if stats["total"] > 0:
                pass_rate = (stats["passed"] / stats["total"] * 100)
                print(f'  {level}: {stats["passed"]}/{stats["total"]} ({pass_rate:.1f}%)')
        
        print(f'\nBy Category:')
        for category in sorted(report["by_category"].keys()):
            stats = report["by_category"][category]
            if stats["total"] > 0:
                pass_rate = (stats["passed"] / stats["total"] * 100)
                print(f'  {category}: {stats["passed"]}/{stats["total"]} ({pass_rate:.1f}%)')
        
        print(f'\nBy Language Type:')
        for lang_type in ["professional", "colloquial"]:
            stats = report["by_language"][lang_type]
            if stats["total"] > 0:
                pass_rate = (stats["passed"] / stats["total"] * 100)
                print(f'  {lang_type}: {stats["passed"]}/{stats["total"]} ({pass_rate:.1f}%)')
        
        if report["failures"]:
            print(f'\nTop Failed Cases (showing first 5):')
            for i, failure in enumerate(report["failures"][:5], 1):
                print(f'\n  {i}. {failure["name"]} (ID: {failure["id"]}, Category: {failure["category"]})')
                print(f'     Language: {failure["language"]}, Query type: {failure["category"]}')
                exp_urg, act_urg = failure["urgency"]
                exp_spe, act_spe = failure["specialty"]
                exp_cond, act_cond = failure["condition"]
                print(f'     Urgency - Expected: {exp_urg}, Got: {act_urg}')
                print(f'     Specialty - Expected: {exp_spe}, Got: {act_spe}')
                print(f'     Condition - Expected: {exp_cond}, Got: {act_cond}')
        
        print('\n' + '='*80 + '\n')
        
        # Save full report
        report_file = backend_path / "evaluation_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Full report saved to: {report_file}\n")
        
        return 0
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
