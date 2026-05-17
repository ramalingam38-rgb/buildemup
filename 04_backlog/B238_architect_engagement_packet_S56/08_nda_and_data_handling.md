# 08 — NDA + Data Handling

**Purpose:** Define what's confidential, what's shareable, and what protection the engagement letter needs to give Ramalingam without scaring off the architect.

---

## What's confidential (must NOT leak)

These items are confidential to BuildEase / Ramalingam:

1. **The product name and brand identity.** Whether the final name is "BuildEase," "BuildemUp," or something else — undecided. Architects MUST not refer to the product by name externally.
2. **The 17-component spec architecture itself.** The order, the names, the LOCK versions — this is the IP of the project.
3. **The pricing model and business model.** How Ramalingam plans to monetize is not in the briefing pack and is none of the architect's concern, but if it comes up, it's confidential.
4. **The founder's commercial timeline and launch plans.** "When is v1 going live, who are the target users, what's the marketing strategy" — confidential.
5. **The specific KB defaults that have not been published.** The city construction rates per ₹/sqft, the soil-class table, the cultural-profile variant definitions — these are accumulated IP, confidential.
6. **The fact that Ramalingam is using Claude / AI as a collaborator.** This is private development methodology, not for architect to disclose.

---

## What's shareable (architect CAN reference)

The architect can talk publicly about:

1. **The engagement existed.** "I did a paid architectural review for a residential design software project" is fine.
2. **At the level of category, what was reviewed.** "I reviewed setback rules, FAR calculations, structural grid logic" — fine.
3. **Personal anecdotes about the review experience.** "It was interesting; the founder is detail-oriented; the deliverable was 4 pages" — fine.

The architect CANNOT publicly disclose:

- The product name
- The founder's name (Ramalingam) — unless agreed in writing later
- Specific findings (the deliverable findings are Ramalingam's IP after payment)
- The use of AI in the project's development
- Screenshots, code snippets, or specific spec excerpts
- Future plans, launch dates, business model

---

## Recommended NDA clauses (already in engagement letter draft)

From `05_compensation_structure.md` engagement letter draft, the relevant clauses:

> All project documents (specifications, code, knowledge-base rules, master documents) provided by Engager remain the exclusive property of Engager and are treated as confidential by Reviewer.
>
> The findings produced by Reviewer under this engagement become the property of Engager upon final payment. Reviewer may reference this engagement on a CV/portfolio at the level of "architectural review for a residential design software project" without identifying the product, its features, or the Engager by name.

**This is sufficient for a ₹15-40K engagement.** A separate standalone NDA is overkill at this scope; the clauses above + the implicit professional duty an architect carries are enough.

If the architect insists on a separate NDA (rare at this scope), use the template below.

---

## OPTIONAL — Standalone NDA template

```
MUTUAL NON-DISCLOSURE AGREEMENT

Date: [DATE]
Parties:
  Disclosing Party: Ramalingam, [contact]
  Receiving Party: [Architect name + COA registration number, contact]

1. PURPOSE
This Agreement governs the disclosure of confidential information by the
Disclosing Party to the Receiving Party in connection with an architectural
review engagement for a residential design software project (reference B-238).

2. CONFIDENTIAL INFORMATION
"Confidential Information" includes: specification documents, knowledge-base
defaults, master architecture documents, design rules, severity tables,
cultural profile variants, soil/city defaults, business model, product name,
and any other information designated as confidential or that a reasonable
person would understand to be confidential under the circumstances.

3. EXCLUSIONS
Confidential Information does NOT include information that:
  (a) is or becomes publicly available through no fault of Receiving Party;
  (b) was rightfully known by Receiving Party before disclosure;
  (c) is rightfully obtained by Receiving Party from a third party without
      breach of obligation; or
  (d) is independently developed by Receiving Party without reference to
      Disclosing Party's Confidential Information.

4. OBLIGATIONS
Receiving Party agrees to:
  (a) hold Confidential Information in strict confidence;
  (b) not disclose Confidential Information to any third party;
  (c) use Confidential Information solely for purposes of the review
      engagement;
  (d) take reasonable measures to protect Confidential Information from
      unauthorized disclosure.

5. PERMITTED REFERENCE
Receiving Party may reference the engagement on CV/portfolio at the
abstraction level of "architectural review for a residential design
software project," without identifying the product, the Disclosing
Party, or specific findings.

6. TERM
This Agreement applies for 3 years from the date of signing.

7. RETURN / DESTRUCTION
On request from Disclosing Party, Receiving Party will return or destroy
all Confidential Information in their possession.

8. JURISDICTION
This Agreement is governed by the laws of India and subject to the
exclusive jurisdiction of courts in [Chennai / Tamil Nadu].

SIGNATURES
Disclosing Party: ____________________  Date: __________
Receiving Party:  ____________________  Date: __________
                   [Name + COA Reg No.]
```

---

## What to do if architect leaks confidential information

Realistically: at ₹15-40K, the practical remedy is reputational, not legal.

- Document the leak with timestamp + source.
- Send a written cease-and-desist email to architect, citing the engagement letter / NDA clause.
- If continued, file a complaint with the IIA Tamil Nadu chapter (architect's professional body has a code of conduct).
- Avoid litigation unless the leak causes material damage (very unlikely at this scope).

The deterrent is the architect's professional reputation, not contract penalty. Pick a reviewer whose reputation is on the line.

---

## What Ramalingam should do on his side

Even before sending the briefing pack:

1. **Use a clear file-naming convention.** All files sent to architect must include "B-238" or "review_pack" in the filename so it's clear they are engagement-related.
2. **Use a single email thread** for the engagement. Don't fragment across multiple threads, phone, WhatsApp.
3. **Don't share login credentials to anything.** The architect doesn't need access to GitHub, the codebase, the running server. They only need the spec PDFs/markdown.
4. **Don't send the entire `06_upstream_codebase/` directory.** Code is not the review subject.
5. **Don't send raw session transcripts.** Those expose how the project is built (AI-assisted), which is private.
6. **Keep a copy of every email exchange.** For audit trail.

---

## What to do POST-engagement

After deliverable is received and final payment is made:

1. Send a written acknowledgment of receipt and final payment.
2. Confirm in writing: "The engagement under B-238 is now complete. Confidentiality obligations under the engagement letter / NDA continue for the term specified."
3. Optionally: thank the architect publicly (at the abstraction level above — "I worked with a Chennai architect who provided excellent independent review") if the engagement was good. This is a small reciprocity that costs nothing and may help with future referrals.
4. Save the deliverable in `04_backlog/B238_architect_review_findings_S57.md` (or whatever session it lands in). Treat it as a backlog source document.
