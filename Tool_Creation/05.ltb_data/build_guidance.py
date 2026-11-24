"""
Build ltb_guidance.json: the evidence checklist Housekeeper shows tenants.

Each case type has a short list of things to prepare. Every item says why it
matters (from the Residential Tenancies Act and how LTB orders treat it) and
points to real LTB orders where that point decided something.

Inputs
  --samples DIR   A2AJ search results saved as JSON (one file per topic; each a
                  list of {citation_en, citation2_en, document_date_en, url_en,
                  snippet}). Used to pick real examples.
  --stats FILE    Optional ltb_stats.json from ltb_stats.py. When given, each
                  case type also carries counts from the full dataset.
Output
  ltb_guidance.json (default: ../01.local app version/ltb_guidance.json)

Examples show the LTB file number and date only, never party names, and the
excerpt is skipped when it names a person in full.
"""
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "01.local app version", "ltb_guidance.json")

# ─── checklist content ────────────────────────────────────────────────────────
# `source` = sample file that holds real examples; `match` = regex an excerpt
# must contain to be used as an example of this item.

GUIDANCE = {
    "N4": {
        "label": "N4 / L1 – Landlord says rent is owed",
        "board_decides": [
            "Was the N4 notice valid, and did you pay everything owing before its termination date? Paying in full by that date voids the notice.",
            "How much is owed, including rent that came due after the application was filed.",
            "Under section 83, whether it would be unfair to evict you: refuse the eviction, delay it, or make it conditional on a payment plan.",
        ],
        "items": [
            {
                "id": "proof_of_payments",
                "tab_name": "Rent Payments Made",
                "label": "Proof of every payment you made",
                "why": "The Board works out the arrears from both sides' records. E-transfer confirmations, receipts and bank statements let you challenge the landlord's ledger.",
                "documents": ["E-transfer confirmations", "Rent receipts", "Bank statements showing rent paid"],
                "evidence_key": "bank_records",
            },
            {
                "id": "income_and_budget",
                "tab_name": "Income and Monthly Budget",
                "label": "Proof of income and expenses, if you will ask for a payment plan",
                "why": "Members often refuse a payment plan when the tenant has no documents showing it is affordable. Pay stubs, benefit statements and a simple monthly budget make the plan believable.",
                "documents": ["Pay stubs or an employment letter", "ODSP / Ontario Works / CPP / EI statements", "Bank statements", "A monthly budget (Housekeeper can build one)"],
                "evidence_key": "income_proof",
                "source": "documentary_evidence_payment_plan",
                "match": r"documentary evidence|payment plan is not|corroborating",
            },
            {
                "id": "household_circumstances",
                "tab_name": "Household Circumstances",
                "label": "Your household circumstances (section 83)",
                "why": "Children, disability or health issues, benefits income, how long you have lived there, and how hard it is to find another home can lead the Board to delay or refuse an eviction. Documents make these facts easier to accept.",
                "documents": ["Medical or disability letters", "Proof of benefits", "Records of your housing search", "School or childcare information"],
                "evidence_key": "benefit_records",
                "source": "ow_odsp_relief",
                "match": r"ODSP|Ontario Works|children|disab",
            },
            {
                "id": "repair_issues_s82",
                "tab_name": "Repair Issues (s.82) and Notice Given",
                "label": "Repair problems you want to raise (section 82) – give notice in writing first",
                "why": "In a rent arrears hearing you can raise the landlord's maintenance failures, but only if you gave the landlord and the LTB a written description of each issue and copies of your evidence before the hearing. The Notice of Hearing package says at least 7 days before. Without that, members often refuse to hear the issues.",
                "documents": ["Written description of each issue (Housekeeper can draft it)", "Dated photos or videos", "Your written repair requests to the landlord", "Proof you sent the disclosure, with the date"],
                "evidence_key": "written_requests",
                "source": "s82_rules",
                "match": r"section 82|Rule 19",
            },
            {
                "id": "serious_breach_s83_3",
                "tab_name": "Landlord's Serious Breach – Evidence",
                "label": "If the landlord is in serious breach (section 83(3)(a)): corroborating evidence",
                "why": "If the landlord is in serious breach of their obligations, the Board must refuse the eviction. Members want evidence beyond your own testimony: photos, technician or inspection reports, utility records, and messages to the landlord.",
                "documents": ["Photos and videos with dates", "Municipal property standards or inspection reports", "Technician or contractor reports", "Utility records", "Messages reporting the problem"],
                "evidence_key": "inspection_reports",
                "source": "s83_3_serious_breach",
                "match": r"83\(3\)",
            },
            {
                "id": "attend_and_get_advice",
                "tab_name": None,
                "label": "Attend the hearing, and speak to Tenant Duty Counsel first",
                "why": "If you do not attend, the hearing goes ahead on the landlord's evidence alone. Tenant Duty Counsel gives free legal advice to tenants on the day of the hearing.",
                "documents": [],
                "source": "tenant_duty_counsel",
                "match": r"Tenant Duty Counsel",
            },
        ],
    },
    "N5": {
        "label": "N5 / L2 – Landlord alleges interference or damage",
        "board_decides": [
            "Did the conduct described in the N5 happen, and was it serious enough?",
            "For a first N5: did you void it by stopping the conduct (or paying for or repairing the damage) within 7 days?",
            "Under section 83, whether eviction would be unfair in your circumstances.",
        ],
        "items": [
            {
                "id": "your_account",
                "tab_name": "Response to N5 Allegations",
                "label": "Your account of each incident in the N5",
                "why": "The landlord must prove the conduct. A dated account of each incident, with messages or witness names, lets you dispute what did not happen.",
                "documents": ["A dated timeline of each incident", "Messages with the landlord or neighbours", "Names of witnesses who can attend"],
                "evidence_key": "written_requests",
                "source": "n5",
                "match": r"testif|credib|evidence|witness",
            },
            {
                "id": "stopped_or_repaired",
                "tab_name": "Proof the Conduct Stopped / Damage Repaired",
                "label": "Proof you stopped the conduct or fixed the damage in time",
                "why": "A first N5 is void if the tenant stops the conduct, or pays for or repairs the damage, within 7 days.",
                "documents": ["Dated photos after the repair", "Receipts", "Messages to the landlord confirming the issue stopped"],
                "evidence_key": "photos_video",
            },
            {
                "id": "household_circumstances",
                "tab_name": "Household Circumstances",
                "label": "Your household circumstances (section 83)",
                "why": "The Board considers whether evicting you would be unfair, for example because of children, disability or how long you have lived there.",
                "documents": ["Medical or disability letters", "Proof of benefits", "Records of your housing search"],
                "evidence_key": "benefit_records",
            },
        ],
    },
    "N12": {
        "label": "N12 / L2 – Landlord or family wants to move in",
        "board_decides": [
            "Does the landlord (or a family member, or a purchaser) in good faith need the unit to live in for at least one year?",
            "Was the tenant paid the compensation the Act requires (one month's rent) by the termination date?",
            "Under section 83, whether to delay or refuse the eviction.",
        ],
        "items": [
            {
                "id": "good_faith",
                "tab_name": "Evidence on the Landlord's Good Faith",
                "label": "Evidence that questions the landlord's good faith",
                "why": "The Board looks at whether the landlord genuinely intends to move in. Re-listing the unit, demands for a rent increase or earlier attempts to end the tenancy can cast doubt on that.",
                "documents": ["Online listings of the unit", "Messages about raising the rent", "Earlier notices or applications"],
                "evidence_key": "written_requests",
                "source": "n12",
                "match": r"good faith|genuine|intends? to (move|reside|live)",
            },
            {
                "id": "compensation",
                "tab_name": "N12 Compensation",
                "label": "Whether you received one month's rent as compensation",
                "why": "An N12 eviction order requires the compensation to have been paid by the termination date.",
                "documents": ["Bank statement or receipt showing the payment, or its absence"],
                "evidence_key": "bank_records",
            },
            {
                "id": "time_to_move",
                "tab_name": "Household Circumstances",
                "label": "What you need in order to move",
                "why": "Members often delay N12 evictions to give a family time to find housing. Explain your situation and bring proof of your housing search.",
                "documents": ["Records of your housing search", "School or medical constraints"],
                "evidence_key": "benefit_records",
                "source": "n12",
                "match": r"postpone|delay",
            },
        ],
    },
    "T2": {
        "label": "T2 – Tenant's rights (interference, harassment, illegal entry)",
        "board_decides": [
            "Did the landlord do what you allege, under section 29 of the Act?",
            "If so, what remedy is fair: rent abatement, out-of-pocket costs, an order to stop, or a fine.",
        ],
        "items": [
            {
                "id": "incident_log",
                "tab_name": "Incident Log",
                "label": "A dated log of each incident",
                "why": "T2 applications turn on specific incidents. Members weigh dates, details and whether the record was made at the time.",
                "documents": ["Timeline with date, time, what happened, who was there"],
                "evidence_key": "written_requests",
                "source": "t2",
                "match": r"incident|testif|text messages|emails|video|credib",
            },
            {
                "id": "communications",
                "tab_name": "Communications with Landlord",
                "label": "Messages, notices and letters",
                "why": "Written communication shows what the landlord said and did, and when.",
                "documents": ["Texts and emails", "Notices of entry (or the lack of them)", "Letters"],
                "evidence_key": "written_requests",
            },
            {
                "id": "losses",
                "tab_name": "Losses and Expenses",
                "label": "What it cost you",
                "why": "Abatements and costs need a number. Receipts and a short calculation help the member award an amount.",
                "documents": ["Receipts", "A calculation of the abatement you are asking for"],
                "evidence_key": "bank_records",
            },
        ],
    },
    "T6": {
        "label": "T6 – Maintenance and repairs",
        "board_decides": [
            "Did the landlord fail to meet maintenance obligations or health, safety and housing standards?",
            "Did the landlord know about the problem, and how long did it last?",
            "What remedy fits: rent abatement, repairs ordered, costs.",
        ],
        "items": [
            {
                "id": "notice_to_landlord",
                "tab_name": "Repair Requests to Landlord",
                "label": "Proof you told the landlord about each problem",
                "why": "Members look at when the landlord knew. Dated written requests are the clearest proof.",
                "documents": ["Emails, texts, letters or work-order requests, with dates"],
                "evidence_key": "written_requests",
                "source": "t6",
                "match": r"notif|complain|aware|knew|reported|work order",
            },
            {
                "id": "condition_evidence",
                "tab_name": "Photos of Unit Conditions",
                "label": "Photos, videos and reports showing the problem",
                "why": "Dated photos and inspection reports (for example a municipal property standards order) show what the problem was and how long it lasted.",
                "documents": ["Dated photos or videos", "Municipal inspection reports", "Technician reports"],
                "evidence_key": "photos_video",
            },
            {
                "id": "abatement",
                "tab_name": "Abatement and Costs",
                "label": "How much rent abatement you are asking for, and why",
                "why": "Abatement is usually a share of rent for the period the problem lasted. Show the period, the share you ask for, and any receipts.",
                "documents": ["A calculation", "Receipts for repairs or replacement items"],
                "evidence_key": "bank_records",
                "source": "t6",
                "match": r"abatement",
            },
        ],
    },
}

