"""
Run the labeled eval set end-to-end and report agreement rates.

Usage: python3 eval.py [--json report.json]
"""

import json
import sys

from agent import run_intake
from eval_cases import EVAL_CASES
from rule_engine import compute_priority
from routing_table import ALWAYS_ESCALATE_DOMAINS, ALWAYS_ESCALATE_PRIORITIES


def expected_priority(case: dict) -> str:
    return compute_priority(case["expected_facts"])["priority"]


def expected_escalation(case: dict, exp_priority: str) -> bool:
    seniority = case["expected_facts"].get("claimed_seniority", "not_stated")
    return (
        case["expected_domain"] in ALWAYS_ESCALATE_DOMAINS
        or exp_priority in ALWAYS_ESCALATE_PRIORITIES
        or seniority == "executive_or_leadership"
    )


def run_eval() -> list[dict]:
    rows = []
    for i, case in enumerate(EVAL_CASES):
        print(f"[{i + 1}/{len(EVAL_CASES)}] running '{case['id']}'...", file=sys.stderr)
        result = run_intake(case["text"])

        exp_prio = expected_priority(case)
        exp_esc = expected_escalation(case, exp_prio)

        actual_domain = result.classification.get("domain")
        actual_work_type = result.classification.get("work_type")
        actual_priority = result.priority.get("priority")
        actual_esc = result.routing.get("requires_downstream_review")

        domain_ok = (actual_domain == case["expected_domain"]) or case.get("lenient_domain", False)
        work_type_ok = (actual_work_type == case["expected_work_type"]) or case.get("lenient_work_type", False)
        priority_ok = actual_priority == exp_prio
        esc_ok = actual_esc == exp_esc

        rows.append({
            "id": case["id"],
            "domain": {"expected": case["expected_domain"], "actual": actual_domain, "ok": domain_ok, "lenient": case.get("lenient_domain", False)},
            "work_type": {"expected": case["expected_work_type"], "actual": actual_work_type, "ok": work_type_ok, "lenient": case.get("lenient_work_type", False)},
            "priority": {"expected": exp_prio, "actual": actual_priority, "ok": priority_ok},
            "requires_downstream_review": {"expected": exp_esc, "actual": actual_esc, "ok": esc_ok},
        })
    return rows


def print_report(rows: list[dict]) -> None:
    n = len(rows)
    domain_hits = sum(r["domain"]["ok"] for r in rows)
    work_type_hits = sum(r["work_type"]["ok"] for r in rows)
    priority_hits = sum(r["priority"]["ok"] for r in rows)
    esc_hits = sum(r["requires_downstream_review"]["ok"] for r in rows)

    print("\n" + "=" * 78)
    print(f"EVAL REPORT ({n} cases)")
    print("=" * 78)
    print(f"Domain match              : {domain_hits}/{n}  ({100 * domain_hits / n:.0f}%)")
    print(f"Work type match           : {work_type_hits}/{n}  ({100 * work_type_hits / n:.0f}%)")
    print(f"Priority match            : {priority_hits}/{n}  ({100 * priority_hits / n:.0f}%)")
    print(f"requires_downstream_review: {esc_hits}/{n}  ({100 * esc_hits / n:.0f}%)")

    # requires_downstream_review's ground truth here only encodes the hard policy
    # triggers (Security domain, P0, seniority claims) -- it does NOT model
    # completeness_score or the route stage's own judgment call, so raw agreement
    # understates the system. What matters more is the *direction* of disagreement:
    # false positives (system flags for review when the naive label didn't expect it)
    # are the safe failure mode; false negatives (system skips review when it should
    # have flagged) are the dangerous one. Report both so the number isn't misread as
    # "44% broken."
    esc_misses = [r for r in rows if not r["requires_downstream_review"]["ok"]]
    false_positives = sum(1 for r in esc_misses if r["requires_downstream_review"]["expected"] is False)
    false_negatives = sum(1 for r in esc_misses if r["requires_downstream_review"]["expected"] is True)
    print(f"  -> of {len(esc_misses)} misses: {false_positives} over-cautious (safe direction), "
          f"{false_negatives} under-cautious (dangerous direction)")
    print("-" * 78)

    for r in rows:
        flags = []
        if not r["domain"]["ok"]:
            flags.append(f"DOMAIN: expected {r['domain']['expected']!r}, got {r['domain']['actual']!r}")
        if not r["work_type"]["ok"]:
            flags.append(f"WORK_TYPE: expected {r['work_type']['expected']!r}, got {r['work_type']['actual']!r}")
        if not r["priority"]["ok"]:
            flags.append(f"PRIORITY: expected {r['priority']['expected']!r}, got {r['priority']['actual']!r}")
        if not r["requires_downstream_review"]["ok"]:
            flags.append(
                f"DOWNSTREAM_REVIEW: expected {r['requires_downstream_review']['expected']!r}, "
                f"got {r['requires_downstream_review']['actual']!r}"
            )

        status = "PASS" if not flags else "MISS"
        print(f"[{status}] {r['id']}")
        for f in flags:
            print(f"        {f}")
    print("=" * 78)


if __name__ == "__main__":
    rows = run_eval()
    print_report(rows)

    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        out_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "eval_report.json"
        with open(out_path, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"\nWrote {out_path}", file=sys.stderr)
