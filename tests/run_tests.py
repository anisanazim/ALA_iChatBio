"""
ALA Pipeline Test Runner
Tests planner and extractor stages directly without a running server.

Usage:
    python tests/run_tests.py
    python tests/run_tests.py --verbose
    python tests/run_tests.py --stage planner
    python tests/run_tests.py --stage extractor
    python tests/run_tests.py --id occ_001
"""

import sys
import os
import json
import asyncio
import argparse
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from planning.planner import ALAPlanner
from planning.registry import ToolCapabilityRegistry
from extraction.extractor import ALAExtractor
from common.config import get_config_value


# ─────────────────────────────────────────────
# Colours for terminal output
# ─────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def pass_label(): return f"{GREEN}PASS{RESET}"
def fail_label(): return f"{RED}FAIL{RESET}"
def skip_label(): return f"{YELLOW}SKIP{RESET}"


# ─────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────

def validate_planner(result: dict, expected: dict) -> tuple[bool, list[str]]:
    """Check planner output against expected fields."""
    failures = []

    if "intent" in expected:
        if result.get("intent") != expected["intent"]:
            failures.append(
                f"intent: expected '{expected['intent']}' got '{result.get('intent')}'"
            )

    if "tools" in expected:
        actual_tools = result.get("tools", [])
        for t in expected["tools"]:
            if t not in actual_tools:
                failures.append(f"tools: expected '{t}' in {actual_tools}")

    if "requires_lsid" in expected:
        if result.get("requires_lsid") != expected["requires_lsid"]:
            failures.append(
                f"requires_lsid: expected {expected['requires_lsid']} got {result.get('requires_lsid')}"
            )

    if "species_mentioned" in expected:
        actual = [s.lower() for s in result.get("species_mentioned", [])]
        for s in expected["species_mentioned"]:
            if s.lower() not in actual:
                failures.append(
                    f"species_mentioned: expected '{s}' in {result.get('species_mentioned')}"
                )
    
    if "query_type" in expected:
        if result.get("query_type") != expected["query_type"]:
            failures.append(
                f"query_type: expected '{expected['query_type']}' got '{result.get('query_type')}'"
            )

    return len(failures) == 0, failures


def validate_extractor(result: dict, expected: dict) -> tuple[bool, list[str]]:
    """Check extractor output against expected fields."""
    failures = []

    for key, exp_val in expected.items():
        actual_val = result.get(key)

        if actual_val is None and exp_val is not None:
            failures.append(f"{key}: expected {exp_val!r} but field is missing/None")
            continue

        # List fields — check all expected values are present (order-insensitive)
        if isinstance(exp_val, list):
            if not isinstance(actual_val, list):
                failures.append(f"{key}: expected list, got {type(actual_val).__name__}")
                continue
            # For species lists, compare lowercase
            if key == "species":
                actual_lower = [s.lower() for s in actual_val]
                for item in exp_val:
                    if item.lower() not in actual_lower:
                        failures.append(f"{key}: expected '{item}' in {actual_val}")
            # For months, check exact set match
            elif key == "months":
                if set(actual_val) != set(exp_val):
                    failures.append(f"{key}: expected {sorted(exp_val)} got {sorted(actual_val)}")
            else:
                for item in exp_val:
                    if item not in actual_val:
                        failures.append(f"{key}: expected '{item}' in {actual_val}")

        # String fields — case-insensitive for species/state
        elif isinstance(exp_val, str):
            if key in ("species", "state"):
                if str(actual_val).lower() != exp_val.lower():
                    failures.append(f"{key}: expected '{exp_val}' got '{actual_val}'")
            else:
                if actual_val != exp_val:
                    failures.append(f"{key}: expected '{exp_val}' got '{actual_val}'")

        # Everything else — exact match
        else:
            if actual_val != exp_val:
                failures.append(f"{key}: expected {exp_val!r} got {actual_val!r}")

    return len(failures) == 0, failures


# ─────────────────────────────────────────────
# Stage runners
# ─────────────────────────────────────────────

async def run_planner_test(case: dict, planner: ALAPlanner, verbose: bool) -> dict:
    query    = case["query"]
    expected = case["expected"]

    try:
        plan = await planner.plan(query)
        result = {
            "intent":            plan.intent,
            "query_type":        plan.query_type,
            "tools":             [t.tool_name for t in plan.tools_planned],
            "species_mentioned": plan.species_mentioned,
            "requires_lsid":     plan.requires_lsid,
}
        passed, failures = validate_planner(result, expected)
        return {
            "id":       case["id"],
            "query":    query,
            "stage":    "planner",
            "passed":   passed,
            "failures": failures,
            "result":   result,
        }
    except Exception as e:
        return {
            "id":       case["id"],
            "query":    query,
            "stage":    "planner",
            "passed":   False,
            "failures": [f"Exception: {e}"],
            "result":   {},
        }