# ─── example picking ──────────────────────────────────────────────────────────

FULL_NAME = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]{2,}\b")
ALLOWED_PHRASES = {"Tenant Duty", "Duty Counsel", "Landlord Tenant", "Residential Tenancies", "Tenancies Act",
                   "Ontario Works", "Board Member", "Rules Of", "Dispute Resolution", "Resolution Officer",
                   "Hearing Officer", "Ontario Disability", "Disability Support", "Support Program",
                   "Tenant Board", "Landlord And", "The Tenant", "The Landlord", "The Board", "The Act",
                   "The Member", "In June", "In July", "In May"}


def _clean(snippet):
    s = re.sub(r"</?em>", "", snippet or "")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("’", "'")
    return s


def _names_person(text):
    for m in FULL_NAME.finditer(text):
        if m.group(0) not in ALLOWED_PHRASES and not m.group(0).startswith(("The ", "In ", "On ", "As ", "I ")):
            return True
    return False


def pick_examples(rows, pattern, k=2):
    out, seen = [], set()
    for r in rows:
        ex = _clean(r.get("snippet"))
        fn = r.get("citation2_en") or r.get("citation_en")
        if not ex or fn in seen or len(ex) < 60 or len(ex) > 320:
            continue
        if not re.search(pattern, ex, re.I) or _names_person(ex):
            continue
        seen.add(fn)
        out.append({
            "file_number": fn,
            "citation": r.get("citation_en"),
            "date": (r.get("document_date_en") or "")[:10],
            "url": r.get("url_en"),
            "excerpt": ex,
        })
        if len(out) == k:
            break
    return out


