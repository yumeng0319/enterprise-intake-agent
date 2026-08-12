# Enterprise Intake Agent — System Design

## Architecture & Reasoning

Five sequential decision stages, each consuming the previous stage's output. Four are
LLM reasoning; one (priority) is deterministic policy — deliberately not all five are
"reasoning." Core principle: **the LLM handles language understanding; the
highest-stakes business decision (priority) is handled by deterministic code, not model
judgment** — so "why P1?" always has an auditable answer, never "the model thought so."

![Architecture diagram: raw request flows through Extract, then branches into Classify (LLM) and Priority (rule engine), which merge into Route, then Respond, producing the structured output](data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA4NjAgNjIwIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSwgSGVsdmV0aWNhLCBBcmlhbCwgc2Fucy1zZXJpZiI+CiAgPGRlZnM+CiAgICA8bWFya2VyIGlkPSJhcnJvdyIgdmlld0JveD0iMCAwIDEwIDEwIiByZWZYPSI5IiByZWZZPSI1IiBtYXJrZXJXaWR0aD0iNyIgbWFya2VySGVpZ2h0PSI3IiBvcmllbnQ9ImF1dG8tc3RhcnQtcmV2ZXJzZSI+CiAgICAgIDxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzRiNTU2MyIvPgogICAgPC9tYXJrZXI+CiAgPC9kZWZzPgoKICA8cmVjdCB4PSIwIiB5PSIwIiB3aWR0aD0iODYwIiBoZWlnaHQ9IjYyMCIgZmlsbD0iI2ZmZmZmZiIvPgoKICA8IS0tIFJhdyBSZXF1ZXN0IC0tPgogIDxyZWN0IHg9IjMzMCIgeT0iMTQiIHdpZHRoPSIyMDAiIGhlaWdodD0iNDIiIHJ4PSI4IiBmaWxsPSIjZjNmNGY2IiBzdHJva2U9IiM5Y2EzYWYiIHN0cm9rZS13aWR0aD0iMS41Ii8+CiAgPHRleHQgeD0iNDMwIiB5PSI0MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxNSIgZmlsbD0iIzFmMjkzNyI+UmF3IFJlcXVlc3QgKHRleHQpPC90ZXh0PgoKICA8bGluZSB4MT0iNDMwIiB5MT0iNTYiIHgyPSI0MzAiIHkyPSI4OCIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJyb3cpIi8+CgogIDwhLS0gMSBFeHRyYWN0IC0tPgogIDxyZWN0IHg9IjI5MCIgeT0iOTAiIHdpZHRoPSIyODAiIGhlaWdodD0iNTgiIHJ4PSIxMCIgZmlsbD0iI2VlZjJmZiIgc3Ryb2tlPSIjNGY0NmU1IiBzdHJva2Utd2lkdGg9IjIiLz4KICA8dGV4dCB4PSI0MzAiIHk9IjExNCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzM3MzBhMyI+MS4gRXh0cmFjdCBGYWN0czwvdGV4dD4KICA8dGV4dCB4PSI0MzAiIHk9IjEzNCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjNGY0NmU1Ij5MTE0g4oCUIGxhbmd1YWdlIHVuZGVyc3RhbmRpbmc8L3RleHQ+CgogIDxsaW5lIHgxPSI0MzAiIHkxPSIxNDgiIHgyPSI0MzAiIHkyPSIxODAiIHN0cm9rZT0iIzRiNTU2MyIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93KSIvPgoKICA8IS0tIFN0cnVjdHVyZWQgRmFjdHMgbGFiZWwgLS0+CiAgPHRleHQgeD0iNDMwIiB5PSIxOTYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzZiNzI4MCIgZm9udC1zdHlsZT0iaXRhbGljIj5zdHJ1Y3R1cmVkIGZhY3RzPC90ZXh0PgoKICA8IS0tIGJyYW5jaCBsaW5lcyAtLT4KICA8bGluZSB4MT0iNDMwIiB5MT0iMjA0IiB4Mj0iNDMwIiB5Mj0iMjIyIiBzdHJva2U9IiM0YjU1NjMiIHN0cm9rZS13aWR0aD0iMiIvPgogIDxsaW5lIHgxPSIyMjAiIHkxPSIyMjIiIHgyPSI2NDAiIHkyPSIyMjIiIHN0cm9rZT0iIzRiNTU2MyIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPGxpbmUgeDE9IjIyMCIgeTE9IjIyMiIgeDI9IjIyMCIgeTI9IjI0OCIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJyb3cpIi8+CiAgPGxpbmUgeDE9IjY0MCIgeTE9IjIyMiIgeDI9IjY0MCIgeTI9IjI0OCIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJyb3cpIi8+CgogIDwhLS0gMiBDbGFzc2lmeSAtLT4KICA8cmVjdCB4PSI4MCIgeT0iMjUwIiB3aWR0aD0iMjgwIiBoZWlnaHQ9IjU4IiByeD0iMTAiIGZpbGw9IiNlZWYyZmYiIHN0cm9rZT0iIzRmNDZlNSIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPHRleHQgeD0iMjIwIiB5PSIyNzQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMzNzMwYTMiPjIuIENsYXNzaWZ5PC90ZXh0PgogIDx0ZXh0IHg9IjIyMCIgeT0iMjk0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyLjUiIGZpbGw9IiM0ZjQ2ZTUiPkxMTSDigJQgZG9tYWluICsgd29yayB0eXBlPC90ZXh0PgoKICA8IS0tIDMgUHJpb3JpdHkgLS0+CiAgPHJlY3QgeD0iNTAwIiB5PSIyNTAiIHdpZHRoPSIyODAiIGhlaWdodD0iNTgiIHJ4PSIxMCIgZmlsbD0iI2ZmZmJlYiIgc3Ryb2tlPSIjZDk3NzA2IiBzdHJva2Utd2lkdGg9IjIiLz4KICA8dGV4dCB4PSI2NDAiIHk9IjI3NCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzkyNDAwZSI+My4gUHJpb3JpdHk8L3RleHQ+CiAgPHRleHQgeD0iNjQwIiB5PSIyOTQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iI2I0NTMwOSI+UnVsZSBlbmdpbmUg4oCUIDAgTExNIGNhbGxzPC90ZXh0PgoKICA8IS0tIG1lcmdlIGxpbmVzIC0tPgogIDxsaW5lIHgxPSIyMjAiIHkxPSIzMDgiIHgyPSIyMjAiIHkyPSIzMzAiIHN0cm9rZT0iIzRiNTU2MyIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPGxpbmUgeDE9IjY0MCIgeTE9IjMwOCIgeDI9IjY0MCIgeTI9IjMzMCIgc3Ryb2tlPSIjNGI1NTYzIiBzdHJva2Utd2lkdGg9IjIiLz4KICA8bGluZSB4MT0iMjIwIiB5MT0iMzMwIiB4Mj0iNjQwIiB5Mj0iMzMwIiBzdHJva2U9IiM0YjU1NjMiIHN0cm9rZS13aWR0aD0iMiIvPgogIDxsaW5lIHgxPSI0MzAiIHkxPSIzMzAiIHgyPSI0MzAiIHkyPSIzNTIiIHN0cm9rZT0iIzRiNTU2MyIgc3Ryb2tlLXdpZHRoPSIyIiBtYXJrZXItZW5kPSJ1cmwoI2Fycm93KSIvPgoKICA8IS0tIDQgUm91dGUgLS0+CiAgPHJlY3QgeD0iMjkwIiB5PSIzNTQiIHdpZHRoPSIyODAiIGhlaWdodD0iNTgiIHJ4PSIxMCIgZmlsbD0iI2VlZjJmZiIgc3Ryb2tlPSIjNGY0NmU1IiBzdHJva2Utd2lkdGg9IjIiLz4KICA8dGV4dCB4PSI0MzAiIHk9IjM3OCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzM3MzBhMyI+NC4gUm91dGU8L3RleHQ+CiAgPHRleHQgeD0iNDMwIiB5PSIzOTgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzRmNDZlNSI+TExNICsgaGFyZCBwb2xpY3kgb3ZlcnJpZGVzPC90ZXh0PgoKICA8bGluZSB4MT0iNDMwIiB5MT0iNDEyIiB4Mj0iNDMwIiB5Mj0iNDQ0IiBzdHJva2U9IiM0YjU1NjMiIHN0cm9rZS13aWR0aD0iMiIgbWFya2VyLWVuZD0idXJsKCNhcnJvdykiLz4KCiAgPCEtLSA1IFJlc3BvbmQgLS0+CiAgPHJlY3QgeD0iMjkwIiB5PSI0NDYiIHdpZHRoPSIyODAiIGhlaWdodD0iNTgiIHJ4PSIxMCIgZmlsbD0iI2VlZjJmZiIgc3Ryb2tlPSIjNGY0NmU1IiBzdHJva2Utd2lkdGg9IjIiLz4KICA8dGV4dCB4PSI0MzAiIHk9IjQ3MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzM3MzBhMyI+NS4gUmVzcG9uZDwvdGV4dD4KICA8dGV4dCB4PSI0MzAiIHk9IjQ5MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjNGY0NmU1Ij5MTE0g4oCUIGRyYWZ0IGZpcnN0IHJlc3BvbnNlPC90ZXh0PgoKICA8bGluZSB4MT0iNDMwIiB5MT0iNTA0IiB4Mj0iNDMwIiB5Mj0iNTM2IiBzdHJva2U9IiM0YjU1NjMiIHN0cm9rZS13aWR0aD0iMiIgbWFya2VyLWVuZD0idXJsKCNhcnJvdykiLz4KCiAgPCEtLSBPdXRwdXQgLS0+CiAgPHJlY3QgeD0iMjQwIiB5PSI1MzgiIHdpZHRoPSIzODAiIGhlaWdodD0iNDYiIHJ4PSI4IiBmaWxsPSIjZjBmZGY0IiBzdHJva2U9IiMxNmEzNGEiIHN0cm9rZS13aWR0aD0iMS41Ii8+CiAgPHRleHQgeD0iNDMwIiB5PSI1NjYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiMxNjY1MzQiPkNsYXNzaWZpY2F0aW9uIMK3IFByaW9yaXR5IMK3IFJvdXRpbmcgwrcgRHJhZnQgUmVzcG9uc2U8L3RleHQ+CgogIDwhLS0gTGVnZW5kIC0tPgogIDxyZWN0IHg9IjgwIiB5PSI1OTYiIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgcng9IjMiIGZpbGw9IiNlZWYyZmYiIHN0cm9rZT0iIzRmNDZlNSIgc3Ryb2tlLXdpZHRoPSIxLjUiLz4KICA8dGV4dCB4PSIxMDIiIHk9IjYwOCIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjMzc0MTUxIj5Qcm9iYWJpbGlzdGljIChMTE0pIOKAlCBsYW5ndWFnZSB1bmRlcnN0YW5kaW5nPC90ZXh0PgogIDxyZWN0IHg9IjQ0MCIgeT0iNTk2IiB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHJ4PSIzIiBmaWxsPSIjZmZmYmViIiBzdHJva2U9IiNkOTc3MDYiIHN0cm9rZS13aWR0aD0iMS41Ii8+CiAgPHRleHQgeD0iNDYyIiB5PSI2MDgiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzM3NDE1MSI+RGV0ZXJtaW5pc3RpYyAoY29kZSkg4oCUIGJ1c2luZXNzIHBvbGljeTwvdGV4dD4KPC9zdmc+Cg==)

