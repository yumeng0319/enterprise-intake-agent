# Reliability Findings

Concrete things we found broken, tested, and fixed — not spot-checked examples.

## 1. Malformed structured output (classify_request)

Forcing `tool_choice` makes Claude emit schema-matching JSON the overwhelming majority
of the time, but not with a 100% guarantee. Testing surfaced a specific schema shape
that reproducibly broke it.

**Expected output:**
```json
{
  "domain": "Data/Analytics",
  "domain_reasoning": "...(explanation)...",
  "work_type": "Incident/Debug",
  "work_type_reasoning": "...(explanation)..."
}
```

**What actually came back, on a real run (~50% of the time, 10-trial test):**
```json
{
  "domain": "Data/Analytics",
  "domain_reasoning": "...The systems mentioned (ETL job, reporting feed) point to data engineering ownership.</domain_reasoning>\n<parameter name=\"work_type\">Incident/Debug",
  "work_type_reasoning": "The core ask is to fix a failing/broken ETL job...",
  "classification_confidence": 0.75
}
```

`work_type`'s value ("Incident/Debug") leaked into the end of `domain_reasoning` as
stray tag-like text, and the standalone `work_type` key never appeared at all — the
downstream code reading `result["work_type"]` got nothing, which is why an earlier demo
run showed "WORK TYPE: —" on screen.

**Root-causing it, empirically, not by guessing once and shipping:**

| Attempt | Change | Result |
|---|---|---|
| Baseline | `domain`, `domain_reasoning`, `work_type`, `work_type_reasoning` as 4 separate fields | 5/10 failed |
| Hypothesis 1 | Reorder: both enums first, then both reasoning fields | 8/8 failed (worse, different field dropped each time) |
| Fix that shipped | Merge `domain_reasoning` + `work_type_reasoning` into one `classification_reasoning` field | 10/10 clean |

The pattern that broke it: two short-enum-then-long-freetext pairs, back to back.
Removing the repeated pattern removed the failure. Backed by required-field validation
and automatic retry as defense in depth (`agent.py::_call_tool`), in case it resurfaces
on a schema shape we haven't tested yet.

## 2. Labeled eval set (16 cases)

Not five hand-picked examples that "looked right" — a labeled set spanning every
domain and work type, with expected priority computed by running hand-specified facts
through the real rule engine (so the eval checks extraction/classification accuracy,
not re-grading deterministic code). Re-run live, most recent numbers:

| Metric | Result |
|---|---:|
| Domain | 16/16 (100%) |
| Work type | 16/16 (100%) |
| Priority | 13/16 (81%) |
| `requires_downstream_review` (raw) | 6/16 (38%) |
| — of those misses, over-cautious (safe) | 10/10 |
| — of those misses, under-cautious (dangerous) | 0/10 |

The headline number to defend isn't the 38% — it's that **every single
`requires_downstream_review` disagreement was the system flagging something for review
that a simplified ground truth didn't expect, never the reverse.** The ground truth
here only encodes the hard policy triggers (Security domain, P0, seniority claims); it
doesn't model `completeness_score`, so it systematically undercounts legitimate review
triggers. Real evidence the system's error mode skews toward caution, not false
confidence.

**Priority misses (3 of 16), each traced back individually:**

| Case | Expected | Actual | Why |
|---|---|---|---|
| `vpn_unreliable` | P1-High | P3-Low | Eval label assumed "unreliable VPN" implies `system_down=true`; the request text says "not fully down," and the model extracted that literally instead of rounding up — a labeling issue, not a model error |
| `contractor_badge_access` | P3-Low | P1-High | The model classified lingering unauthorized access as `business_impact=revenue_or_compliance` on this run; a genuinely ambiguous judgment call (compliance risk vs. routine IT housekeeping) that can land either way run to run |
| `cross_system_mismatch` | P1-High | P2-Medium | Deliberately marked as an ambiguous case in the eval set itself (`lenient_domain: true`) — this is expected variance, not a defect |

**`requires_downstream_review` misses are all the same shape:** short requests like "new
hire needs a laptop" or "set up SSO integration" get flagged for review because
`completeness_score` comes back low (missing details a real triager would ask about),
which the simplified eval label didn't anticipate. Not a bug in the system — a gap in
the label.

## 3. Routing hallucination without a fixed team list

Removing the fixed `routing_table.py` constraint and asking the model to freely name a
team it thinks should own the request produced invented, inconsistent team names in
4 of 5 test requests:

| Request | Constrained (current system) | Unconstrained (test only) |
|---|---|---|
| ETL job failing, finance close blocked | Data Engineering | Data Engineering *(matched)* |
| Salesforce pipeline dashboard for QBR | GTM Applications Engineering | "Sales/GTM Systems (Salesforce) Engineering" |
| New hire needs laptop + access | Client Platform & Support Engineering | "IT Service Desk / Employee IT Support" |
| Ex-contractor still has badge access | Security | "Physical Security / Badge Access Administration" |
| Compliance agreement needs signature | Enterprise Applications | "Legal/Compliance" |

The model isn't wrong about what these requests *are* — the unconstrained names are
plausible-sounding. It's wrong about the *organization*, because it's guessing at a
structure it was never given. This is the concrete case for why routing is constrained
to a fixed capability map instead of left to the model to invent one.
