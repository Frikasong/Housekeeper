"""
Local evidence analyzer for LTB N4 decisions.

Uses sentence-transformers (all-MiniLM-L6-v2, ~80MB) for semantic similarity.
All processing runs locally — no data is sent to any cloud service.

Usage:
    from evidence_analyzer import analyze_pdf
    stats = analyze_pdf("decisions.pdf")
    # stats is a dict ready to write as evidence_stats.json
"""

import re
import json
import os
from collections import Counter

# ---------------------------------------------------------------------------
# Evidence categories and their semantic reference phrases
# Each category has multiple example phrases that describe what that evidence
# looks like in an LTB decision. The model compares case text against these.
#
# Phrases are chosen to be specific and distinctive — avoiding generic legal
# language that could false-positive across categories.
# ---------------------------------------------------------------------------

EVIDENCE_CATEGORIES = {
    "N4 Notice of Termination": [
        "N4 notice of termination was served",
        "the landlord served an N4 notice",
        "form N4 for non-payment of rent",
        "N4 application for termination",
        "notice of termination for non-payment of rent",
        "the N4 notice was filed with the Board",
    ],
    "Financial records (rent receipts, bank statements, rent ledger)": [
        "rent receipts were submitted as evidence",
        "bank statements showing rent deposits",
        "rent ledger documenting monthly payments",
        "financial records of rent transactions",
        "account statements from the bank were filed",
        "receipts for rent paid were entered as exhibits",
        "the landlord submitted a rent ledger as an exhibit",
    ],
    "Lease agreement": [
        "the lease agreement between the parties was submitted as evidence",
        "the tenancy agreement was entered into evidence at the hearing",
        "a signed rental agreement was filed as an exhibit",
        "the written lease document specifies the monthly rent",
        "a copy of the lease was produced by the landlord",
    ],
    "Payment history / transaction records": [
        "payment history showing rent arrears over several months",
        "e-transfer records confirming rent payments",
        "cheques provided as proof of rent payment",
        "money order receipts for rent",
        "rent arrears accumulated over several months",
        "outstanding rent owing to the landlord totals",
        "record of partial payments made by the tenant",
    ],
    "Communication records (emails, text messages, letters)": [
        "email correspondence between landlord and tenant was submitted",
        "text messages about rent were filed as exhibits",
        "demand letters sent by the landlord were entered into evidence",
        "voicemail messages were submitted as evidence",
        "written communication records were filed as exhibits",
    ],
    "Legal documents (prior orders, court filings)": [
        "a prior Board order from a previous proceeding was filed",
        "a previous LTB order regarding this tenancy was submitted",
        "a section 78 conditional order was previously granted",
        "the tenant breached a previous conditional order",
        "a previous application had been filed with the Board",
        "documents from a prior court hearing were submitted",
    ],
    "Witness testimony": [
        "a witness testified at the hearing about the tenancy",
        "oral testimony was provided by a third party witness",
        "the witness gave sworn evidence about the rental unit",
        "a sworn affidavit was submitted by a witness",
        "testimony from a third party corroborated the claim",
    ],
    "Government/third-party records (inspection reports, municipal notices)": [
        "an inspection report from the municipality was filed",
        "a by-law enforcement notice was submitted",
        "the health inspector report on the rental unit",
        "fire inspector findings were entered as evidence",
        "property standards inspection report was submitted",
        "a municipal notice regarding the property was filed",
    ],
    "Photos of unit conditions": [
        "photographs of the rental unit were submitted",
        "photos showing the condition of the unit were filed",
        "photographic evidence of the unit was entered as an exhibit",
        "pictures of damage to the property were submitted",
        "video evidence of the unit condition was shown",
    ],
    "Maintenance/repair requests or records": [
        "repair requests submitted by the tenant to the landlord",
        "maintenance records for the rental unit were filed",
        "work orders for repairs to the unit were submitted",
        "service requests for maintenance issues were entered",
        "record of maintenance performed on the rental unit",
    ],
}

# LTB file number patterns:
# Standard: TSL-12345-22, SOL-98765-23, TEL-00001-24-SA
# AI-generated: LTB-L-30001-25
CASE_NUMBER_RE = re.compile(
    r"\b([A-Z]{2,3}(?:-[A-Z])?-\d{4,6}-\d{2}(?:-[A-Z]{2,3})?)\b"
)

# Sentence splitting — split on period/newline but keep chunks meaningful
SENTENCE_RE = re.compile(r"(?<=[.!?\n])\s+")


