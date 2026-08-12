"""
CLI for a human to log a correction to the agent's output.

Usage:
  python3 record_correction.py \\
    --rule P2_deadline_contained_scope \\
    --from P2-Medium --to P1-High \\
    --request "raw request text or excerpt" \\
    --note "why the human disagreed with the rule"
"""

import argparse

from feedback_log import record_correction


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rule", required=True, help="rule_triggered value from the agent's priority output")
    p.add_argument("--from", dest="from_priority", required=True)
    p.add_argument("--to", dest="to_priority", required=True)
    p.add_argument("--request", default="", help="raw request text or a short excerpt")
    p.add_argument("--from-team", dest="from_team", default=None)
    p.add_argument("--to-team", dest="to_team", default=None)
    p.add_argument("--note", default="")
    args = p.parse_args()

    record = record_correction(
        raw_request=args.request,
        rule_triggered=args.rule,
        original_priority=args.from_priority,
        corrected_priority=args.to_priority,
        original_team=args.from_team,
        corrected_team=args.to_team,
        note=args.note,
    )
    print("Logged correction:")
    print(record)


if __name__ == "__main__":
    main()
