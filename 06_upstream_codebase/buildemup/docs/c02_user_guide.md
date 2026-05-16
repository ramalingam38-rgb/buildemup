# BuildemUp Feasibility Report — User Guide

This guide helps you understand your BuildemUp feasibility report. The report
tells you whether your house plan is buildable — and surfaces honest trade-offs
you may not have known you were making.

## Quick start: reading the summary

The summary section gives you the bottom line in three numbers:

- **Practical score (X/100)** — How well your stated preferences work as a
  buildable design. Higher is better.
- **Code-Strict score (Y/100)** — How well your design holds up to full
  NBC + DCR compliance with no compromises. Often lower than Practical.
- **Cost delta (₹ZL)** — What you'd add to upgrade Practical → Code-Strict.

Then **TOP CONCERNS** lists the 3 biggest issues to think about. If you have
no time to read the full report, this is enough to take action.

## Understanding "Practical" vs "Code-Strict"

These are two ways of looking at the same plot + brief:

**PRACTICAL** = "Can I build what I want?"

It uses your stated preferences as-is. If you said "I want 0.9m setbacks
to maximise floor area," Practical accepts that. It only fails on physical
impossibilities (e.g., negative setbacks, plot too small for any building).

**CODE-STRICT** = "What does the law strictly require?"

It applies NBC 2016 + your city's Development Control Regulations to the
letter. If your city requires 1.5m front setbacks and you stated 0.9m,
Code-Strict will flag this as BLOCKING.

The point is not that one is right and the other is wrong. The point is to
make your trade-offs **visible** so you can make informed decisions about
what to compromise on and what to push back on.

## Understanding scores (0–100)

Both lanes use the same scoring method:

- **Start at 100**, deduct points for issues
- **HIGH-confidence SOFT_WARN**: -10 points
- **MEDIUM-confidence SOFT_WARN**: -7 points
- **LOW-confidence SOFT_WARN**: -5 points
- **Any HARD_FAIL** caps the score at **40 max**, regardless of how many

This means: if you have even one HARD_FAIL, you can't score above 40 — that
issue is design-blocking and needs to be addressed before construction can
proceed.

## Reading the per-lane details

Each check has a result in one of four buckets:

| Symbol | Meaning |
|---|---|
| ✗ BLOCKING | Hard fail. This issue must be addressed. |
| ! WARNING | Soft warn. Workable but worth attention. |
| ✓ PASSED | No issue. |
| - NOT APPLICABLE | Doesn't apply to your build (e.g., parking check skipped if no stilt). |

Each check has a category (Spatial, Cost, Compliance, Structural, Usability)
and a confidence level (High / Medium / Low). Lower-confidence findings
generally come from **city defaults** (educated guesses) rather than verified
data — see the "Verification recommended" section.

## Understanding gaps

A **gap** appears when the Practical and Code-Strict lanes diverge on a
specific check. For example:

> [DECISION NEEDED] solar_exposure
>   Plot faces N (score 30/100). Practical accepts the marginal sun exposure;
>   Code-Strict requires score ≥ 55 per NBC Part 8 daylight factor.

This is telling you: "you've accepted dimmer rooms (Practical OK) but the
NBC daylight code says you should redesign for better light (Code-Strict
fails)."

Gap severities:
- **DECISION NEEDED** — Real divergence. You need to decide.
- **SIGNIFICANT** — Notable trade-off. Worth thinking about.
- **MINOR** — Small trade-off. May not need a decision.
- **INFO** — Informational only. No decision needed.

## Verification recommended

When BuildemUp doesn't have your specific data (soil type, water table depth,
distance from electric lines), it uses **city-typical defaults** as educated
guesses. Each unknown shows:

- What field is missing
- What value we're currently assuming
- Where to get verified data, including approximate cost

For example:

> [IMPORTANT] soil_type
>   Currently assuming: Assumed sandy_alluvial (typical for Chennai)
>   Get a site-specific soil test from a NABL-accredited geotechnical lab.
>   Cost: ₹5,000-₹15,000. Timeline: 3-5 days.

If the assumed value would normally HARD-fail a check, BuildemUp downgrades
it to a SOFT WARNING — we don't block you on a guess. But you should still
get the verification done before final design.

## Action steps

Action steps are sorted by priority (1 = most urgent):

| Priority | Meaning |
|---|---|
| P1 | HARD blocker with high confidence — must address |
| P2 | HARD blocker with assumed data — verify first |
| P3 | SOFT warning with high confidence — real concern |
| P4 | SOFT warning with assumed/lower confidence — advisory |

Each action step links back to the checks that triggered it.

## Frequently asked questions (FAQ)

The FAQ section at the end of the report includes Q&A specific to the checks
that triggered for your brief. These are common questions homeowners ask
about each topic.

## What this report is NOT

- **Not architectural design.** This is feasibility, not a building plan.
  You still need a licensed architect for actual drawings + approval.
- **Not legal advice.** Approval requirements vary by city, ward, and even
  individual officers. Always confirm with your local authority.
- **Not site-specific.** City defaults for soil + water table are estimates;
  your specific plot may differ. Verify before final foundation design.
- **Not final.** The Practical report assumes you accept your stated
  trade-offs. As you iterate (Sessions H+ will add an interactive UI),
  you can accept/reject each gap and the report updates.

## Quick decisions guide

For each gap in your report, ask yourself:

1. **Can I afford to upgrade?** Look at the cost delta. ₹0.15L for soil/water
   verification is often worth it for any G+1+ build.

2. **Will this cost me later?** Below-NBC setbacks may face issues at approval
   time, force a variance application, or limit resale. Solar/ventilation
   compromises affect daily living quality.

3. **Is the assumption defensible?** If a check is failing because of a
   city-default assumption (LOW confidence), get the real data first before
   deciding to compromise.

If you're stuck, share the report with a licensed local architect — they
can help interpret which compromises are common in your area and which are
flagged unusually strictly.

---

*Generated by BuildemUp v0.1. For questions or feedback, contact the
BuildemUp team or your architect.*
