"""
Rule-based extractor for Ontario Landlord and Tenant Board (LTB) orders.

LTB orders are written from fixed templates, so most procedural facts sit in
predictable sentences ("The Tenant did not void the notice...", "it would be
unfair to grant relief from eviction..."). This module turns the text of one
order into a flat dict of fields that the stats scripts, Housekeeper and Ratio
can all reuse.

Nothing here calls the network. Input is plain text (A2AJ's `unofficial_text_en`).

Usage:
    from ltb_extract import extract
    record = extract(text, meta={"citation": "...", "url": "..."})

Every field is a best-effort reading of the text. `None` means "the order does
not say", which is different from False ("the order says no").
"""

import re

# ─── helpers ──────────────────────────────────────────────────────────────────

def _norm(text):
    """Collapse whitespace and straighten quotes so patterns stay simple."""
    t = text.replace("’", "'").replace("‘", "'")
    t = t.replace("“", '"').replace("”", '"')
    t = t.replace("–", "-").replace("—", "-")
    return re.sub(r"[ \t]+", " ", t)


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _any(patterns, text):
    return any(re.search(p, text, re.I) for p in patterns)


def _money(s):
    try:
        return float(s.replace(",", ""))
    except (AttributeError, ValueError):
        return None


# ─── application type ─────────────────────────────────────────────────────────

# Ground of a landlord's eviction application, read from the
# "applied for an order to terminate the tenancy ... because ..." sentence.
GROUNDS = [
    ("arrears_N4",     r"did not pay the rent (that the Tenant owes|owed)|non-payment of rent"),
    ("persistent_late_N8", r"persistently fail(ed)? to pay the rent on the date it was due"),
    ("interference_N5", r"substantially interfered with the reasonable enjoyment"),
    ("damage_N5",      r"wilfully or negligently caused undue damage"),
    ("own_use_N12",    r"own (residential )?(use|occupation)|requires possession of the rental unit for the purpose of residential occupation"),
    ("renovation_N13", r"demolish|repairs or renovations so extensive|convert the rental unit"),
    ("illegal_act_N6", r"illegal act|illegal (business|trade|occupation)"),
    ("safety_N7",      r"seriously impaired the safety"),
    ("breach_of_order_s78", r"section 78|failed to meet a condition (specified )?in (the|an) (order|agreement)"),
]

TENANT_APP_PATTERNS = [
    ("T2", r"\bT2\b|harassed, obstructed|interfered with (the )?(Tenant's|their) reasonable enjoyment"),
    ("T6", r"\bT6\b|maintenance obligations|health, safety, housing or maintenance standards"),
    ("T1", r"\bT1\b|illegal (charge|rent|deposit)|money (the|they) owe"),
    ("T5", r"\bT5\b|bad faith"),
]


def application_side(file_number):
    m = re.match(r"LTB-([LT])-", file_number or "")
    return {"L": "landlord", "T": "tenant"}.get(m.group(1)) if m else None


def landlord_grounds(flat):
    m = re.search(r"applied for an order to terminate the tenancy(.{0,600})", flat, re.I)
    window = m.group(1) if m else flat[:3000]
    found = [name for name, pat in GROUNDS if re.search(pat, window, re.I)]
    return found


def tenant_application_types(flat):
    head = flat[:4000]
    return [name for name, pat in TENANT_APP_PATTERNS if re.search(pat, head, re.I)]


# ─── parties, hearing, attendance ─────────────────────────────────────────────

def parties(text):
    """Return (landlord_lines, tenant_lines) from the 'Between: ... And ...' block."""
    m = re.search(r"Between:\s*(.+?)\n\s*Landlords?\s*(?:\n|And)\s*(?:And\s*)?(.+?)\n\s*Tenants?\b",
                  text, re.S | re.I)
    if not m:
        return [], []
    split = lambda s: [ln.strip() for ln in s.split("\n") if ln.strip() and ln.strip().lower() != "and"]
    return split(m.group(1)), split(m.group(2))


