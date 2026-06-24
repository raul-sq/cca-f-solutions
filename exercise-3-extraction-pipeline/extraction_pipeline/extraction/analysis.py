"""
analysis.py - Accuracy analysis and review-routing summary (STEP 5).

Given validated extractions and gold labels, compute:
  - per-FIELD accuracy (how often each field matches gold),
  - per-DOCUMENT-TYPE accuracy (to verify consistent performance across formats),
  - a human-review routing summary (how many extractions were flagged low-confidence).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .schema import PublicationMetadata

# Fields we score against gold. (abstract_summary is free text -> not exact-matched.)
SCORED_FIELDS = [
    "title",
    "authors",
    "publication_year",
    "document_type",
    "doi",
    "funding_source",
    "citation_count",
]


def _norm(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return tuple(sorted(str(v).strip().lower() for v in value))
    return value


def _field_matches(field: str, extracted: PublicationMetadata, gold: Dict) -> bool:
    got = getattr(extracted, field)
    want = gold.get(field)
    return _norm(got) == _norm(want)


def accuracy_report(
    extractions: Dict[str, PublicationMetadata],
    gold: Dict[str, Dict],
) -> Dict:
    """Build the per-field and per-type accuracy breakdown."""
    field_hits = {f: 0 for f in SCORED_FIELDS}
    field_total = {f: 0 for f in SCORED_FIELDS}
    # type -> {"docs": n, "field_hits": ..., "field_total": ...}
    by_type: Dict[str, Dict] = {}

    for cid, meta in extractions.items():
        g = gold.get(cid)
        if g is None:
            continue
        dtype = g.get("doc_type_label", "unknown")
        bucket = by_type.setdefault(dtype, {"docs": 0, "hits": 0, "total": 0})
        bucket["docs"] += 1
        for f in SCORED_FIELDS:
            ok = _field_matches(f, meta, g)
            field_total[f] += 1
            bucket["total"] += 1
            if ok:
                field_hits[f] += 1
                bucket["hits"] += 1

    per_field = {
        f: (field_hits[f] / field_total[f] if field_total[f] else None)
        for f in SCORED_FIELDS
    }
    per_type = {
        t: {
            "documents": b["docs"],
            "accuracy": (b["hits"] / b["total"] if b["total"] else None),
        }
        for t, b in by_type.items()
    }

    # Consistency check: spread of accuracy across document types.
    type_accs = [v["accuracy"] for v in per_type.values() if v["accuracy"] is not None]
    consistency_spread = (max(type_accs) - min(type_accs)) if type_accs else None

    return {
        "per_field_accuracy": per_field,
        "per_type_accuracy": per_type,
        "consistency_spread": consistency_spread,  # smaller = more consistent
        "scored_documents": sum(field_total[f] for f in SCORED_FIELDS) // len(SCORED_FIELDS)
        if SCORED_FIELDS else 0,
    }


def routing_summary(results: List) -> Dict:
    """Summarize how many extractions were routed to human review (Step 5).

    `results` is a list of extract.ExtractionResult-like objects exposing
    `needs_human_review` and `review_reasons`.
    """
    flagged = [r for r in results if getattr(r, "needs_human_review", False)]
    return {
        "total": len(results),
        "auto_accepted": len(results) - len(flagged),
        "routed_to_review": len(flagged),
        "review_rate": (len(flagged) / len(results)) if results else 0.0,
        "examples": [
            {"custom_id": getattr(r, "custom_id", "?"), "reasons": r.review_reasons}
            for r in flagged[:5]
        ],
    }


def format_report(acc: Dict) -> str:
    """Pretty-print the accuracy report as plain text."""
    lines = ["Per-field accuracy:"]
    for f, a in acc["per_field_accuracy"].items():
        lines.append(f"  {f:18s} {'n/a' if a is None else f'{a*100:5.1f}%'}")
    lines.append("Per-document-type accuracy:")
    for t, v in acc["per_type_accuracy"].items():
        a = v["accuracy"]
        lines.append(f"  {t:18s} {'n/a' if a is None else f'{a*100:5.1f}%'} "
                     f"({v['documents']} docs)")
    spread = acc["consistency_spread"]
    lines.append(f"Consistency spread across types: "
                 f"{'n/a' if spread is None else f'{spread*100:.1f} pts'}")
    return "\n".join(lines)
