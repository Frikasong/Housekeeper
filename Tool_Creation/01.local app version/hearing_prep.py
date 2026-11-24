"""
Hearing-preparation pages for the evidence brief.

Three optional documents a tenant can add in front of their evidence:

  1. Issues the Tenant Intends to Raise (section 82) – for rent arrears hearings.
  2. Proposed Payment Plan – income, expenses and a repayment schedule.
  3. Tenant's Circumstances (section 83) – facts the Board weighs on relief.

Each builder returns ReportLab flowables in the brief's Times style. They are
added to the brief as their own tabs, so they appear in the table of contents.

What goes in these pages is the tenant's own information. The wording explains
what the Residential Tenancies Act asks for; it is not legal advice.
"""
import datetime as dt
import math
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, Spacer, Table, TableStyle

# ─── payment plan maths ───────────────────────────────────────────────────────

LONG_PLAN_MONTHS = 12  # members often question plans much longer than a year


def _num(x):
    try:
        return round(float(str(x).replace(",", "").replace("$", "")), 2)
    except (TypeError, ValueError):
        return 0.0


def _add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    last = [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return dt.date(year, month, min(d.day, last))


def payment_plan(arrears, monthly_rent, incomes=None, expenses=None,
                 proposed_monthly=None, start_date=None):
    """Work out an affordable repayment schedule.

    incomes / expenses: lists of {"label", "amount"} per month. Expenses should
    include the ongoing rent, because a plan only works if new rent is also paid.
    proposed_monthly: amount the tenant wants to offer; defaults to the whole
    monthly surplus.
    """
    arrears = _num(arrears)
    monthly_rent = _num(monthly_rent)
    incomes = [{"label": str(i.get("label", "")), "amount": _num(i.get("amount"))} for i in (incomes or []) if i]
    expenses = [{"label": str(e.get("label", "")), "amount": _num(e.get("amount"))} for e in (expenses or []) if e]
    total_in = round(sum(i["amount"] for i in incomes), 2)
    total_out = round(sum(e["amount"] for e in expenses), 2)
    rent_listed = any("rent" in e["label"].lower() for e in expenses)
    surplus = round(total_in - total_out, 2)

    offer = _num(proposed_monthly) if proposed_monthly not in (None, "") else max(surplus, 0)
    warnings = []
    if not rent_listed and monthly_rent:
        warnings.append("Your expenses do not include rent. The Board will expect you to keep paying the full rent on top of the plan, so add it as an expense.")
    if surplus <= 0:
        warnings.append("Your expenses are equal to or higher than your income, so the budget shows no money for repayment. Members usually refuse a payment plan that the budget cannot support.")
    if offer > surplus > 0:
        warnings.append("The monthly amount you offer is more than your budget surplus. Members check whether a plan is realistic.")

    schedule, months = [], None
    if offer > 0 and arrears > 0:
        months = math.ceil(arrears / offer)
        start = start_date if isinstance(start_date, dt.date) else (
            dt.date.fromisoformat(start_date) if start_date else _add_months(dt.date.today().replace(day=1), 1))
        remaining = arrears
        for i in range(months):
            amt = round(min(offer, remaining), 2)
            remaining = round(remaining - amt, 2)
            schedule.append({"due": _add_months(start, i).isoformat(), "amount": amt, "balance_after": remaining})
        if months > LONG_PLAN_MONTHS:
            warnings.append("This plan takes %d months. Members are often reluctant to approve plans much longer than a year; a larger monthly amount or a lump sum may be needed." % months)

    return {
        "arrears": arrears, "monthly_rent": monthly_rent,
        "incomes": incomes, "expenses": expenses,
        "total_income": total_in, "total_expenses": total_out,
        "surplus": surplus, "proposed_monthly": round(offer, 2),
        "months": months, "schedule": schedule, "warnings": warnings,
    }


# ─── PDF pages ────────────────────────────────────────────────────────────────

def _styles():
    s = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("PrepTitle", parent=s["Normal"], fontName="Times-Bold", fontSize=14, leading=18, alignment=TA_CENTER, spaceAfter=4),
        "sub": ParagraphStyle("PrepSub", parent=s["Normal"], fontName="Times-Italic", fontSize=10, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#333333")),
        "h": ParagraphStyle("PrepH", parent=s["Normal"], fontName="Times-Bold", fontSize=12, leading=16, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("PrepBody", parent=s["Normal"], fontName="Times-Roman", fontSize=11, leading=15, spaceAfter=6),
        "cell": ParagraphStyle("PrepCell", parent=s["Normal"], fontName="Times-Roman", fontSize=10, leading=13),
        "cellb": ParagraphStyle("PrepCellB", parent=s["Normal"], fontName="Times-Bold", fontSize=10, leading=13),
        "note": ParagraphStyle("PrepNote", parent=s["Normal"], fontName="Times-Italic", fontSize=9, leading=12, textColor=colors.HexColor("#444444"), spaceBefore=10),
    }


def _p(text, style):
    return Paragraph(xml_escape(str(text or "")).replace("\n", "<br/>"), style)


def _money(x):
    return "${:,.2f}".format(_num(x))


def _table(rows, widths, st, header=True):
    data = [[c if not isinstance(c, str) else _p(c, st["cellb"] if header and r == 0 else st["cell"]) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee") if header else colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _heading(title, subtitle, case_info, st):
    out = [_p(title, st["title"])]
    if subtitle:
        out.append(_p(subtitle, st["sub"]))
    fn = (case_info or {}).get("file_number")
    if fn:
        out.append(_p("LTB File Number: " + fn, st["sub"]))
    out += [Spacer(1, 0.12 * inch), HRFlowable(width="100%", thickness=0.5, color=colors.black), Spacer(1, 0.15 * inch)]
    return out


def s82_page(data, case_info, usable_w):
    st = _styles()
    issues = [i for i in (data.get("issues") or []) if (i.get("issue") or "").strip()]
    story = _heading("Issues the Tenant Intends to Raise at the Rent Arrears Hearing",
                     "Residential Tenancies Act, 2006, section 82", case_info, st)
    story.append(_p("The Tenant intends to raise the following issues about the Landlord's obligations under the Act. "
                    "Copies of the supporting evidence are in the tabs noted below.", st["body"]))
    rows = [["#", "Issue", "Started", "Reported to Landlord (date and how)", "Evidence"]]
    for n, i in enumerate(issues, 1):
        rows.append([str(n), i.get("issue", ""), i.get("started", ""), i.get("reported", ""), i.get("evidence_tab", "")])
    w = usable_w
    story.append(_table(rows, [0.35 * inch, w * 0.36, w * 0.14, w * 0.24, w - 0.35 * inch - w * 0.74], st))
    if data.get("remedy"):
        story += [_p("Remedy requested", st["h"]), _p(data["remedy"], st["body"])]
    served = data.get("served_on")
    how = data.get("served_how")
    story += [_p("Disclosure", st["h"]),
              _p("This description and copies of the evidence were given to the Landlord and the Landlord and Tenant Board"
                 + (" on " + served if served else "") + (" by " + how if how else "") + ".", st["body"]),
              _p("The Notice of Hearing asks parties to share evidence as soon as possible and at least 7 days before the hearing. "
                 "A tenant who does not give written notice of section 82 issues may not be allowed to raise them.", st["note"])]
    return story


def payment_plan_page(data, case_info, usable_w):
    st = _styles()
    plan = payment_plan(data.get("arrears"), data.get("monthly_rent"), data.get("incomes"), data.get("expenses"),
                        data.get("proposed_monthly"), data.get("start_date"))
    story = _heading("Tenant's Proposed Payment Plan", "Request for relief from eviction subject to conditions, section 83(1)(a)", case_info, st)
    story.append(_p("The Tenant asks the Board to refuse the eviction on condition that the Tenant pays the arrears "
                    "on the schedule below and pays the full rent on time as it comes due.", st["body"]))

    summary = [["", "Amount"],
               ["Arrears and costs claimed", _money(plan["arrears"])],
               ["Monthly rent", _money(plan["monthly_rent"])],
               ["Monthly household income", _money(plan["total_income"])],
               ["Monthly expenses (including rent)", _money(plan["total_expenses"])],
               ["Money left each month", _money(plan["surplus"])],
               ["Proposed monthly payment toward arrears", _money(plan["proposed_monthly"])]]
    story.append(_table(summary, [usable_w * 0.65, usable_w * 0.35], st))

    def budget(title, items):
        if not items:
            return []
        rows = [[title, "Per month"]] + [[i["label"], _money(i["amount"])] for i in items]
        return [_p(title, st["h"]), _table(rows, [usable_w * 0.65, usable_w * 0.35], st)]

    story += budget("Income", plan["incomes"]) + budget("Expenses", plan["expenses"])

    if plan["schedule"]:
        story.append(_p("Proposed schedule (%d payments)" % plan["months"], st["h"]))
        rows = [["Payment", "Due date", "Amount", "Balance after"]]
        for n, s in enumerate(plan["schedule"], 1):
            rows.append([str(n), s["due"], _money(s["amount"]), _money(s["balance_after"])])
        story.append(_table(rows, [usable_w * 0.15, usable_w * 0.3, usable_w * 0.25, usable_w * 0.3], st))

    if data.get("documents_tab"):
        story.append(_p("Proof of income and expenses: see " + data["documents_tab"] + ".", st["body"]))
    if data.get("explanation"):
        story += [_p("Why the arrears happened and what has changed", st["h"]), _p(data["explanation"], st["body"])]
    story.append(_p("Members often refuse payment plans that are not supported by documents showing the tenant's income "
                    "and expenses. Attach pay stubs, benefit statements or bank statements.", st["note"]))
    return story


CIRCUMSTANCE_LABELS = {
    "children": "Children live in the unit",
    "disability_health": "Disability or health condition in the household",
    "benefits_income": "Household income comes from ODSP, Ontario Works or other benefits",
    "job_loss": "Recent loss of job or income",
    "long_tenancy": "Long tenancy",
    "senior": "Senior in the household",
    "housing_search": "Actively searching for other housing",
    "landlord_breach": "Landlord has not kept the unit in good repair",
}

RELIEF_LABELS = {
    "refuse": "Refuse the eviction",
    "payment_plan": "Refuse the eviction on condition of a payment plan (see Proposed Payment Plan)",
    "postpone": "Delay the eviction to give the household time to move",
}


def circumstances_page(data, case_info, usable_w):
    st = _styles()
    story = _heading("Tenant's Circumstances", "Relevant to relief from eviction, Residential Tenancies Act, 2006, section 83", case_info, st)
    checked = [k for k in data.get("checked") or [] if k in CIRCUMSTANCE_LABELS]
    if checked:
        rows = [["Circumstance", "Details"]]
        details = data.get("details") or {}
        for k in checked:
            rows.append([CIRCUMSTANCE_LABELS[k], details.get(k, "")])
        story.append(_table(rows, [usable_w * 0.42, usable_w * 0.58], st))
        story.append(Spacer(1, 0.15 * inch))
    if data.get("household"):
        story += [_p("Household", st["h"]), _p(data["household"], st["body"])]
    if data.get("tenancy_since"):
        story.append(_p("The Tenant has lived in the unit since " + data["tenancy_since"] + ".", st["body"]))
    if data.get("statement"):
        story += [_p("Statement", st["h"]), _p(data["statement"], st["body"])]
    relief = data.get("relief")
    if relief in RELIEF_LABELS:
        txt = RELIEF_LABELS[relief]
        if relief == "postpone" and data.get("postpone_until"):
            txt += " until " + data["postpone_until"]
        story += [_p("Relief requested", st["h"]), _p(txt + ".", st["body"])]
    if data.get("documents_tab"):
        story.append(_p("Supporting documents: see " + data["documents_tab"] + ".", st["body"]))
    story.append(_p("Under section 83 the Board considers all circumstances in deciding whether to refuse or delay an eviction. "
                    "Documents (medical letters, benefit statements, housing search records) make these facts easier to accept.", st["note"]))
    return story


def build_prep_tabs(prep):
    """Return generated tabs to place before the evidence tabs, in a fixed order."""
    prep = prep or {}
    tabs = []
    s82 = prep.get("s82") or {}
    if any((i.get("issue") or "").strip() for i in s82.get("issues") or []):
        tabs.append({"title": "Issues the Tenant Intends to Raise (s. 82)", "images": [], "generated": {"kind": "s82", "data": s82}})
    pp = prep.get("payment_plan") or {}
    if _num(pp.get("arrears")) > 0:
        tabs.append({"title": "Tenant's Proposed Payment Plan", "images": [], "generated": {"kind": "payment_plan", "data": pp}})
    c = prep.get("circumstances") or {}
    if c.get("checked") or c.get("statement") or c.get("relief"):
        tabs.append({"title": "Tenant's Circumstances (s. 83)", "images": [], "generated": {"kind": "circumstances", "data": c}})
    return tabs


BUILDERS = {"s82": s82_page, "payment_plan": payment_plan_page, "circumstances": circumstances_page}


def generated_flowables(generated, case_info, usable_w):
    fn = BUILDERS.get((generated or {}).get("kind"))
    return fn(generated.get("data") or {}, case_info, usable_w) if fn else []