CORPORATE_MARKERS = r"\b(inc|ltd|limited|corp|corporation|lp|l\.p|partnership|reit|trust|holdings|properties|property|management|housing|realty|rentals?|rents|apartments|investments|developments|co-?op|cooperative|non-profit|homes|living|residences|services|group|company|capreit|minto|metcap|greenwin|homestead|skyline|quadreal|bentall|board|county|counties|city|region|municipality|clc|condominium|tcc|tchc)\b|\d{6,}"


def is_corporate(name):
    return bool(name) and bool(re.search(CORPORATE_MARKERS, name, re.I))


def hearing_mode(flat):
    if re.search(r"video ?conference|zoom", flat, re.I):
        return "video"
    if re.search(r"in[- ]person", flat, re.I):
        return "in_person"
    if re.search(r"written hearing|in writing", flat, re.I):
        return "written"
    if re.search(r"by telephone|teleconference", flat, re.I):
        return "phone"
    return None


TENANT_ABSENT = [
    r"Tenants?\s+(was|were)\s+not\s+present",
    r"Only the Landlord('s)?( (legal )?representative[^.]{0,60})? attended",
    r"Neither Tenant attended",
    r"Tenants?\s+did not attend",
    r"no one (appeared|attended) for the Tenant",
    r"hearing proceeded with only the Landlord",
    r"Tenants? (was|were) not in attendance",
]
TENANT_PRESENT = [
    r"and the Tenants?\b[^.]{0,80}\battended",
    r"the Tenants?\b[^.]{0,60}\battended the hearing",
    r"Tenant'?s? (legal )?representative[^.]{0,80}attended",
    r"the Tenants? testified",
    r"Tenants?'?s? legal representative",
    r"parties elected to participate in (LTB )?(facilitated )?mediation",
    r"parties (had )?reached an agreement",
]


def tenant_attended(flat):
    if _any(TENANT_ABSENT, flat):
        return False
    if _any(TENANT_PRESENT, flat):
        return True
    return None


def landlord_rep(flat):
    if re.search(r"Landlord'?s'? (legal )?representative[^.]{0,80}licensed paralegal|Landlord'?s'?[^.]{0,40}paralegal", flat, re.I):
        return "paralegal"
    if re.search(r"Landlord'?s'? (legal representative|lawyer|counsel)", flat, re.I):
        return "legal_rep"
    if re.search(r"Landlord'?s'? (representative|agent)", flat, re.I):
        return "agent"
    return None


def tenant_rep(flat):
    if re.search(r"Tenant'?s'? (legal representative|lawyer|counsel|paralegal)", flat, re.I):
        return "legal_rep"
    if re.search(r"Tenant'?s'? (representative|agent)", flat, re.I):
        return "agent"
    return None


def duty_counsel(flat):
    """True = the tenant spoke to Tenant Duty Counsel, False = declined or did not."""
    if re.search(r"(did not|didn't|declined( the opportunity)? to|chose not to) (utilize|use|consult|speak|meet)[^.]{0,40}Tenant Duty Counsel", flat, re.I):
        return False
    if re.search(r"(met with|consulted( with)?|spoke (with|to)|did speak (with|to)|was able to meet with|utilized the services of|assisted by|advice from)[^.]{0,30}Tenant Duty Counsel", flat, re.I):
        return True
    return None


# ─── substance ────────────────────────────────────────────────────────────────

def notice_findings(flat):
    valid = None
    if re.search(r"served the Tenants? with a valid Notice", flat, re.I):
        valid = True
    elif re.search(r"(notice|N4|N5|N12)[^.]{0,60}(was|is) (invalid|defective|void)", flat, re.I):
        valid = False
    voided = None
    if re.search(r"did not void the (N\d+ )?notice", flat, re.I):
        voided = False
    elif re.search(r"(voided|void(ed)?) the (N\d+ )?notice by paying", flat, re.I) and not re.search(r"did not void", flat, re.I):
        voided = True
    return valid, voided