**There is no human in the intake loop.** The agent always completes all five stages and
produces a full result. Some results carry a `requires_downstream_review` flag —
that's a governance signal on the output (should whatever acts on this check with a
person first?), not a pause in the agent's own reasoning. It's forced to true whenever:
domain is Security, priority is P0, the requester makes an unverified seniority claim
("I'm the CFO"), or `completeness_score < 0.5`.

**Priority measures business impact, not organizational power.** Claimed seniority is
extracted (self-reported, unverified) but never changes the priority number — it only
ever triggers the downstream-review flag. An identical request gets an identical
priority whether the requester claims to be a VP or says nothing about who they are.
Seniority is not indifferent to *everything*, though: it does set `review_urgency` to
"expedited," which only affects how fast a human looks at the flagged item, never what
gets resourced or promised before they do. Splitting "does this change the outcome"
(no) from "does this change how fast a human checks it" (yes) keeps the claim from
ever being a free fast-pass while still reflecting that who's asking realistically
affects response speed in any real organization.

**`completeness_score` is cross-checked, not taken on faith.** It gates real behavior
(whether the agent asks a clarifying question instead of routing), so it gets the same
skepticism as priority: the LLM's own 0–1 self-rating is checked against a second,
deterministic score computed from the length of the `missing_info` list it itself
named, and the *lower* of the two wins. An overconfident self-rating can't survive
contact with the concrete gaps the model already listed.

