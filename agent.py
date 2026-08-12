"""
AI-native enterprise intake agent.

Five sequential decision stages, each consuming the previous stage's structured output.
Four are LLM reasoning; one is deterministic policy -- deliberately not all five are
"reasoning," and that's the point:
  1. extract   (LLM)          -> understand the raw request, pull out signals/facts
  2. classify  (LLM)          -> domain + work type, reasoned from the extraction
  3. priority  (rule engine)  -> deterministic computation over stage-1 facts, no LLM call
  4. route     (LLM + policy) -> which team owns it, plus hard downstream-review triggers
  5. respond   (LLM)          -> draft first response to the requester, using the full trail

The agent ALWAYS completes all five stages and produces a full result -- there is no
human in the intake loop itself. What some outputs carry is a `requires_downstream_review`
flag: a governance signal telling whatever acts on this result (a person, a ticketing
system) whether it's safe to auto-execute or needs a check first. That's a property of
the output, not a pause in the agent's own reasoning.

Each LLM stage calls Claude once with a forced tool call so the output is structured
JSON, not free text we have to parse. The full reasoning trail (every stage's output) is
kept so the final result is defensible -- you can see *why* the agent decided what it
decided.
"""

import datetime
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv

# Explicit path, not load_dotenv()'s default caller-stack guess -- that guess resolves
# differently depending on how this module gets imported (plain script, Streamlit,
# uvicorn --reload's worker process all behave differently) and silently finds nothing
# in some of them. Anchoring to this file's own directory is unambiguous.
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from routing_table import (
    DOMAINS,
    WORK_TYPES,
    DOMAIN_TO_TEAM,
    ALWAYS_ESCALATE_DOMAINS,
    ALWAYS_ESCALATE_PRIORITIES,
    routing_table_as_prompt_context,
)
from rule_engine import compute_priority, compute_completeness, CLARIFICATION_THRESHOLD
from feedback_log import advisory_note

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


def _call_tool(system: str, user: str, tool: dict, max_retries: int = 2) -> dict:
    """Call Claude with a single forced tool call and return its parsed input.

    Forcing tool_choice makes the model emit JSON matching the schema in the
    overwhelming majority of calls, but it's not a hard guarantee -- occasionally a
    call comes back with a required field missing or merged into another field's text
    (observed once in testing: work_type's value leaked into domain_reasoning as stray
    tag-like text). Required-field validation + one retry catches that instead of
    silently passing broken data downstream.
    """
    required_keys = tool["input_schema"].get("required", [])
    last_error = "unknown error"

    for attempt in range(max_retries + 1):
        resp = _get_client().messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
        )
        tool_input = None
        for block in resp.content:
            if block.type == "tool_use":
                tool_input = block.input
                break

        if tool_input is None:
            last_error = "No tool_use block returned by model."
        else:
            missing = [k for k in required_keys if k not in tool_input]
            if not missing:
                return tool_input
            last_error = f"Tool call missing required field(s) {missing}. Raw output: {tool_input}"

        if attempt < max_retries:
            print(f"[agent] '{tool['name']}' call malformed, retrying: {last_error}")

    raise RuntimeError(f"'{tool['name']}' failed after {max_retries + 1} attempt(s): {last_error}")


# ---------------------------------------------------------------------------
# Step 1: Extract & understand
# ---------------------------------------------------------------------------

