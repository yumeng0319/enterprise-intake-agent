"""
Deterministic priority rule engine.

Design principle: the LLM is trusted to understand natural language and extract facts
(step 1), but NOT trusted to make the business-priority call directly -- that's a policy
decision, and policy should be auditable code, not a model's judgment call. This is what
lets the agent answer "why P1?" with a rule, not "the model thought so."

Each rule is evaluated in order; the first match wins. Thresholds here are working
assumptions -- call this out explicitly in the design doc as something to validate with
real triage data, not something the agent invented on its own.

A second principle governs claimed_seniority (e.g. "I'm the CFO"): priority measures
business impact, not organizational power, so claimed seniority NEVER changes the
number this module returns -- an identical request gets an identical priority whether
the requester claims to be a VP or says nothing about who they are. What claimed
seniority *does* do lives entirely in agent.py: it's an unverified identity claim, so
it always flags the result for downstream review, independent of priority. Authority
you can't verify buys a human's attention, never a shortcut.
"""

CLARIFICATION_THRESHOLD = 0.5  # completeness_score below this -> ask for info instead of routing confidently


def _base_priority(system_down: bool, deadline_urgency: str, scope: str, business_impact: str) -> dict:
    wide_scope = scope in ("multiple_teams", "company_wide", "external_customer")
    critical_impact = business_impact in ("revenue_or_compliance", "customer_facing")

    if system_down and (deadline_urgency == "within_24h" or critical_impact):
        return {
            "priority": "P0-Critical",
            "priority_reasoning": (
                "Rule: system_down=true AND (deadline within 24h OR revenue/compliance/"
                "customer-facing impact) -> P0. A production system is broken with "
                "immediate business impact."
            ),
            "rule_triggered": "P0_system_down_with_immediate_impact",
        }

    if system_down or critical_impact:
        return {
            "priority": "P1-High",
            "priority_reasoning": (
                "Rule: system_down=true OR business_impact in {revenue_or_compliance, "
                "customer_facing} -> P1. Real impact stated, but not the combined "
                "immediate-outage-plus-deadline case that defines P0."
            ),
            "rule_triggered": "P1_impact_stated",
        }

    if deadline_urgency == "within_24h" and wide_scope:
        return {
            "priority": "P1-High",
            "priority_reasoning": (
                "Rule: deadline_urgency=within_24h AND scope in {multiple_teams, "
                "company_wide, external_customer} -> P1. Hard near-term deadline "
                "affecting more than one team."
            ),
            "rule_triggered": "P1_urgent_deadline_wide_scope",
        }

    if deadline_urgency in ("within_24h", "within_1_week"):
        return {
            "priority": "P2-Medium",
            "priority_reasoning": (
                f"Rule: deadline_urgency={deadline_urgency} with no stated outage or "
                "critical business impact -> P2. Real deadline, contained scope."
            ),
            "rule_triggered": "P2_deadline_contained_scope",
        }

    return {
        "priority": "P3-Low",
        "priority_reasoning": (
            "Rule: no stated deadline, outage, or critical business impact -> P3. "
            "Default priority absent explicit urgency signals -- the agent does not "
            "invent urgency that wasn't stated."
        ),
        "rule_triggered": "P3_default_no_urgency_signals",
    }


def compute_priority(extraction: dict) -> dict:
    """Pure function: structured facts in, priority + auditable reasons out. No LLM call.

    Deliberately does NOT look at claimed_seniority. Priority measures business impact
    (outage status, deadline, scope, business_impact) -- who is asking is a separate,
    unverified signal handled entirely as a downstream-review trigger in agent.py, not
    something that can move the priority number.
    """
    system_down = bool(extraction.get("system_down"))
    deadline_urgency = extraction.get("deadline_urgency", "none_stated")
    scope = extraction.get("scope", "unknown")
    business_impact = extraction.get("business_impact", "none_stated")

    return _base_priority(system_down, deadline_urgency, scope, business_impact)


# Each item in missing_info costs this much completeness. Not a holistic self-rating --
# a direct count of concrete gaps the LLM itself named, which a human can read and
# recount in the trail. Deliberately does NOT penalize none_stated/unknown fields
# (deadline_urgency, business_impact, etc.) on their own, because a field being
# genuinely not-applicable ("no deadline, this is a nice-to-have") is not the same as
# information being missing -- conflating the two would flag every low-stakes request
# as incomplete just for being low-stakes.
MISSING_INFO_PENALTY = 0.2


def compute_completeness(extraction: dict) -> dict:
    """Second, independent completeness signal -- deterministic, computed from the
    LLM's own missing_info list, not another holistic LLM self-rating.

    Two different judgments (the model's holistic 0-1 self-rating from stage 1, and
    this formula) triangulate each other. The caller takes whichever is LOWER: same
    "err toward caution, never toward false confidence" principle used everywhere else
    in this pipeline. A completeness_score claim the model can't back up with a matching
    missing_info list gets overridden by the count, not taken on faith.
    """
    missing_info = extraction.get("missing_info", [])
    computed = max(0.0, 1.0 - MISSING_INFO_PENALTY * len(missing_info))
    llm_reported = extraction.get("completeness_score", 1.0)
    effective = min(computed, llm_reported)

    return {
        "completeness_score": effective,
        "completeness_score_llm_reported": llm_reported,
        "completeness_score_computed": computed,
        "completeness_reasoning": (
            f"effective={effective:.2f} = min(llm_reported={llm_reported:.2f}, "
            f"computed={computed:.2f} from {len(missing_info)} missing_info item(s) "
            f"x {MISSING_INFO_PENALTY} penalty each)."
        ),
    }