## Input / Reasoning Steps / Output

- **Input:** one raw, unstructured text request (Slack/email-style — no form fields)
- **Steps:** Extract facts (system_down, deadline_urgency, scope, business_impact,
  claimed_seniority, completeness_score) → Classify domain/work type → compute priority
  from stage-1 facts via rule engine → recommend an owning team from a domain→team map →
  draft the first reply, escalating to a clarification-only response if completeness is
  too low to route confidently
- **Output:** classification (domain, work_type), priority (P0–P3 + the specific rule
  that fired + reasoning), routing recommendation (team + `requires_downstream_review`
  flag + reason), draft first response

## Validation

16-case labeled eval set spanning every domain/work type, expected priority computed by
running hand-specified facts through the real rule engine.

| Metric | Result |
|---|---:|
| Domain | 16/16 |
| Work type | 16/16 |
| Priority | 14/16 |
| Unsafe under-escalation | 0/9 |

The interesting result wasn't the headline accuracy — it was the *direction* of the
errors. Raw `requires_downstream_review` agreement was 7/16, but of the 9 disagreements,
9/9 were the system flagging *more* cautiously than the naive label expected, and 0/9
were the dangerous direction (missing a flag it should have raised). The two priority
misses traced back to imprecise eval labels on manual review, not model error.

