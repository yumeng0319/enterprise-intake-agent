"""
Toy human-correction feedback loop.

The idea: when a human reviewer overrides what the agent decided, that correction gets
logged. If a specific rule keeps getting overridden, the routing stage should know that
and say so -- instead of the rule engine silently making the same debatable call forever.

This is intentionally a toy, not a calibration system: it counts how many times a rule
has been *corrected* (logged here), not a true override *rate*, because we don't log
every time a rule fires uncorrected -- only the corrections. A real V2 would log every
firing and compute an actual rate; this is the smallest version that's still real code
with a real effect on behavior, not just a described idea.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

CORRECTIONS_FILE = Path(__file__).parent / "corrections.jsonl"

# A rule needs at least this many logged corrections before the routing stage
# surfaces an advisory note about it -- one disagreement is noise, not a pattern.
ADVISORY_THRESHOLD = 2


def record_correction(
    raw_request: str,
    rule_triggered: str,
    original_priority: str,
    corrected_priority: str,
    original_team: str | None = None,
    corrected_team: str | None = None,
    note: str = "",
) -> dict:
    """Log a human's correction of the agent's output. Append-only."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_request_excerpt": raw_request[:200],
        "rule_triggered": rule_triggered,
        "original_priority": original_priority,
        "corrected_priority": corrected_priority,
        "original_team": original_team,
        "corrected_team": corrected_team,
        "note": note,
    }
    with open(CORRECTIONS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def _read_all() -> list[dict]:
    if not CORRECTIONS_FILE.exists():
        return []
    with open(CORRECTIONS_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]


def get_correction_count(rule_triggered: str) -> int:
    return sum(1 for r in _read_all() if r["rule_triggered"] == rule_triggered)


def get_recent_corrections(rule_triggered: str, limit: int = 3) -> list[dict]:
    matches = [r for r in _read_all() if r["rule_triggered"] == rule_triggered]
    return matches[-limit:]


def advisory_note(rule_triggered: str) -> str | None:
    """Return an advisory string if this rule has a pattern of being overridden, else None."""
    count = get_correction_count(rule_triggered)
    if count < ADVISORY_THRESHOLD:
        return None
    examples = get_recent_corrections(rule_triggered, limit=2)
    example_str = "; ".join(f"{e['original_priority']}->{e['corrected_priority']} ({e['note']})" for e in examples)
    return (
        f"Advisory: the rule '{rule_triggered}' has been manually corrected {count} "
        f"time(s) before. Recent corrections: {example_str}. Consider double-checking "
        f"this one rather than trusting the rule as-is."
    )
