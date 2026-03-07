import anthropic
import json

client = anthropic.Anthropic()

def extract_evidence_structured(decision_text: str, case_id: str) -> dict:
    prompt = f"""
You are analyzing an Ontario LTB tribunal decision. Extract structured information about evidence.

Decision text:
<decision>
{decision_text[:6000]}
</decision>

Return a JSON object with:
{{
  "application_type": "L1/L2/T2/T6/N12/etc",
  "applicant": "landlord" or "tenant",
  "outcome": "landlord_success" / "tenant_success" / "partial" / "unclear",
  "evidence_submitted": [
    {{
      "type": "e.g. rent ledger, photos, text messages, N4 notice, lease agreement, bank records, inspection report, witness testimony, receipts, audio recording",
      "submitted_by": "landlord" or "tenant",
      "weight_given": "accepted" / "rejected" / "partial" / "not mentioned",
      "notes": "brief note on how adjudicator treated this evidence"
    }}
  ],
  "key_issues": ["list of factual issues adjudicator had to resolve"]
}}

Return only valid JSON, no explanation.
"""
    
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        return json.loads(response.content[0].text)
    except json.JSONDecodeError:
        return {"error": "parse_failed", "case_id": case_id}

import pandas as pd
from collections import defaultdict

def build_evidence_profile(extracted_cases: list[dict]) -> pd.DataFrame:
    rows = []
    for case in extracted_cases:
        if "error" in case:
            continue
        app_type = case.get("application_type", "unknown")
        for ev in case.get("evidence_submitted", []):
            rows.append({
                "application_type": app_type,
                "evidence_type": ev.get("type"),
                "submitted_by": ev.get("submitted_by"),
                "weight": ev.get("weight_given"),
                "outcome": case.get("outcome")
            })
    return pd.DataFrame(rows)

def generate_evidence_suggestions(df: pd.DataFrame, application_type: str, submitted_by: str):
    filtered = df[
        (df["application_type"] == application_type) &
        (df["submitted_by"] == submitted_by)
    ]
    
    # Frequency of each evidence type
    freq = filtered["evidence_type"].value_counts(normalize=True)
    
    # Acceptance rate per evidence type
    accepted = filtered[filtered["weight"] == "accepted"]
    acceptance_rate = accepted["evidence_type"].value_counts() / filtered["evidence_type"].value_counts()
    
    summary = pd.DataFrame({
        "frequency": freq,
        "acceptance_rate": acceptance_rate
    }).dropna().sort_values("frequency", ascending=False)
    
    return summary