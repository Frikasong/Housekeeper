"""
Turn extracted LTB records (JSONL from ltb_fetch.py) into the numbers that
Housekeeper and Ratio show.

    python ltb_stats.py ltb_records.jsonl --out ltb_stats.json
    python build_guidance.py --stats ltb_stats.json --keep-examples "../01.local app version/ltb_guidance.json"

Output sections
  by_case_type   counts per case type (N4, N5, N12, T2, T6) for Housekeeper
  flow_N4        the L1 decision tree: how many orders take each branch
  filers         corporate landlords with at least --min-filings eviction
                 applications. Individual landlords and tenants are never
                 listed.
  representation how often each side had a representative, overall

Counts describe orders as published. "eviction" means an order that
terminates the tenancy; many such orders still let the tenant void it by paying.
"""
import argparse
import collections
import json

CASE_TYPE_OF_GROUND = {
    "arrears_N4": "N4",
    "interference_N5": "N5",
    "damage_N5": "N5",
    "own_use_N12": "N12",
}


def case_types(rec):
    out = set()
    for g in rec.get("grounds") or []:
        if g in CASE_TYPE_OF_GROUND:
            out.add(CASE_TYPE_OF_GROUND[g])
    for t in rec.get("tenant_app_types") or []:
        if t in ("T2", "T6"):
            out.add(t)
    return out


def pct(part, whole):
    return round(100 * part / whole, 1) if whole else None


def summarize(recs):
    n = len(recs)
    buckets = collections.Counter(r.get("outcome_bucket") or "unclear" for r in recs)
    attended = [r for r in recs if r.get("tenant_attended") is True]
    absent = [r for r in recs if r.get("tenant_attended") is False]
    plan_req = [r for r in recs if r.get("payment_plan_requested")]
    plan_rej = [r for r in plan_req if r.get("payment_plan_rejected")]
    kept = [r for r in attended if r.get("outcome_bucket") in ("kept_tenancy_with_plan", "eviction_refused", "eviction_delayed")]

    def evidence_rates(group):
        c = collections.Counter(k for r in group for k in r.get("evidence") or [])
        return {k: pct(v, len(group)) for k, v in c.most_common()}

    return {
        "orders": n,
        "outcomes": {k: {"count": v, "pct": pct(v, n)} for k, v in buckets.most_common()},
        "tenant_attended_pct": pct(len(attended), len([r for r in recs if r.get("tenant_attended") is not None])),
        "outcomes_when_tenant_absent": {k: pct(v, len(absent)) for k, v in collections.Counter(r.get("outcome_bucket") for r in absent).most_common()},
        "outcomes_when_tenant_attended": {k: pct(v, len(attended)) for k, v in collections.Counter(r.get("outcome_bucket") for r in attended).most_common()},
        "payment_plan": {
            "requested": len(plan_req),
            "rejected": len(plan_rej),
            "rejected_without_documents_pct": pct(sum(1 for r in plan_rej if r.get("no_documentary_evidence")), len(plan_rej)),
        },
        "duty_counsel_spoke_pct": pct(sum(1 for r in recs if r.get("tenant_duty_counsel") is True),
                                      sum(1 for r in recs if r.get("tenant_duty_counsel") is not None)),
        "evidence_when_tenancy_kept": evidence_rates(kept),
        "evidence_missing_mentions": dict(collections.Counter(k for r in recs for k in r.get("evidence_missing") or []).most_common()),
    }


def flow_n4(recs):
    l1 = [r for r in recs if "arrears_N4" in (r.get("grounds") or []) and not r.get("review_order")]
    consent = [r for r in l1 if r.get("consent")]
    heard = [r for r in l1 if not r.get("consent")]
    att = [r for r in heard if r.get("tenant_attended") is True]
    absent = [r for r in heard if r.get("tenant_attended") is False]
    count = lambda group: dict(collections.Counter(r.get("outcome_bucket") or "unclear" for r in group).most_common())
    return {
        "total": len(l1),
        "consent": {"n": len(consent), "outcomes": count(consent)},
        "heard": {
            "n": len(heard),
            "tenant_absent": {"n": len(absent), "outcomes": count(absent)},
            "tenant_attended": {
                "n": len(att),
                "s82_raised": sum(1 for r in att if r.get("s82_raised")),
                "s82_barred": sum(1 for r in att if r.get("s82_barred")),
                "s83_3_argued": sum(1 for r in att if r.get("s83_3_argued")),
                "s83_3_refusal": sum(1 for r in att if r.get("s83_3_refusal")),
                "outcomes": count(att),
            },
        },
    }


def norm_landlord(name):
    import re
    n = (name or "").upper()
    n = re.sub(r"\bC/O\b.*$", "", n)
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    n = re.sub(r"\b(THE|INC|LTD|LIMITED|CORP|CORPORATION|LP|L P|CO)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def filers(recs, min_filings):
    evictions = [r for r in recs if r.get("side") == "landlord" and r.get("landlord_corporate")]
    groups = collections.defaultdict(list)
    for r in evictions:
        groups[norm_landlord(r.get("landlord"))].append(r)
    rows = []
    for key, rs in groups.items():
        if len(rs) < min_filings or not key:
            continue
        names = collections.Counter(r.get("landlord") for r in rs)
        rows.append({
            "landlord": names.most_common(1)[0][0],
            "applications_decided": len(rs),
            "by_ground": dict(collections.Counter(g for r in rs for g in r.get("grounds") or []).most_common()),
            "outcomes": dict(collections.Counter(r.get("outcome_bucket") or "unclear" for r in rs).most_common()),
        })
    return sorted(rows, key=lambda x: -x["applications_decided"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("records")
    ap.add_argument("--out", default="ltb_stats.json")
    ap.add_argument("--min-filings", type=int, default=25)
    a = ap.parse_args()
    recs = [json.loads(line) for line in open(a.records, encoding="utf-8") if line.strip()]
    dates = sorted(r["date"] for r in recs if r.get("date"))
    by_type = collections.defaultdict(list)
    for r in recs:
        for ct in case_types(r):
            by_type[ct].append(r)
    out = {
        "orders": len(recs),
        "date_range": [dates[0], dates[-1]] if dates else None,
        "by_case_type": {ct: summarize(rs) for ct, rs in sorted(by_type.items())},
        "flow_N4": flow_n4(recs),
        "filers": filers(recs, a.min_filings),
        "representation": {
            "landlord": dict(collections.Counter(r.get("landlord_rep") or "none_named" for r in recs).most_common()),
            "tenant": dict(collections.Counter(r.get("tenant_rep") or "none_named" for r in recs).most_common()),
        },
        "note": "Counts of published LTB orders, extracted by rule from order text. Not legal advice.",
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("wrote", a.out, "from", len(recs), "orders")


if __name__ == "__main__":
    main()