def s82(flat):
    raised = bool(re.search(r"section 82|s\. ?82|subsection 82", flat, re.I)) or None
    barred = None
    if raised:
        if re.search(r"(did not permit|not (be )?permitted|was not allowed|refused to allow)[^.]{0,80}section 82|not complied with the (statutory )?disclosure|failed to (comply with|provide)[^.]{0,40}disclos|Rule 19\.4", flat, re.I):
            barred = True
        elif re.search(r"(considered|addressed|determined)[^.]{0,60}section 82 issues|abatement (of|is granted)", flat, re.I):
            barred = False
    return raised, barred


def s83_3(flat):
    argued = bool(re.search(r"83\(3\)", flat)) or None
    mandatory_refusal = None
    if argued:
        if re.search(r"(must|shall) (mandatorily )?refuse[^.]{0,80}(eviction|application)[^.]{0,40}(and|therefore|accordingly)|application is (refused|denied) (under|pursuant to) (s\.|section|subsection) ?83\(3\)", flat, re.I):
            mandatory_refusal = True
        elif re.search(r"insufficient evidence|not (satisfied|persuaded)[^.]{0,80}(serious breach|83\(3\))|does not support|failed to lead any (documentary|independent)", flat, re.I):
            mandatory_refusal = False
    return argued, mandatory_refusal


OUTCOME_RULES = [
    # order matters: first match wins
    ("withdrawn",          r"application (is|was) withdrawn|withdrew the [^.]{0,40}application|applications having been withdrawn"),
    ("dismissed",          r"application is dismissed|applications? (is|are) dismissed"),
    ("mandatory_refusal",  r"(refuse|refused|deny|denied) (to grant )?the application (pursuant to|under) (s\.|section|subsection) ?83\(3\)"),
    ("consent_termination", r"on consent[^\n]{0,40}\n?[\s\S]{0,1200}?(tenancy[^.]{0,60}is terminated|must vacate|must move out)"),
    ("consent_payment_plan", r"(ordered on consent|on consent, it is ordered|order on consent)[\s\S]{0,2500}?(in accordance with the following schedule|payment plan|section 78)"),
    ("consent_other",      r"ordered on consent|on consent, it is ordered|order on consent"),
    ("vacated",            r"terminated as of [^.]{0,60}(moved out|vacated)|date the Tenant moved out"),
    ("conditional_relief", r"would not be unfair to grant relief from eviction subject to (the )?conditions"),
    ("postponed",          r"(would not be unfair|is not unfair|would be fair|reasonable in the circumstances)( in the circumstances?)? to (delay or )?postpone the eviction|postpone the eviction (until|to) [A-Z][a-z]+ \d"),
    ("relief_granted",     r"would be unfair to (evict|terminate)|(refuse|refused) to (grant the application|evict)|application for (an )?eviction is (refused|denied)"),
    ("eviction_ordered",   r"would be unfair to grant relief from eviction|tenancy between the Landlord and the Tenants? is terminated"),
]


def outcome(flat):
    for name, pat in OUTCOME_RULES:
        if re.search(pat, flat, re.I):
            return name
    return None


# Plain-language buckets that the tools show to tenants.
OUTCOME_BUCKET = {
    "eviction_ordered": "eviction",
    "consent_termination": "eviction",
    "vacated": "already_moved",
    "conditional_relief": "kept_tenancy_with_plan",
    "consent_payment_plan": "kept_tenancy_with_plan",
    "postponed": "eviction_delayed",
    "relief_granted": "eviction_refused",
    "mandatory_refusal": "eviction_refused",
    "dismissed": "application_dismissed",
    "withdrawn": "withdrawn",
    "consent_other": "settled_other",
}


# ─── amounts ──────────────────────────────────────────────────────────────────

