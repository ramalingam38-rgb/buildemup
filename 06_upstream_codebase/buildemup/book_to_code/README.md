# Book-to-Code Pipeline

Per the BuildEase vision (slide 4), our knowledge base is built by
converting Indian engineering books, building codes, and Vastu texts
into structured rules, then into executable code.

This folder establishes the **pattern** for that pipeline. The pipeline
itself (PDF extraction with Gemini API per the vision) is Phase 1
build month 1-2. v0.4 establishes the folder structure + one worked
example so future rule additions follow the same pattern.

## The pipeline

```
   [PDF source]                      stage 1
         ↓                       extract: text + tables
   01_extracted/<source>.txt        from PDF (manual or
                                    Gemini API)

         ↓                           stage 2
                                  structure: convert to
   02_structured/<source>.json     machine-readable rules

         ↓                           stage 3
                                  code: convert rules to
   03_code/<source>.py             executable Python that
                                    integrates with kb/
```

## Folder conventions

`01_extracted/` — Raw text/tables from the source. One file per source
(e.g., `IS456_section_25.txt`). This is the audit trail: lets a
structural engineer review what we extracted vs the original.

`02_structured/` — JSON files with the extracted rules in machine-
readable form. One file per source. Format below.

`03_code/` — Python modules that consume the JSON and provide functions
the rest of `kb/` can import. One module per JSON file usually.

## Structured rule format

Each `02_structured/*.json` follows this shape:

```json
{
  "source": {
    "title": "IS 456:2000 — Plain and Reinforced Concrete",
    "section": "25.1.2",
    "page": 71,
    "publisher": "Bureau of Indian Standards",
    "extracted_date": "2026-04-01",
    "extracted_by": "manual"   // or "gemini-1.5"
  },
  "rules": [
    {
      "rule_id": "IS456_25_1_2_short_column",
      "applies_to": "rcc_column",
      "condition": {
        "metric": "slenderness_ratio",
        "operator": "<",
        "value": 12,
        "unit": "dimensionless"
      },
      "consequence": "Treated as short column. No buckling check needed.",
      "confidence": "high",
      "notes": "..."
    }
  ]
}
```

## Worked example: IS 456 cl. 25.1.2 — Slenderness Limit

We've already implemented this in `kb/seismic_detailing.py:check_slenderness()`.
This worked example shows the pipeline that produced it, so future
additions follow the same flow.

See:
- `01_extracted/IS456_25_1_2.txt` — The text we extracted
- `02_structured/IS456_25_1_2.json` — Machine-readable rule
- `03_code/IS456_25_1_2.py` — The code that uses the JSON

## When to use this pattern

When adding a new rule from a code/book:

1. Find the source text. Save it to `01_extracted/`.
2. Convert to structured JSON in `02_structured/`.
3. Write a small loader in `03_code/` that reads the JSON and exposes
   a function.
4. Import that function from the relevant `kb/` module.

For one-off rules, you can skip the JSON and write directly in `kb/`.
But for any rule that comes from a published code or book, use this
pipeline so we have an audit trail for engineer review.

## Why this matters

Per the vision doc, BuildEase will eventually have 100+ books and codes
in its knowledge base. Without this discipline, that becomes
unmaintainable spaghetti. With it, every rule is traceable to its
source — which is exactly what a structural engineer or code auditor
needs to trust the system.

## v0.4 status

- ✅ Folder structure established
- ✅ One worked example (IS 456 slenderness)
- ⏳ Gemini-API automation (Phase 1 month 1-2)
- ⏳ Bulk extraction of NBC 2016 + remaining IS codes (Phase 1)

†= placeholder name marker.
