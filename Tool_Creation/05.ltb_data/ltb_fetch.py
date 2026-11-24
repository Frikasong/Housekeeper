"""
Download LTB orders from A2AJ and run the extractor over them.

Two sources:

  hf   Hugging Face bulk dataset (recommended for the full ~56,000 orders).
         pip install datasets pandas
         python ltb_fetch.py hf --out ltb_records.jsonl

  api  A2AJ REST API, for a smaller targeted pull (e.g. one month).
         python ltb_fetch.py api --start 2026-07-01 --end 2026-07-31 \
             --query '"did not pay the rent"' --out july_l1.jsonl
       The API returns at most --size results per query, so this mode walks
       one day at a time. Days with more matches than --size are flagged in
       the log as truncated: use hf mode for complete counts.

Each output line is one order: the extractor's fields plus citation, date and
URL. Full text is NOT written unless --keep-text is passed, to keep the file
small and avoid copying names into derived data.
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request

import ltb_extract

API = "https://api.a2aj.ca"
UA = {"User-Agent": "Housekeeper-LTB-research/1.0 (+https://github.com/Frikasong/Housekeeper)"}


def _get(path, params, retries=3):
    url = API + path + "?" + urllib.parse.urlencode(params)
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - network errors vary
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))
            print("retry", path, e, file=sys.stderr)


def _record(text, meta, keep_text):
    rec = ltb_extract.extract(text, meta)
    if keep_text:
        rec["text"] = text
    return rec


def from_hf(out, keep_text=False, limit=None):
    from datasets import load_dataset  # imported here so api mode needs no extra deps
    ds = load_dataset("a2aj/canadian-case-law", data_dir="ONLTB", split="train")
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for row in ds:
            text = row.get("unofficial_text_en") or ""
            if not text:
                continue
            meta = {
                "citation": row.get("citation_en"),
                "citation2": row.get("citation2_en"),
                "date": (row.get("document_date_en") or "")[:10] if isinstance(row.get("document_date_en"), str) else str(row.get("document_date_en"))[:10],
                "url": row.get("url_en"),
            }
            f.write(json.dumps(_record(text, meta, keep_text), ensure_ascii=False) + "\n")
            n += 1
            if limit and n >= limit:
                break
    print("wrote", n, "orders to", out)


def from_api(out, start, end, query, size=50, keep_text=False, pause=0.5):
    day = dt.date.fromisoformat(start)
    last = dt.date.fromisoformat(end)
    seen, n, truncated = set(), 0, []
    with open(out, "w", encoding="utf-8") as f:
        while day <= last:
            ds = day.isoformat()
            res = _get("/search", {"query": query, "doc_type": "cases", "dataset": "ONLTB",
                                   "size": size, "start_date": ds, "end_date": ds,
                                   "search_type": "full_text"})
            hits = res.get("results", [])
            if len(hits) >= size:
                truncated.append(ds)
            for h in hits:
                cit = h.get("citation_en")
                if not cit or cit in seen:
                    continue
                seen.add(cit)
                doc = _get("/fetch", {"citation": cit, "doc_type": "cases"})
                docs = doc.get("results") or [doc]
                text = (docs[0] or {}).get("unofficial_text_en") or ""
                meta = {"citation": cit, "citation2": h.get("citation2_en"),
                        "date": (h.get("document_date_en") or "")[:10], "url": h.get("url_en")}
                f.write(json.dumps(_record(text, meta, keep_text), ensure_ascii=False) + "\n")
                n += 1
                time.sleep(pause)
            day += dt.timedelta(days=1)
    print("wrote", n, "orders to", out)
    if truncated:
        print("days capped at", size, "results (incomplete):", ", ".join(truncated))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    h = sub.add_parser("hf")
    h.add_argument("--out", default="ltb_records.jsonl")
    h.add_argument("--limit", type=int)
    h.add_argument("--keep-text", action="store_true")
    a = sub.add_parser("api")
    a.add_argument("--start", required=True)
    a.add_argument("--end", required=True)
    a.add_argument("--query", default='"Residential Tenancies Act"')
    a.add_argument("--size", type=int, default=50)
    a.add_argument("--out", default="ltb_records.jsonl")
    a.add_argument("--keep-text", action="store_true")
    args = ap.parse_args()
    if args.mode == "hf":
        from_hf(args.out, args.keep_text, args.limit)
    else:
        from_api(args.out, args.start, args.end, args.query, args.size, args.keep_text)


if __name__ == "__main__":
    main()
