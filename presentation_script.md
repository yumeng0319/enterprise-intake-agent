# Presentation Script — 5 min design walkthrough

## Opening framing (say this before touching the architecture diagram)

Don't open with "here's my pipeline." Open with the reframe — it's the thing that
separates this submission from "I automated a ticket router."

> "Before I built anything, I asked what a good human triager is actually good at —
> because if it's just 'read text, pick a category,' an LLM is already better at that
> than most humans: faster, more consistent, never has a bad Monday. So that's not
> the interesting problem.
>
> What a good triager actually does is three harder things:
> 1. **Knows when they don't know enough** to make the call, and asks instead of guessing.
> 2. **Remembers patterns across time** — this is the third complaint about the same ETL
>    job this week, even though each ticket looks like a one-off.
> 3. **Has calibrated skepticism about urgency and authority claims** — a seasoned
>    triager doesn't fast-track something just because someone says the CFO needs it.
>
> Those three things are what I actually designed for. Property 1 and 3 are built into
> this prototype. Property 2 — institutional memory — is the hardest one, and I
> deliberately didn't try to fake it in a week. I'll say exactly why later."

This gives you a spine for the rest of the 5 minutes: every architecture decision you
show next should map back to one of these three properties, not be presented as an
isolated technical choice.

**Pre-empt the obvious gotcha question.** Somewhere in the first two minutes, say this
explicitly, don't wait to be asked: "The agent always completes all five stages itself
— there's no human anywhere in that loop. What some outputs carry is a
`requires_downstream_review` flag: a governance signal for whatever *acts* on the
result, telling it whether to double-check before executing. That's different from the
agent stopping to wait for a person." If you don't say this up front, "you said no
human in the loop but your architecture has human review checks" is the first thing
you'll get asked, and it'll look like you're backpedaling instead of explaining a
design you already made.

## Structure for the remaining ~4 minutes

**1. Map the architecture to the three properties (don't just narrate the pipeline)**

- "Property 1 — knowing when you don't know: this is why priority is computed by a
  rule engine, not the LLM, and why completeness_score below 0.5 makes the agent ask a
  clarifying question instead of guessing. [point at Extract -> Priority in the diagram]"
- "Property 3 — calibrated skepticism: a self-reported 'I'm the CFO' claim never
  touches priority at all — priority only ever looks at outage status, deadline, scope,
  and business impact. What the claim *does* do is force a downstream-review flag,
  because the identity is unverified. Unverified authority buys a human's attention,
  never a shortcut, and never a number change either."
- "Property 3, second half — this same skepticism is why routing is constrained to a
  fixed team list instead of left open. I tested what happens without that constraint:
  4 of 5 requests came back with invented team names that don't exist in our actual
  org — plausible-sounding, wrong. The model is good at language, not at knowing your
  org chart, so I don't let it guess at one."
- "Property 2 — institutional memory: not solved. No request has memory of past
  requests. I'll come back to this in the assumptions/V2 section — it's the single
  biggest gap between this prototype and something you'd actually trust in production."

**2. One sentence on what you deliberately did NOT build, and why that was the right call**

> "I considered making the agent not just route requests but sometimes *resolve* them —
> e.g. actually drafting the dashboard spec for a 'build me a dashboard' request instead
> of just routing it. I deliberately cut that. Getting classification and priority
> *defensible* was the harder, higher-leverage problem to prove out first — a system
> that confidently does the wrong thing faster is worse than one that routes correctly.
> Auto-resolution for the lowest-risk categories is a natural V2 extension once the
> triage layer underneath it is trustworthy."

**3. Land on the eval numbers, not just the architecture**

> "I also didn't want to just eyeball a few examples and call it good. I built a small
> labeled test set — N requests with expected domain/priority/team — and measured
> agreement. [state the actual numbers from eval_report — see eval.py output]. That's
> not a rigorous benchmark, but it's more evidence than 'I ran a few examples and they
> looked right,' which is what most one-week prototypes stop at."

## Reflection section (last 5 min of the presentation)

Three concrete, specific stories — not "AI is sometimes wrong":

1. **Where AI surprised you (in a good way):** the seniority-claim gaming design. Ask
   Claude directly "how would someone try to abuse a priority system that responds to
   claimed urgency" and it independently proposed the same defense you were reaching
   for — validated your own instinct rather than requiring you to fully specify it. The
   design went through one more round after that: an earlier version let a seniority
   claim nudge priority up slightly if paired with real business context, and that got
   cut too, because it couldn't survive "why should a VP's request outrank an analyst's
   for identical business impact?" Priority now depends only on stated business facts,
   full stop.
2. **Where AI was concretely wrong, and you had to catch it:** the classify_request
   schema produced malformed tool output (a field's value leaking into another field's
   text as stray tag syntax) on ~50% of calls for one specific schema shape. Retrying
   didn't reliably fix it — required-field validation caught it, and restructuring the
   schema (merging two adjacent enum+reasoning field pairs into one) actually fixed the
   root cause, verified by a 10/10 clean re-test. Concrete, falsifiable, not vibes.
3. **Where AI fell short / what's next:** no institutional memory across requests —
   the system re-litigates the same recurring issue from scratch every time. Next build
   would be a lightweight dedup/clustering layer plus the correction-feedback loop
   (prototype exists in `feedback_log.py` — human overrides get logged, and if a
   specific rule has been overridden often, the routing stage surfaces that as a
   warning) so the system gets calibrated by real usage instead of hand-picked
   thresholds.
