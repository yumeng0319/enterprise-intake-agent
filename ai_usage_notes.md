# AI Usage Notes

How AI was used throughout this project — for the live Q&A, not for submission.

## What prompts worked

- **Forcing structured output via tool_choice, not free-text + parsing.** Every stage
  (extract/classify/route/respond) uses a forced tool call with a JSON schema instead of
  asking the model to "return JSON" in prose. This was reliable *once the schema itself
  was fixed* (see below) — free-text-then-parse would have been far more fragile.
- **Asking the model to defend a design out loud, not just implement it.** When adding
  the requester-seniority signal, the useful prompt wasn't "add a seniority field" — it
  was "how would someone abuse a priority system that responds to claimed urgency or
  authority, and how do we design against that specifically." That produced the actual
  end state — claimed seniority never touches the priority number, it only ever
  triggers a downstream-review flag — rather than a naive "if CFO then P0" rule I'd
  have had to catch later. An earlier version let seniority nudge priority up slightly
  when paired with real business context; a later review correctly pushed back on even
  that ("why should a VP's request outrank an analyst's for identical business impact?")
  and it was removed outright.
- **Giving the model today's date explicitly in the extraction prompt** rather than
  relying on training-cutoff knowledge, so relative time expressions ("tomorrow," "by
  Friday") resolve against the actual run date instead of a stale guess.

## Outputs rejected, and why

- **The classify_request schema produced malformed tool output.** Testing (10 trials)
  showed a ~50% failure rate: the model's output would have `work_type`'s value leak
  into `domain_reasoning` as stray XML-tag-like text, dropping the `work_type` key
  entirely. Rejected outright — not a prompt-wording issue, a structural one.
- **First fix hypothesis was wrong, and testing caught it.** Guessed the fix was
  reordering fields (enums before their reasoning text). Tested it: 8/8 failures — worse,
  not better, just with a different field dropped each time. Rejected that theory
  instead of shipping it on faith. The actual fix (merging the two reasoning fields into
  one) was validated with 10/10 clean runs before it went in.
- **The `requires_downstream_review` eval ground truth was rejected mid-analysis.** A
  naive expected-value function (based only on hard policy triggers) produced a 44%
  agreement number that looked bad. Digging into *which direction* the misses went (9/9
  over-cautious, 0/9 under-cautious) showed the ground truth itself was incomplete, not
  the system — the raw percentage was rejected as the headline number in favor of the
  breakdown.

## Where a tool challenged assumptions in a useful way

- Pushed back on adding **multimodal (screenshot) input** when it came up as a "nice to
  have" — argued it was unrequested scope expansion that would dilute time better spent
  on the core reasoning chain the case study is actually evaluating. Cut it, documented
  it as a deliberate V2 boundary instead.
- Flagged that the case study's own framing (`"the intake problem"`) hadn't been
  interrogated yet, and reframed the design question from "how do I automate intake" to
  "what does a human triager actually do that's hard to replicate" (uncertainty
  judgment, institutional memory, calibrated skepticism about urgency/authority claims) —
  this reframe is what the P3-default-on-bare-claims behavior and the
  confidence-gated-clarification mechanism are actually *for*, not just isolated
  features.
- When asked to add "always trust an executive requester," argued for the opposite:
  unverified claims should *only* ever unlock mandatory downstream review, never
  automated priority — reframing "how do we honor authority" as "how do we make
  authority claims cost nothing to fake."
- Also caught a wording contradiction before it reached a reviewer: the UI said "no
  human in the loop" while the design doc described `needs_human_review` checks, which
  reads as a direct contradiction out of context. Fixed by renaming the concept to
  `requires_downstream_review` and being explicit that the agent always completes all
  five stages itself — the flag governs what happens *after* the agent finishes, not
  whether it finishes.
- Proposed testing, rather than asserting, that routing hallucinated team names without
  the fixed routing table. Ran it: 4 of 5 unconstrained test requests produced team
  names that don't exist in the actual routing table (e.g. "Physical Security / Badge
  Access Administration" for a request the constrained system correctly routes to
  "Security"). Turned a plausible-sounding claim into a verified one before it went in
  the AI-usage story.

## Where AI was wrong and had to be overridden

- **The malformed-tool-output bug itself.** This is the clearest case: Claude's own
  structured output was empirically wrong on this schema shape roughly half the time.
  No amount of asking it to "be careful" fixed it — required-field validation +
  automatic retry (code, not a better prompt) was the actual fix, plus restructuring
  the schema so the failure mode stopped recurring.
- **The reordering hypothesis** (above) — proposed by me as the likely fix, disproven by
  testing, discarded before it shipped.
- **Default eval interpretation.** Initial framing of the 44% `requires_downstream_review`
  number as "a weak spot" was wrong until the false-positive/false-negative split was
  actually computed — the raw metric was misleading on its own and needed a human
  (well, needed *me*) to notice the framing was off before presenting it.
- **An earlier version of the seniority rule.** It let claimed seniority lift priority
  from P3 to P2 when paired with real business context. Defensible on paper, but it
  couldn't survive the question "why should identical business impact get a different
  priority based on a title no one verified?" — overridden, priority now only ever
  depends on stated business facts.
- **`completeness_score` was left as raw LLM self-rating for most of the build**, even
  though it gates real behavior (whether the agent asks for clarification). It didn't
  get the same skepticism priority did until it was pointed out directly: an LLM
  self-rating that drives a decision is exactly the pattern the rest of this design
  argues against. Fixed by adding a second, deterministic score computed from the
  length of the model's own `missing_info` list, and taking whichever of the two is
  lower — verified end-to-end: a case where the model self-rated 0.9 complete but had
  listed 4 concrete gaps got correctly overridden down to 0.2.