def amounts(flat):
    def grab(pat):
        m = re.search(pat, flat, re.I)
        return _money(m.group(1)) if m else None
    return {
        "monthly_rent": grab(r"lawful rent is \$([\d,]+\.?\d*)"),
        "arrears": grab(r"rent arrears owing to [^$]{0,40}(?:are|is) \$([\d,]+\.?\d*)"),
        "paid_since_filing": grab(r"paid \$([\d,]+\.?\d*) to the Landlord since the application"),
        "no_payments_since_filing": bool(re.search(r"has not made any payments since the application", flat, re.I)),
    }


# ─── evidence and circumstances ───────────────────────────────────────────────

# What evidence an order mentions. Keys are the checklist ids used by
# Housekeeper's guidance file, so stats line up with what the tool shows.
EVIDENCE_PATTERNS = {
    "income_proof":      r"pay ?stubs?|proof of (income|employment)|employment letter|income (tax )?statements?|notice of assessment|T4",
    "benefit_records":   r"\bODSP\b|Ontario Works|\bOW\b|Ontario Disability Support|benefit (statement|letter)s?|CPP|Employment Insurance|\bEI\b",
    "bank_records":      r"bank statements?|e-?transfer (records|history|confirmations?)|transaction (history|records)",
    "rent_ledger":       r"(rent )?ledger|receipts? for rent|rent receipts?",
    "photos_video":      r"photo(graph)?s?\b|pictures\b|video (recording|footage|evidence|clip)s?|videos\b",
    "written_requests":  r"(written|email|text) (requests?|complaints?|messages?)|maintenance requests?|work orders?|emails?|text messages?|letters?|communications? with the Landlord",
    "inspection_reports": r"inspection reports?|property standards|by-?law (officer|enforcement)|fire (department|inspector)|public health|technician reports?",
    "medical":           r"medical (note|letter|records?|documentation)|doctor'?s (note|letter)|physician",
    "lease":             r"lease|tenancy agreement|rental agreement",
    "witness":           r"witness(es)? testified|testimony of [A-Z]|called [^.]{0,30} as a witness",
}

NO_DOCS = r"no documentary evidence|did not (submit|file|provide) (any )?documentary evidence|has not provided any evidence to support|lack of corroborating evidence|(n)?either [^.]{0,40} submitted any documentary evidence|did not (provide|file|submit|produce|lead) any (documentary|supporting|corroborating)|led no documentary|without (any )?(supporting|documentary) (evidence|documents)|failed to lead any documentary|not provided sufficient documentary evidence|no evidence (was|has been) (provided|filed) to (support|corroborate)"

CIRCUMSTANCES = {
    "children":        r"\bchild(ren)?\b|school[- ]aged|\bkids?\b|\bminor\b",
    "disability_health": r"disabilit|medical condition|illness|surgery|hospital|mental health",
    "benefits_income": r"\bODSP\b|Ontario Works|social assistance",
    "job_loss":        r"lost (his|her|their) (job|employment)|laid off|loss of (income|employment)|unemployed",
    "long_tenancy":    r"(lived|resided) in the (rental )?unit (for|since)|tenancy (began|commenced) in (19|200|201)",
    "senior":          r"\bsenior\b|elderly|retire",
}


NEGATED = r"\b(no|not|never|without|failed to|did not|didn't|insufficient|lack(ed|ing)?|absence of|unable to)\b"


def _sentences(flat):
    return re.split(r"(?<=[.;:])\s+(?=[A-Z0-9(])", flat)


PLAN_REQUESTED = r"(proposed|requested|sought|offered)[^.]{0,40}payment plan|payment plan (of \$|proposed by the Tenant)|request for a payment plan"
PLAN_REJECTED = r"payment plan[^.]{0,80}(not (viable|realistic|reasonable|feasible)|no reasonable prospect|inappropriate)|not (satisfied|persuaded|convinced)[^.]{0,100}payment plan|no realistic payment plan"