def _load_model():
    """Load the sentence-transformers model. Downloads ~80MB on first run."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model


def _split_into_cases(full_text):
    """Split extracted PDF text into individual case blocks by file number."""
    matches = list(CASE_NUMBER_RE.finditer(full_text))

    if not matches:
        # No file numbers found — treat as one block
        return [("FULL_DOC", full_text)]

    case_blocks = []
    seen = set()
    for i, m in enumerate(matches):
        case_id = m.group(1)
        if case_id in seen:
            continue
        seen.add(case_id)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[start:end]
        if len(block.strip()) > 50:  # skip trivially small blocks
            case_blocks.append((case_id, block))

    return case_blocks


def _chunk_text(text, max_chunk_len=200):
    """Split case text into sentence-level chunks for embedding.

    We group sentences into chunks of roughly max_chunk_len characters
    to balance between granularity and speed.
    """
    sentences = SENTENCE_RE.split(text)
    chunks = []
    current = []
    current_len = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if current_len + len(sent) > max_chunk_len and current:
            chunks.append(" ".join(current))
            current = [sent]
            current_len = len(sent)
        else:
            current.append(sent)
            current_len += len(sent)

    if current:
        chunks.append(" ".join(current))

    return chunks


def analyze_cases(full_text, similarity_threshold=0.50, verbose=True):
    """Analyze extracted text and return list of cases with evidence types.

    Args:
        full_text: Full extracted text from PDF
        similarity_threshold: Min cosine similarity to count as a match (0-1).
            Lower = more matches, higher = stricter. 0.50 is well-tuned for
            LTB decisions.
        verbose: Print progress messages

    Returns:
        List of dicts: [{"case_id": "...", "evidence_types": [...]}, ...]
    """
    import numpy as np

    if not full_text or not full_text.strip():
        if verbose:
            print("No text to analyze.")
        return []

    if verbose:
        print("Loading semantic model (all-MiniLM-L6-v2)...")
    model = _load_model()

    # Pre-encode all reference phrases individually (not averaged).
    # Using max similarity across individual phrases is more precise than
    # comparing against an averaged category embedding.
    if verbose:
        print("Encoding evidence category references...")
    category_names = list(EVIDENCE_CATEGORIES.keys())

    all_ref_phrases = []
    phrase_to_cat_idx = []
    for cat_idx, cat_name in enumerate(category_names):
        for phrase in EVIDENCE_CATEGORIES[cat_name]:
            all_ref_phrases.append(phrase)
            phrase_to_cat_idx.append(cat_idx)

    ref_embeddings = model.encode(
        all_ref_phrases, show_progress_bar=False, normalize_embeddings=True
    )
    phrase_to_cat_idx = np.array(phrase_to_cat_idx)
    num_categories = len(category_names)

    # Split into cases
    case_blocks = _split_into_cases(full_text)
    if verbose:
        print(f"Found {len(case_blocks)} case(s). Analyzing...")

    all_cases = []
    for idx, (case_id, block) in enumerate(case_blocks):
        chunks = _chunk_text(block)
        if not chunks:
            all_cases.append({"case_id": case_id, "evidence_types": []})
            continue

        # Batch encode all chunks for this case
        chunk_embs = model.encode(chunks, show_progress_bar=False,
                                  normalize_embeddings=True, batch_size=64)

        # Cosine similarity: (num_chunks x dim) @ (dim x num_phrases)
        similarities = chunk_embs @ ref_embeddings.T  # (num_chunks, num_phrases)

        # For each category, find the max similarity across ALL its phrases
        # and ALL chunks. This is more precise than averaged embeddings.
        evidence_found = []
        for cat_i in range(num_categories):
            phrase_mask = phrase_to_cat_idx == cat_i
            cat_sims = similarities[:, phrase_mask]  # (num_chunks, phrases_in_cat)
            max_sim = cat_sims.max()
            if max_sim >= similarity_threshold:
                evidence_found.append(category_names[cat_i])

        all_cases.append({"case_id": case_id, "evidence_types": evidence_found})

        if verbose and (idx + 1) % 10 == 0:
            print(f"  Processed {idx + 1}/{len(case_blocks)} cases...")

    if verbose:
        print(f"Analysis complete. {len(all_cases)} case(s) processed.")
        for c in all_cases[:5]:
            print(f"  {c['case_id']}: {len(c['evidence_types'])} evidence types")
        if len(all_cases) > 5:
            print(f"  ... and {len(all_cases) - 5} more")

    return all_cases


def aggregate_stats(all_cases):
    """Convert case-level results into the evidence_stats.json format.

    Returns:
        Dict in the format expected by the app's /evidence-stats endpoint.
    """
    total = len(all_cases)
    counts = Counter()
    for case in all_cases:
        for et in set(case.get("evidence_types", [])):
            counts[et] += 1

    evidence_types = []
    for category, count in counts.most_common():
        pct = round(100 * count / total) if total > 0 else 0
        evidence_types.append({
            "category": category,
            "percentage": pct,
            "count": count,
        })

    return {
        "N4": {
            "description": "Non-payment of rent",
            "total_cases_analyzed": total,
            "evidence_types": evidence_types,
        }
    }


def analyze_pdf(pdf_path, output_path=None, similarity_threshold=0.50):
    """Full pipeline: PDF → text extraction → analysis → JSON.

    Args:
        pdf_path: Path to concatenated PDF of LTB decisions
        output_path: Where to save evidence_stats.json (optional)
        similarity_threshold: Cosine similarity threshold (default 0.50)

    Returns:
        Dict with evidence statistics
    """
    import pdfplumber

    print(f"Extracting text from {pdf_path}...")
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

    full_text = "\n\n".join(pages)
    print(f"Extracted {len(pages)} pages, {len(full_text):,} characters.")

    all_cases = analyze_cases(full_text, similarity_threshold=similarity_threshold)
    stats = aggregate_stats(all_cases)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(stats, f, indent=2)
        print(f"\nSaved to {output_path}")

    return stats


# ---------------------------------------------------------------------------
# CLI usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python evidence_analyzer.py <pdf_path> [output.json]")
        sys.exit(1)

    pdf_file = sys.argv[1]
    out_file = sys.argv[2] if len(sys.argv) > 2 else "evidence_stats.json"
    stats = analyze_pdf(pdf_file, out_file)

    print("\nResults:")
    for ev in stats["N4"]["evidence_types"]:
        print(f"  {ev['percentage']:3d}%  ({ev['count']})  {ev['category']}")