async def run_extractor_test(case: dict, planner: ALAPlanner, extractor: ALAExtractor, verbose: bool) -> dict:
    query    = case["query"]
    intent   = case["intent"]
    expected = case["expected"]

    try:
        # Build a minimal plan to pass to extractor
        plan = await planner.plan(query)
        extraction = await extractor.extract(query, plan)
        result = extraction.model_dump(exclude_none=False)
        passed, failures = validate_extractor(result, expected)
        return {
            "id":       case["id"],
            "query":    query,
            "stage":    "extractor",
            "passed":   passed,
            "failures": failures,
            "result":   result,
        }
    except Exception as e:
        return {
            "id":       case["id"],
            "query":    query,
            "stage":    "extractor",
            "passed":   False,
            "failures": [f"Exception: {e}"],
            "result":   {},
        }
    

# ─────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────

async def main(stage_filter: Optional[str], id_filter: Optional[str], verbose: bool):
    # Load test cases
    test_file = Path(__file__).parent / "test_cases.json"
    with open(test_file) as f:
        all_cases = json.load(f)

    # Apply filters
    cases = all_cases
    if stage_filter:
        cases = [c for c in cases if c["stage"] == stage_filter]
    if id_filter:
        cases = [c for c in cases if c["id"] == id_filter]

    if not cases:
        print(f"{YELLOW}No test cases matched filters.{RESET}")
        return

    # Init pipeline components
    print(f"\n{BOLD}Initialising pipeline components...{RESET}")

    from openai import AsyncOpenAI
    from common.config import get_config_value

    openai_client = AsyncOpenAI(
        api_key=get_config_value("OPENAI_API_KEY"),
        base_url=get_config_value("OPENAI_BASE_URL"),
    )

    registry  = ToolCapabilityRegistry()
    planner   = ALAPlanner(openai_client)
    extractor = ALAExtractor(openai_client)
    print("Ready.\n")

    # Run tests
    results = []
    for case in cases:
        stage = case["stage"]

        if stage == "planner":
            r = await run_planner_test(case, planner, verbose)
        elif stage == "extractor":
            r = await run_extractor_test(case, planner, extractor, verbose)
        else:
            continue

        results.append(r)

        # Print per-test result
        status = pass_label() if r["passed"] else fail_label()
        print(f"[{status}] {r['id']} | {stage:10} | {r['query']}")

        if not r["passed"]:
            for f in r["failures"]:
                print(f"         {RED}✗ {f}{RESET}")

        if verbose and r["passed"]:
            for k, v in r["result"].items():
                if v is not None:
                    print(f"         {k}: {v}")

    # ─── Summary ───────────────────────────────
    total  = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    print(f"\n{'─'*60}")
    print(f"{BOLD}Results: {passed}/{total} passed{RESET}  |  {RED}{failed} failed{RESET}")
    print(f"{'─'*60}")

    # Results by stage
    stages = sorted(set(r["stage"] for r in results))
    for s in stages:
        s_results = [r for r in results if r["stage"] == s]
        s_passed  = sum(1 for r in s_results if r["passed"])
        print(f"  {s:12} {s_passed}/{len(s_results)}")

    # Results by intent
    print()
    intents = sorted(set(c.get("intent", "unknown") for c in cases))
    for intent in intents:
        intent_cases   = [c["id"] for c in cases if c.get("intent") == intent]
        intent_results = [r for r in results if r["id"] in intent_cases]
        i_passed = sum(1 for r in intent_results if r["passed"])
        print(f"  {intent:25} {i_passed}/{len(intent_results)}")

    print(f"{'─'*60}\n")

    # Failed test details
    failed_results = [r for r in results if not r["passed"]]
    if failed_results:
        print(f"{BOLD}{RED}Failed tests:{RESET}")
        for r in failed_results:
            print(f"\n  {r['id']} — {r['query']}")
            for f in r["failures"]:
                print(f"    {RED}✗ {f}{RESET}")
            if verbose:
                print(f"    Actual result: {json.dumps(r['result'], indent=6)}")

    # Save JSON report
    report_path = Path(__file__).parent / "test_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "total":   total,
            "passed":  passed,
            "failed":  failed,
            "results": results,
        }, f, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ALA Pipeline Test Runner")
    parser.add_argument("--stage",   "-s", help="Filter by stage: planner or extractor")
    parser.add_argument("--id",      "-i", help="Run a single test by ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full result for each test")
    args = parser.parse_args()

    asyncio.run(main(args.stage, args.id, args.verbose))