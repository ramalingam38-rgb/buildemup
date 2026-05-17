# 01 — Sourcing Channels for B-238 Architect

**Goal:** Build a longlist of 8-12 candidate architects with realistic responsiveness, then narrow to 3-4 for vetting.

**Why these channels in this order:** Chennai/Tamil Nadu first because TNCDBR (Tamil Nadu Combined Development and Building Rules) is the most-cited jurisdiction in the codebase. Then broader Indian channels for fallback. Always prefer practitioners with current-day field exposure (active commissions in last 12 months) over pure academics, because the project's correctness goals are real-world plan-approval, not theoretical.

---

## Tier 1 — Chennai / Tamil Nadu (preferred)

### A. Indian Institute of Architects (IIA) — Tamil Nadu Chapter
- **URL:** Check `https://indianinstituteofarchitects.com/` for the Tamil Nadu chapter directory and current office bearers.
- **What to ask for:** Chapter secretary's email; request a referral note explaining the project (use the template in `03_outreach_message_template.md`).
- **Best for:** Reputational filter. IIA membership = qualified, registered, peer-vetted.
- **Cost:** Free (the membership directory). Architects you contact through it set their own rates.

### B. Council of Architecture (COA) — registration verification
- **URL:** `https://coa.gov.in/` — public registry of all India-registered architects.
- **What to ask for:** Use the search-by-state-and-name function to verify any candidate's COA registration number is active. **This is a HARD must-check before signing.** Anyone calling themselves "architect" in India must hold a current COA-registered number; practising without it is an offense under the Architects Act 1972.
- **Best for:** Final disqualifier check, not initial sourcing.

### C. Anna University SAP (School of Architecture and Planning) alumni network
- **URL:** Anna University SAP alumni association, Chennai.
- **Approach:** Reach out to recent graduates (5-15 years post-degree) who are now in independent practice. They are often more affordable than mid-career partners at big firms and more willing to take a non-construction "audit" engagement.

### D. Local firms — direct outreach
Examples of Chennai-based architectural firms known for residential/small-plot work (the project's primary use case). Verify each is still active before contacting:
- Firms focused on residential up to 2-3 floors
- Firms with published portfolios of plots under 2400 sq ft
- Avoid firms that exclusively do commercial / high-rise / luxury — wrong calibration

**How to find them:** Google `"Chennai residential architect" small plot` or `"Chennai independent architect" residential` (May 2026). Cross-check Instagram presence (Indian architects increasingly use Instagram for portfolio). Look for blog posts about TNCDBR navigation — that's a strong signal of practical familiarity.

---

## Tier 2 — Other Tamil Nadu cities (fallback)

If Chennai responses are slow:
- **Coimbatore** — second-largest TN architectural community
- **Madurai** — strong for traditional housing review
- **Tier-2 cities** (Trichy, Salem, Erode) — likely lower rates, may be a better budget fit at the ₹15K end

---

## Tier 3 — Pan-India (last resort)

Other state architects can still review — most of the code's compliance logic generalizes (NBC 2016 is national; only TNCDBR overlays are Tamil-Nadu-specific):
- **Bangalore / Karnataka** — BBMP byelaws differ but architects familiar with multi-state work
- **Mumbai / Maharashtra** — strong NBC compliance discipline; DCR is different from TNCDBR but the rigor is high
- **Pune** — strong for soil/foundation review (the murrum / BLACK_COTTON distinction matters here)
- **Hyderabad / Telangana** — GHMC byelaws differ; less ideal but workable

Avoid first-time foreign-trained-only architects without active India practice — they may miss the local plan-approval idiosyncrasies that are the whole point.

---

## Tier 4 — Adjacent expertise (if specific gaps surface)

You may want to engage specialists, not generalists, for these:
- **NBC 2016 reviewer** — someone who works on fire/egress design (NBC Part 4) for the corridor minimum verification (B-108 / B-150 follow-up)
- **Plumbing engineer** — for B-220 (hydraulics depth in C10). Separate engagement, distinct from B-238.
- **Structural engineer** — for C7 grid sanity, especially the IS 13920 stub-column patterns. Not required for B-238 but worth knowing.
- **Vastu consultant** — only if you want B-099 (Vastu FULL tier) to ship pre-v1; otherwise irrelevant.

---

## How to build the longlist

Practical recipe (3-4 hours, one evening):

1. **30 min** — Search the IIA Tamil Nadu chapter directory; collect 5 names with contact methods.
2. **30 min** — Google search for `Chennai residential architect TNCDBR` and similar; collect 5-8 names from blog posts, firm websites, LinkedIn.
3. **30 min** — Verify each candidate's COA registration is active via `coa.gov.in`. Drop anyone unverifiable.
4. **30 min** — Check each candidate's Instagram / LinkedIn for last-12-months evidence of active practice. Drop anyone who looks dormant.
5. **30 min** — Filter for residential-plot focus, not luxury-villa or commercial. Drop the wrong-calibration ones.
6. **30 min** — Score remaining candidates on responsiveness signals: does their firm website have a working contact form? Recent blog? Listed phone number? Drop the unreachable ones.

You should end with **8-12 candidates**. Send the outreach message (from `03_outreach_message_template.md`) to all of them simultaneously; expect 30-50% response rate.

---

## Realistic timeline

| Step | Calendar time | Why |
|---|---|---|
| Build longlist | 3-4 hours (one evening) | Mostly manual search |
| First outreach | 1 day | Send all messages same day |
| Initial replies | 3-7 days | Working architects are busy; reply within a week is normal |
| Vetting calls | 2-3 days | 15-min calls each with 3-4 shortlist |
| Pick + sign | 1-2 days | Engagement letter back-and-forth |
| Briefing pack send | 1 day | After signed |
| Architect review | 7-14 days | Depending on volume; expect them to need 6-10 focused hours but spread across calendar |
| Debrief call | 1 day | After deliverable arrives |

**Total calendar:** 3-5 weeks from start to feedback in hand. **This is why we start at S56 open, even with Bucket C polish running in parallel.**
