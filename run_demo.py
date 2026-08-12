"""
CLI demo runner.

Usage:
  python run_demo.py                       # interactive: paste/type a request
  python run_demo.py "raw request text"    # single request from argv
  python run_demo.py --sample clear_dashboard
  python run_demo.py --all-samples         # run every sample request, print each
  python run_demo.py --json "raw request"  # print full structured trail as JSON
"""

import json
import sys

from agent import run_intake
from test_requests import SAMPLE_REQUESTS


def print_result(raw_request: str, as_json: bool) -> None:
    result = run_intake(raw_request)
    print("=" * 80)
    print("REQUEST:", raw_request)
    print("-" * 80)
    if as_json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.summary())
    print("=" * 80)
    print()


def main() -> None:
    args = sys.argv[1:]
    as_json = "--json" in args
    if as_json:
        args.remove("--json")

    if "--all-samples" in args:
        for name, text in SAMPLE_REQUESTS.items():
            print(f"[sample: {name}]")
            print_result(text, as_json)
        return

    if args and args[0] == "--sample":
        if len(args) < 2 or args[1] not in SAMPLE_REQUESTS:
            print(f"Available samples: {list(SAMPLE_REQUESTS.keys())}")
            sys.exit(1)
        print_result(SAMPLE_REQUESTS[args[1]], as_json)
        return

    if args:
        print_result(" ".join(args), as_json)
        return

    print("Paste the raw request, then press Enter and Ctrl-D (or Ctrl-Z on Windows):")
    raw = sys.stdin.read().strip()
    if not raw:
        print("No input received.")
        sys.exit(1)
    print_result(raw, as_json)


if __name__ == "__main__":
    main()
