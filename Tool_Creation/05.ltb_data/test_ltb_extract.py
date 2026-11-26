"""
Tests for ltb_extract.py.

Fixtures in fixtures/ are real LTB orders from A2AJ (Open Government Licence –
Ontario), trimmed, with tenant names replaced by [Tenant]. The one-line cases
below are real sentences taken from LTB orders through A2AJ search.

Run:  python -m pytest Tool_Creation/05.ltb_data -q
"""
import os
import pytest

import ltb_extract as E

HERE = os.path.dirname(__file__)


def fx(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return E.extract(f.read())


# ─── whole orders ─────────────────────────────────────────────────────────────

def test_tenant_absent_eviction():
    r = fx("kay_absent_refused.txt")
    assert r["file_number"] == "LTB-L-103302-24"
    assert r["side"] == "landlord"
    assert r["grounds"] == ["arrears_N4"]
    assert r["tenant_attended"] is False
    assert r["notice_valid"] is True and r["notice_voided"] is False
    assert r["outcome"] == "eviction_ordered"
    assert r["outcome_bucket"] == "eviction"
    assert r["monthly_rent"] == 1100.0 and r["arrears"] == 18360.0
    assert r["paid_since_filing"] == 10640.0
    assert r["decision_maker"] == "Bryan Delorenzi"
    assert r["landlord_corporate"] is False


def test_payment_plan_after_hearing():
    r = fx("kako_payment_plan.txt")
    assert r["tenant_attended"] is True
    assert r["landlord_rep"] == "legal_rep"
    assert r["landlord_corporate"] is True
    assert r["outcome"] == "conditional_relief"
    assert r["outcome_bucket"] == "kept_tenancy_with_plan"
    assert r["consent"] is False


def test_tenant_already_moved_out():
    r = fx("saleh_vacated.txt")
    assert r["tenant_attended"] is False
    assert r["tenant_vacated"] is True
    assert r["outcome"] == "vacated"


def test_mediated_consent_payment_plan():
    r = fx("aquash_consent_plan.txt")
    assert r["consent"] is True and r["mediated"] is True
    assert r["tenant_attended"] is True
    assert r["outcome"] == "consent_payment_plan"
    assert r["decision_maker_role"] == "hearing_officer"


def test_consent_move_out_date():
    r = fx("sinnott_consent_termination.txt")
    assert r["outcome"] == "consent_termination"
    assert r["outcome_bucket"] == "eviction"
    assert r["tenant_rep"] == "legal_rep"
    assert r["landlord"] == "Housing York Inc."


def test_postponed_with_s82_barred_and_missing_documents():
    r = fx("moylan_postponed_s82.txt")
    assert r["landlord_rep"] == "paralegal"
    assert r["s82_raised"] is True and r["s82_barred"] is True
    assert r["s83_3_argued"] is True and r["s83_3_refusal"] is False
    assert r["outcome"] == "postponed"
    assert r["no_documentary_evidence"] is True
    assert r["payment_plan_requested"] is True
    assert r["payment_plan_rejected"] is True
    # listed as missing, not as filed
    assert "photos_video" in r["evidence_missing"]
    assert "photos_video" not in r["evidence"]
    assert "children" in r["circumstances"]


def test_videoconference_is_not_video_evidence():
    r = fx("kako_payment_plan.txt")
    assert "photos_video" not in r["evidence"]


# ─── single sentences from real orders ────────────────────────────────────────

@pytest.mark.parametrize("sentence,expected", [
    ("The Tenant met with Tenant Duty Counsel prior to the hearing.", True),
    ("The Tenant did speak with Tenant Duty Counsel prior to mediation.", True),
    ("Prior to mediation, the Tenant utilized the services of Tenant Duty Counsel.", True),
    ("The Tenant declined to speak to Tenant Duty Counsel prior to the hearing.", False),
    ("Prior to mediation, the Tenant did not utilize the services of Tenant Duty Counsel.", False),
    ("The Tenants were self-represented and did not speak with Tenant Duty Counsel prior to the mediation.", False),
])
def test_duty_counsel(sentence, expected):
    assert E.duty_counsel(sentence) is expected


@pytest.mark.parametrize("sentence", [
    "In light of there being children in the unit and one of the Tenants being pregnant I find it is not unfair to postpone the eviction until August 31, 2026.",
    "and find that it would not be unfair to postpone the eviction until August 31, 2026, pursuant to",
    "As such, I find it reasonable in the circumstances to postpone the eviction until August 28, 2026 pursuant to subsection 83(1)(b) of the Act",
])
def test_postponed(sentence):
    assert E.outcome(sentence) == "postponed"


@pytest.mark.parametrize("sentence", [
    "The Tenant did not submit documentary evidence to support his alleged income and expenses.",
    "The Tenant has not provided any evidence to support an income, or a reasonable payment plan, to pay for these arrears and costs.",
    "This lack of corroborating evidence informs my decision that a payment plan is not realistic in the circumstances.",
])
def test_no_documents(sentence):
    import re
    assert re.search(E.NO_DOCS, sentence, re.I)


@pytest.mark.parametrize("name,corporate", [
    ("CAPREIT Limited Partnership", True),
    ("Housing York Inc.", True),
    ("13878074 Canada Inc.", True),
    ("Homestead Land Holdings Limited", True),
    ("David Kay", False),
    ("RAMA SALEH", False),
])
def test_corporate_landlord(name, corporate):
    assert E.is_corporate(name) is corporate