EXTRACT_TOOL = {
    "name": "extract_request_info",
    "description": "Record a structured understanding of a raw incoming request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "requester_context": {
                "type": "string",
                "description": "Inferred role/department of the requester based on the text. 'unknown' if not stated or inferable.",
            },
            "core_ask": {
                "type": "string",
                "description": "One normalized sentence: what is actually being requested, stripped of filler.",
            },
            "systems_mentioned": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific tools/systems/processes named in the request. Empty array if none.",
            },
            "urgency_signals": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Explicit phrases or facts indicating urgency (deadlines, production impact, revenue/customer impact). Empty array if none present -- do not infer urgency that isn't stated.",
            },
            "missing_info": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key information a skilled human triager would normally ask a clarifying question about, that is absent here.",
            },
            "completeness_score": {
                "type": "number",
                "description": "0.0-1.0: confidence that there is enough information here to classify and route without further clarification from the requester.",
            },
            "system_down": {
                "type": "boolean",
                "description": "True only if the text explicitly states a production system/process is currently broken or down. False by default -- do not infer from tone.",
            },
            "deadline_urgency": {
                "type": "string",
                "enum": ["none_stated", "within_24h", "within_1_week", "beyond_1_week"],
                "description": "Resolve any relative time expressions (e.g. 'tomorrow', 'by Friday') against today's date, given in the user message. 'none_stated' if no deadline/timeframe is mentioned at all.",
            },
            "scope": {
                "type": "string",
                "enum": ["individual", "team", "multiple_teams", "company_wide", "external_customer", "unknown"],
                "description": "Who is affected by this request, based only on what's stated.",
            },
            "business_impact": {
                "type": "string",
                "enum": ["none_stated", "operational_inefficiency", "revenue_or_compliance", "customer_facing"],
                "description": "The most severe business impact explicitly stated or clearly implied. 'none_stated' if the text gives no basis to judge impact.",
            },
            "claimed_seniority": {
                "type": "string",
                "enum": ["not_stated", "executive_or_leadership", "manager", "individual_contributor"],
                "description": (
                    "What the TEXT ITSELF claims about the requester's seniority (e.g. 'I'm the CFO', "
                    "'on behalf of our VP of Sales') -- this is a self-reported, UNVERIFIED claim, not a "
                    "confirmed identity, and it never affects priority (see rule_engine.py). It only "
                    "affects whether this result gets flagged for downstream review. Only use "
                    "'executive_or_leadership' when a specific senior title/role is explicitly stated, "
                    "never inferred from tone, urgency, or the topic being important-sounding. "
                    "'not_stated' if no seniority claim is made at all."
                ),
            },
        },
        "required": [
            "requester_context",
            "core_ask",
            "systems_mentioned",
            "urgency_signals",
            "missing_info",
            "completeness_score",
            "system_down",
            "deadline_urgency",
            "scope",
            "business_impact",
            "claimed_seniority",
        ],
    },
}

EXTRACT_SYSTEM = """You are the intake-understanding stage of an enterprise technology triage agent.
Your only job is to read a raw, unstructured request and extract a faithful, structured summary of it,
including a handful of discrete facts (system_down, deadline_urgency, scope, business_impact) that a
downstream rule engine -- not you -- will use to set priority, plus claimed_seniority, which never
affects priority and only feeds a downstream-review flag. Because these facts drive automated decisions,
default conservatively when the text doesn't clearly support a stronger value: false / none_stated /
unknown rather than guessing upward. claimed_seniority in particular is an unverified self-report from
the text -- extract what is claimed, don't validate or trust it, and never infer executive status just
because a request sounds important. Do not classify, prioritize, or route yourself -- later stages do
that. Do not invent facts that aren't stated or clearly implied. If something is unclear or absent, say
so in missing_info rather than guessing."""


def step1_extract(raw_request: str) -> dict:
    today = datetime.date.today().isoformat()
    user = f"Today's date: {today}\n\nRaw incoming request:\n\n\"\"\"\n{raw_request}\n\"\"\""
    extraction = _call_tool(EXTRACT_SYSTEM, user, EXTRACT_TOOL)

    # Completeness guardrail: don't just take the model's holistic self-rating on
    # faith. Cross-check it against a deterministic count of the missing_info items
    # it itself listed, and keep whichever is lower -- see rule_engine.compute_completeness.
    # completeness_score is overwritten with that effective value; the two inputs are
    # kept alongside it so the trail shows why.
    extraction.update(compute_completeness(extraction))
    return extraction


# ---------------------------------------------------------------------------
# Step 2: Classify -- domain, work type, priority
# ---------------------------------------------------------------------------

CLASSIFY_TOOL = {
    "name": "classify_request",
    "description": "Classify a request's business domain and work type. Priority is NOT decided here -- it's computed by a deterministic rule engine from stage 1's extracted facts, not by model judgment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "enum": DOMAINS},
            "work_type": {"type": "string", "enum": WORK_TYPES},
            "classification_confidence": {
                "type": "number",
                "description": "0.0-1.0 confidence in this domain/work_type call.",
            },
            "classification_reasoning": {
                "type": "string",
                "description": "One short paragraph justifying both the domain and work_type choice together.",
            },
        },
        # NOTE: domain/work_type reasoning is deliberately ONE combined field, not two
        # separate ones next to their enums. Two short-enum-then-long-text pairs back to
        # back (domain, domain_reasoning, work_type, work_type_reasoning) reproducibly
        # triggered malformed tool_use output from the model on this schema+prompt (an
        # observed ~50% failure rate where work_type's value leaked into domain_reasoning
        # as stray tag-like text, dropping the work_type key entirely). Collapsing to one
        # reasoning field removed the repeating pattern and eliminated the failures in
        # testing (0/10). See _call_tool's required-field validation/retry for the
        # remaining defense-in-depth.
        "required": [
            "domain",
            "work_type",
            "classification_confidence",
            "classification_reasoning",
        ],
    },
}

