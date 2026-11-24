"""
Tests for v2.2: real-order guidance, similar-orders search, hearing-prep pages.

Run:  python -m pytest Tool_Creation/04.test/test_real_data_features.py -q
"""
import io
import json
import os
import sys
from unittest import mock

import pytest

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "01.local app version")
sys.path.insert(0, os.path.abspath(APP_DIR))

import app as housekeeper  # noqa: E402
import hearing_prep  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    housekeeper.app.config["UPLOAD_FOLDER"] = str(tmp_path)
    housekeeper.app.config["TESTING"] = True
    return housekeeper.app.test_client()


# ─── guidance ─────────────────────────────────────────────────────────────────

def test_guidance_covers_five_case_types(client):
    g = client.get("/ltb-guidance").get_json()
    assert g["version"] == 2
    assert set(g["case_types"]) == {"N4", "N5", "N12", "T2", "T6"}
    for block in g["case_types"].values():
        assert block["items"], "every case type needs checklist items"
        for item in block["items"]:
            assert item["label"] and item["why"]


def test_guidance_examples_are_real_orders_without_full_names(client):
    g = client.get("/ltb-guidance").get_json()
    examples = [ex for b in g["case_types"].values() for it in b["items"] for ex in it["examples"]]
    assert len(examples) >= 10
    for ex in examples:
        assert ex["file_number"].startswith("LTB-")
        assert ex["url"].startswith("https://")
        assert " v " not in ex["excerpt"]  # no case names (they include tenants)


# ─── similar orders ───────────────────────────────────────────────────────────

def test_similar_query_building():
    assert housekeeper._similar_query("N4", "") == '"did not pay the rent"'
    q = housekeeper._similar_query("N4", 'payment "plan" ODSP')
    assert q == '"did not pay the rent" AND (payment OR plan OR ODSP)'


def test_similar_uses_live_api_when_available(client):
    fake = {"results": [{"citation2_en": "LTB-L-000001-26", "document_date_en": "2026-07-31T00:00:00",
                         "url_en": "https://example.org/x.pdf", "snippet": "the <em>payment plan</em> is reasonable"}]}
    resp = mock.MagicMock()
    resp.__enter__.return_value.read.return_value = json.dumps(fake).encode()
    with mock.patch.object(housekeeper.urllib.request, "urlopen", return_value=resp):
        r = client.get("/similar?type=N4&q=payment plan").get_json()
    assert r["source"] == "live"
    assert r["results"][0]["excerpt"] == "the payment plan is reasonable"


def test_similar_falls_back_to_saved_examples(client):
    with mock.patch.object(housekeeper.urllib.request, "urlopen", side_effect=OSError("offline")):
        r = client.get("/similar?type=N4&q=anything").get_json()
    assert r["source"] == "saved"
    assert r["results"]


# ─── payment plan maths ───────────────────────────────────────────────────────

def test_plan_uses_surplus_by_default():
    p = hearing_prep.payment_plan(6090, 2030, [{"label": "Wages", "amount": 3600}],
                                  [{"label": "Rent", "amount": 2030}, {"label": "Food", "amount": 700}],
                                  start_date="2026-08-01")
    assert p["surplus"] == 870 and p["proposed_monthly"] == 870
    assert p["months"] == 7
    assert p["schedule"][-1]["balance_after"] == 0
    assert round(sum(s["amount"] for s in p["schedule"]), 2) == 6090
    assert p["warnings"] == []


def test_plan_warns_on_missing_rent_long_plan_and_no_surplus():
    p = hearing_prep.payment_plan(23000, 2000, [{"label": "ODSP", "amount": 2100}], [{"label": "Food", "amount": 300}])
    text = " ".join(p["warnings"])
    assert "do not include rent" in text and "months" in text
    broke = hearing_prep.payment_plan(5000, 2000, [{"label": "Wages", "amount": 2000}], [{"label": "Rent", "amount": 2000}])
    assert broke["months"] is None
    assert any("no money for repayment" in w for w in broke["warnings"])


def test_plan_month_end_dates():
    p = hearing_prep.payment_plan(300, 0, [{"label": "x", "amount": 100}], [], start_date="2026-01-31")
    assert [s["due"] for s in p["schedule"]] == ["2026-01-31", "2026-02-28", "2026-03-31"]


def test_payment_plan_route(client):
    r = client.post("/payment-plan", json={"arrears": 1000, "incomes": [{"label": "w", "amount": 600}],
                                            "expenses": [{"label": "Rent", "amount": 100}], "proposed_monthly": 250})
    assert r.get_json()["months"] == 4


# ─── hearing-prep pages in the brief ──────────────────────────────────────────

PREP = {
    "s82": {"issues": [{"issue": "No heat in bedroom", "started": "2025-12", "reported": "2025-12-11 email", "evidence_tab": "Tab 5"}],
            "served_on": "2026-07-10", "served_how": "email"},
    "payment_plan": {"arrears": 6090, "monthly_rent": 2030, "incomes": [{"label": "Wages", "amount": 3600}],
                     "expenses": [{"label": "Rent", "amount": 2030}], "start_date": "2026-08-01"},
    "circumstances": {"checked": ["children"], "relief": "postpone", "postpone_until": "2026-09-30"},
}


def test_prep_tabs_order_and_skip_empty():
    tabs = hearing_prep.build_prep_tabs(PREP)
    assert [t["generated"]["kind"] for t in tabs] == ["s82", "payment_plan", "circumstances"]
    assert hearing_prep.build_prep_tabs({"s82": {"issues": [{"issue": "  "}]}, "payment_plan": {"arrears": 0}}) == []


def test_generate_brief_with_prep_pages_only(client):
    r = client.post("/generate", json={"case_info": {"file_number": "LTB-L-000000-26"}, "tabs": [], "hearing_prep": PREP})
    assert r.status_code == 200 and r.mimetype == "application/pdf"
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not installed")
    text = "".join(p.get_text() for p in fitz.open(stream=r.data, filetype="pdf"))
    assert "Issues the Tenant Intends to Raise" in text
    assert "Tenant's Proposed Payment Plan" in text
    assert "Delay the eviction to give the household time to move until 2026-09-30" in text


def test_generate_rejects_empty_brief(client):
    r = client.post("/generate", json={"case_info": {}, "tabs": []})
    assert r.status_code == 400


def test_client_cannot_inject_generated_tabs(client):
    r = client.post("/generate", json={"case_info": {}, "tabs": [{"title": "Evidence", "images": [],
                                                                    "generated": {"kind": "payment_plan", "data": {"arrears": 99999}}}]})
    assert r.status_code == 200
    import fitz
    text = "".join(p.get_text() for p in fitz.open(stream=r.data, filetype="pdf"))
    assert "Proposed Payment Plan" not in text