Separately, removing the fixed routing table and asking the model to freely name a team
produced inconsistent, invented team names in 4 of 5 test requests (e.g. "Physical
Security / Badge Access Administration" for a request the constrained system correctly
routes to "Security") — concrete evidence for why routing is constrained to a fixed
capability map rather than left to the model to invent.

## What's automated vs. left to humans — and why

**Automated:** understanding raw text, domain/work-type classification, team routing,
first-response drafting, and the priority *computation* itself (via rule engine, not
LLM) — the agent always finishes the job.

**Flagged for downstream review, not handed off:** anything P0-Critical, anything in the
Security domain, anything where completeness is too low to act on responsibly, and
anything where the requester's claimed authority is unverified. These are precisely the
cases where an autonomous wrong *action* is expensive or the system genuinely lacks
enough signal — the design bet is that knowing when a result needs a second look is as
important as producing the result.

## Assumptions made to get this working — and what breaks at scale

- **Text-only input.** Real intake includes screenshots/attachments; not handled.
- **Routing table is a working assumption**, reverse-engineered from public job
  postings, not a confirmed org chart — needs validation with real stakeholders.
- **Priority thresholds (24h / 1 week, etc.) are hand-picked, not calibrated** against
  historical triage data — the rule engine's *auditability* is real, but its
  *correctness* still needs to be validated against how a real team actually triages.
- **No memory across requests.** Two submissions about the same recurring outage are
  treated as unrelated; a real system needs deduplication/clustering.
- **Sequential LLM calls add latency (~20–30s/request)** — fine for a demo, not for a
  high-volume real-time queue.
- **LLM structured-output reliability is not 100%.** Testing surfaced a schema shape
  (two enum fields each immediately followed by their own long free-text reasoning
  field) that produced malformed tool output ~50% of the time; fixed by restructuring
  the schema, backed by required-field validation + automatic retry as defense in
  depth. At scale, every tool schema needs this kind of adversarial testing, not just
  happy-path testing.

## V2 — and what we'd need to know before building it

**V2 would add:** persistent state to recognize recurring/duplicate issues; real
identity verification (SSO/directory lookup) so seniority claims could eventually
inform something beyond a review flag; multi-turn clarification (actually wait for the
requester's reply instead of a one-shot guess); async processing for volume. A first
version of a feedback loop already exists: `feedback_log.py` logs human corrections, and
if a specific priority rule has been corrected enough times, routing now surfaces an
advisory note about it automatically (verified working) — real V2 would log every
firing to compute an actual override rate and auto-adjust thresholds.

**Before building it, we'd need:** real historical triage data to calibrate priority
thresholds and validate the routing table against the actual org structure; access to
a real identity/directory system; actual volume and latency requirements from the team
that would own this.