def build(samples_dir=None, stats=None):
    guidance = json.loads(json.dumps(GUIDANCE))  # deep copy
    for ct, block in guidance.items():
        for item in block["items"]:
            src = item.pop("source", None)
            pat = item.pop("match", ".")
            item["examples"] = []
            if samples_dir and src:
                path = os.path.join(samples_dir, src + ".json")
                if os.path.exists(path):
                    with open(path, encoding="utf-8") as f:
                        item["examples"] = pick_examples(json.load(f), pat)
        if stats and ct in stats:
            block["stats"] = stats[ct]
    return {
        "version": 2,
        "source": "LTB orders from A2AJ Canadian Legal Data (Open Government Licence – Ontario). Not legal advice.",
        "case_types": guidance,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default=None)
    ap.add_argument("--stats", default=None)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--keep-examples", default=None,
                    help="existing guidance file whose examples are kept when --samples is not given")
    a = ap.parse_args()
    stats = None
    if a.stats:
        with open(a.stats, encoding="utf-8") as f:
            stats = json.load(f).get("by_case_type")
    g = build(a.samples, stats)
    if not a.samples and a.keep_examples and os.path.exists(a.keep_examples):
        old = json.load(open(a.keep_examples, encoding="utf-8"))
        for ct, block in g["case_types"].items():
            old_items = {i["id"]: i for i in old.get("case_types", {}).get(ct, {}).get("items", [])}
            for item in block["items"]:
                item["examples"] = old_items.get(item["id"], {}).get("examples", [])
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(g, f, indent=2, ensure_ascii=False)
    print("wrote", os.path.abspath(a.out))


if __name__ == "__main__":
    main()