def evidence_mentions(flat):
    """Split evidence mentions into (provided, missing).

    A mention in a sentence that says the evidence was absent ("led no
    documentary evidence ... such as photographs") counts as missing, so the
    stats do not treat a gap in the record as evidence that was filed.
    """
    provided, missing = set(), set()
    for sent in _sentences(flat):
        neg = re.search(NEGATED, sent, re.I)
        for k, p in EVIDENCE_PATTERNS.items():
            if re.search(p, sent, re.I):
                (missing if neg else provided).add(k)
    return sorted(provided), sorted(missing - provided)


def circumstances(flat):
    return sorted(k for k, p in CIRCUMSTANCES.items() if re.search(p, flat, re.I))


# ─── decision maker ───────────────────────────────────────────────────────────

def decision_maker(text):
    m = re.search(r"\n([A-Z][^\n]{2,60})\n\s*(Member|Vice[- ]Chair|Hearings? Officer|Dispute Resolution Officer)[^\n]*Landlord and Tenant Board", text)
    if not m:
        return None, None
    role = m.group(2).lower().replace(" ", "_").replace("-", "_")
    return m.group(1).strip(), role


# ─── main entry ───────────────────────────────────────────────────────────────

def extract(text, meta=None):
    meta = meta or {}
    t = _norm(text or "")
    flat = _flat(t)

    fn = re.search(r"File Numbers?:\s*(LTB-[LT]-\d{5,6}-\d{2})", flat)
    file_number = fn.group(1) if fn else meta.get("citation2") or meta.get("file_number")

    landlord_lines, _tenant_lines = parties(t)
    landlord = landlord_lines[0] if landlord_lines else None
    valid, voided = notice_findings(flat)
    s82_raised, s82_barred = s82(flat)
    s83_argued, s83_refusal = s83_3(flat)
    oc = outcome(flat)
    name, role = decision_maker(t)

    rec = {
        "file_number": file_number,
        "citation": meta.get("citation"),
        "date": meta.get("date"),
        "url": meta.get("url"),
        "side": application_side(file_number),
        "grounds": landlord_grounds(flat),
        "tenant_app_types": tenant_application_types(flat) if application_side(file_number) == "tenant" else [],
        "review_order": bool(re.search(r"\bReview Order\b|request to review|review of (the|an) order", flat, re.I)),
        "landlord": landlord,
        "landlord_corporate": is_corporate(landlord),
        "hearing_mode": hearing_mode(flat),
        "consent": bool(re.search(r"on consent", flat, re.I)),
        "mediated": bool(re.search(r"mediation|Dispute Resolution Officer", flat, re.I)),
        "tenant_attended": tenant_attended(flat),
        "landlord_rep": landlord_rep(flat),
        "tenant_rep": tenant_rep(flat),
        "tenant_duty_counsel": duty_counsel(flat),
        "notice_valid": valid,
        "notice_voided": voided,
        "tenant_vacated": bool(re.search(r"Tenants? (has |have )?(vacated|moved out)", flat, re.I)),
        "s82_raised": s82_raised,
        "s82_barred": s82_barred,
        "s83_3_argued": s83_argued,
        "s83_3_refusal": s83_refusal,
        "outcome": oc,
        "outcome_bucket": OUTCOME_BUCKET.get(oc),
        "no_documentary_evidence": bool(re.search(NO_DOCS, flat, re.I)),
        "payment_plan_requested": bool(re.search(PLAN_REQUESTED, flat, re.I)),
        "payment_plan_rejected": bool(re.search(PLAN_REJECTED, flat, re.I)),
        "evidence": evidence_mentions(flat)[0],
        "evidence_missing": evidence_mentions(flat)[1],
        "circumstances": circumstances(flat),
        "decision_maker": name,
        "decision_maker_role": role,
    }
    rec.update(amounts(flat))
    return rec


if __name__ == "__main__":
    import json
    import sys
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as f:
            print(json.dumps(extract(f.read()), indent=2, ensure_ascii=False))
