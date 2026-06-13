#!/usr/bin/env python
"""Quick evaluation runner script."""

import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path / 'tests'))

# Import after path setup
import os
os.chdir(backend_path)

# Now we can import
from tests.test_triage_prioritization import TriageEvaluation


def main():
    """Run evaluation."""
    print("Starting comprehensive evaluation of triage system...")
    print("This will test 70+ cases across medical categories.\n")
    
    evaluator = TriageEvaluation()
    report = evaluator.run_all_evaluations()
    
    print('\n' + '='*80)
    print('TRIAGE SYSTEM EVALUATION REPORT')
    print('='*80)
    print(f'\nSummary:')
    print(f'  Total Cases: {report["summary"]["total_cases"]}')
    print(f'  Passed: {report["summary"]["passed"]}')
    print(f'  Failed: {report["summary"]["failed"]}')
    print(f'  Pass Rate: {report["summary"]["pass_rate"]}')
    
    print(f'\nBy Urgency Level:')
    for level, stats in report['by_urgency'].items():
        if stats['total'] > 0:
            pass_rate = (stats['passed'] / stats['total'] * 100)
            print(f'  {level}: {stats["passed"]}/{stats["total"]} ({pass_rate:.1f}%)')
    
    print(f'\nBy Category:')
    for category, stats in sorted(report['by_category'].items()):
        if stats['total'] > 0:
            pass_rate = (stats['passed'] / stats['total'] * 100)
            print(f'  {category}: {stats["passed"]}/{stats["total"]} ({pass_rate:.1f}%)')
    
    print(f'\nBy Language Type:')
    for lang_type, stats in report['by_language'].items():
        if stats['total'] > 0:
            pass_rate = (stats['passed'] / stats['total'] * 100)
            print(f'  {lang_type}: {stats["passed"]}/{stats["total"]} ({pass_rate:.1f}%)')
    
    if report['failed_cases']:
        print(f'\nTop Failed Cases (showing first 5):')
        for i, failure in enumerate(report['failed_cases'][:5], 1):
            print(f'\n  {i}. {failure["name"]} (ID: {failure["id"]}, Category: {failure["category"]})')
            print(f'     Language: {failure["language_type"]}, Age: {failure["age"]}')
            print(f'     Urgency - Expected: {failure["urgency"]["expected"]}, Got: {failure["urgency"]["actual"]}')
            print(f'     Specialty - Expected: {failure["specialty"]["expected"]}, Got: {failure["specialty"]["actual"]}')
            print(f'     Condition - Expected: {failure["condition"]["expected"]}, Got: {failure["condition"]["actual"]}')
    
    print('\n' + '='*80)
    
    # Save full report
    report_file = Path(__file__).parent / "evaluation_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report saved to: {report_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