CLASSIFY_SYSTEM = f"""You are the classification stage of an enterprise technology triage agent.
You receive a structured extraction of a raw request (not the raw text itself) and must assign:
- domain: which part of the business this request belongs to
- work_type: what kind of work this is

Valid domains: {DOMAINS}
Valid work types: {WORK_TYPES}

Priority is deliberately NOT your job -- language understanding (what is this and who does it concern)
is something you're trusted with; the business-priority call is handled by a separate deterministic
rule engine so it stays auditable. Just classify domain and work type as accurately as the extraction
supports, and reflect genuine ambiguity in classification_confidence rather than picking confidently."""


def step2_classify(extraction: dict) -> dict:
    user = f"Structured extraction from stage 1:\n\n{json.dumps(extraction, indent=2)}"
    return _call_tool(CLASSIFY_SYSTEM, user, CLASSIFY_TOOL)


def step2b_priority(extraction: dict) -> dict:
    """No LLM call -- a deterministic rule engine decides priority from stage 1's facts."""
    return compute_priority(extraction)


# ---------------------------------------------------------------------------
# Step 3: Route
# ---------------------------------------------------------------------------

ROUTE_TOOL = {
    "name": "route_request",
    "description": (
        "Recommend which team should own this request, using the provided routing table. "
        "This stage always completes and returns a full recommendation -- "
        "requires_downstream_review is a governance flag on that recommendation, not a "
        "request to pause and wait for a human before answering."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "recommended_team": {"type": "string"},
            "routing_reasoning": {"type": "string"},
            "requires_downstream_review": {
                "type": "boolean",
                "description": "True if this recommendation is low-confidence, high-stakes, or cross-domain and should be checked by a person before anyone acts on it.",
            },
            "escalation_reason": {
                "type": "string",
                "description": "Why downstream review is needed. Empty string if requires_downstream_review is false.",
            },
        },
        "required": ["recommended_team", "routing_reasoning", "requires_downstream_review", "escalation_reason"],
    },
}

ROUTE_SYSTEM = f"""You are the routing stage of an enterprise technology triage agent.
You receive stage-1 extraction and stage-2 classification and must recommend an owning team.

{routing_table_as_prompt_context()}

Use the domain from stage 2 to pick the team, unless the extraction/classification reveals the
request genuinely spans multiple domains or doesn't fit the table -- in that case route to
"Enterprise Technology Intake Lead (cross-domain escalation)" and explain why in routing_reasoning.
Set requires_downstream_review=true whenever classification_confidence or completeness_score was low,
priority is P0, domain is Security, or the routing itself is a judgment call. You still always produce
a complete recommendation either way -- this flag tells whoever acts on your output whether to check
with a person first, it does not mean you're deferring the decision itself."""


def step3_route(extraction: dict, classification: dict, priority: dict) -> dict:
    payload = {"extraction": extraction, "classification": classification, "priority": priority}
    user = f"Stage 1 + 2 + priority-rule output:\n\n{json.dumps(payload, indent=2)}"
    result = _call_tool(ROUTE_SYSTEM, user, ROUTE_TOOL)

    # Deterministic safety net on top of the model's own judgment: some conditions
    # always force the downstream-review flag regardless of what the model decided, so
    # a confidently-wrong model call can't silently skip escalation. The stage above
    # still always runs and returns a complete recommendation -- this only marks that
    # recommendation "check before acting," it never blocks the agent from finishing.
    domain = classification.get("domain")
    priority_level = priority.get("priority")
    completeness_score = extraction.get("completeness_score", 1.0)
    claimed_seniority = extraction.get("claimed_seniority", "not_stated")
    forced_reasons = []
    if domain in ALWAYS_ESCALATE_DOMAINS:
        forced_reasons.append(f"Policy: {domain} domain always requires downstream review.")
    if priority_level in ALWAYS_ESCALATE_PRIORITIES:
        forced_reasons.append(f"Policy: {priority_level} priority always requires downstream review.")
    if claimed_seniority == "executive_or_leadership":
        forced_reasons.append(
            "Policy: requester is self-reported as executive/leadership in the request "
            "text. This claim is unverified and has NOT affected priority -- it only "
            "means a person should confirm the requester's actual identity before this "
            "is acted on. An unverified title claim never grants automated "
            "fast-tracking on its own."
        )
    if completeness_score < CLARIFICATION_THRESHOLD:
        forced_reasons.append(
            f"Policy: completeness_score {completeness_score} is below the "
            f"{CLARIFICATION_THRESHOLD} clarification threshold -- routing is provisional "
            "until the requester provides missing_info."
        )

    # Feedback loop: if humans have previously corrected this exact rule before, say so.
    note = advisory_note(priority.get("rule_triggered", ""))
    if note:
        forced_reasons.append(note)

    if forced_reasons:
        result["requires_downstream_review"] = True
        existing = result.get("escalation_reason") or ""
        result["escalation_reason"] = " ".join([existing] + forced_reasons).strip()

    result["needs_clarification"] = completeness_score < CLARIFICATION_THRESHOLD
    return result


