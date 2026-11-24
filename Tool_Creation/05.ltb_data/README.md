# LTB real-data pipeline

Turns real Landlord and Tenant Board orders (from [A2AJ Canadian Legal Data](https://huggingface.co/datasets/a2aj/canadian-case-law), Open Government Licence – Ontario) into what Housekeeper shows tenants. The same data can feed the decision-tree charts on Ratio.

| File | What it does |
| --- | --- |
| `ltb_extract.py` | Reads one order's text and returns structured fields: application type, who attended, representatives, Tenant Duty Counsel, N4 validity, s.82, s.83(3), outcome, rent and arrears, evidence provided or missing, household circumstances |
| `ltb_fetch.py` | Downloads orders (Hugging Face bulk, or the A2AJ API for one date range) and runs the extractor → JSONL |
| `ltb_stats.py` | JSONL → `ltb_stats.json`: outcomes per case type, the N4 decision tree, corporate filers, representation |
| `build_guidance.py` | Writes `../01.local app version/ltb_guidance.json`: the evidence checklist per case type, each point linked to real orders |
| `fixtures/` | Six real orders (tenant names replaced) used by the tests |

## Full run (about 56,000 orders)

```bash
pip install datasets pandas
python ltb_fetch.py hf --out ltb_records.jsonl
python ltb_stats.py ltb_records.jsonl --out ltb_stats.json
python build_guidance.py --stats ltb_stats.json --keep-examples "../01.local app version/ltb_guidance.json"
```

`--keep-examples` keeps the current example orders and adds the counts. To refresh the examples too, save A2AJ search results (one JSON list per topic, named as in `build_guidance.py`) and pass `--samples DIR`.

## Status (Nov 2026)

- The extractor is tested on 6 full real orders and checked against 250 real excerpts. Measured hit rates: postponements 47/50, Tenant Duty Counsel 50/50.
- `ltb_guidance.json` was built from about 550 real excerpts, collected through A2AJ search.
- Counts from the full dataset are **not** in yet: bulk download could not be reached from the build environment. Run the commands above to add them.

## Privacy rules

- Outputs never include tenant names. Examples show the LTB file number, date and a short excerpt; an excerpt that names a person in full is skipped.
- `filers` in `ltb_stats.json` lists corporate landlords only (25+ applications by default), never individual landlords.
- "Eviction" in the stats means an order that ends the tenancy. Many of those orders still let the tenant keep the home by paying, so describe them as applications decided, not evictions carried out.