# ---------------------------------------------------------------------------
# Step 4: Draft first response
# ---------------------------------------------------------------------------

RESPOND_TOOL = {
    "name": "draft_response",
    "description": "Draft the first response sent back to the person who submitted the request.",
    "input_schema": {
        "type": "object",
        "properties": {
            "draft_response": {
                "type": "string",
                "description": "The actual message to send the requester. Match tone to priority -- P0/P1 should feel urgent and specific, P2/P3 can be a standard acknowledgment. If needs_clarification is true, this should primarily ask the missing_info questions rather than confirm a routing/priority that isn't reliable yet.",
            },
        },
        "required": ["draft_response"],
    },
}

RESPOND_SYSTEM = """You are the response-drafting stage of an enterprise technology triage agent.
Write the first reply the requester will see. It should be short and specific (reference their actual
ask, not generic boilerplate).

If needs_clarification is true: completeness_score was too low to route this confidently. Lead with
the specific questions from missing_info -- don't state a team/priority as settled, since it isn't yet.

Otherwise: state what team is picking it up and roughly what happens next. If requires_downstream_review
is true (but needs_clarification is false), say a team member will confirm details before it's actioned --
don't state the routing/priority as final fact when it's still pending a downstream check."""


def step4_respond(raw_request: str, extraction: dict, classification: dict, priority: dict, routing: dict) -> dict:
    payload = {
        "original_request": raw_request,
        "extraction": extraction,
        "classification": classification,
        "priority": priority,
        "routing": routing,
    }
    user = f"Full reasoning trail so far:\n\n{json.dumps(payload, indent=2)}"
    return _call_tool(RESPOND_SYSTEM, user, RESPOND_TOOL)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

@dataclass
class IntakeResult:
    raw_request: str
    extraction: dict = field(default_factory=dict)
    classification: dict = field(default_factory=dict)
    priority: dict = field(default_factory=dict)
    routing: dict = field(default_factory=dict)
    response: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        c, p, r = self.classification, self.priority, self.routing
        review_line = f"Downstream review required? : {r.get('requires_downstream_review')}"
        if r.get("requires_downstream_review"):
            review_line += f" ({r.get('escalation_reason')})"
        lines = [
            f"Classification : {c.get('domain')} / {c.get('work_type')}",
            f"Priority       : {p.get('priority')}  [{p.get('rule_triggered')}]",
            f"  reason       : {p.get('priority_reasoning')}",
            f"Routed to      : {r.get('recommended_team')}",
            review_line,
            "",
            "Draft first response:",
            self.response.get("draft_response", ""),
        ]
        return "\n".join(lines)


def run_intake(raw_request: str) -> IntakeResult:
    """Run all five decision stages. Each stage's output feeds the next. Always
    completes and returns a full result -- there's no human in this loop; some
    results just carry a requires_downstream_review flag for whatever acts on them next.

    extract (LLM) -> classify domain/work_type (LLM) -> priority (rule engine, no LLM)
    -> route (LLM + hard policy overrides) -> draft response (LLM)
    """
    result = IntakeResult(raw_request=raw_request)

    result.extraction = step1_extract(raw_request)
    result.classification = step2_classify(result.extraction)
    result.priority = step2b_priority(result.extraction)
    result.routing = step3_route(result.extraction, result.classification, result.priority)
    result.response = step4_respond(
        raw_request, result.extraction, result.classification, result.priority, result.routing
    )

    return result
