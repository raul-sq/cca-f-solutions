"""
documents.py - Sample source documents of varied formats, their gold labels,
and a generator that produces a 100-document batch.

Used by:
  STEP 1 - documents where some fields are absent (to verify null, not fabrication).
  STEP 3 - varied formats (inline citations vs bibliography, narrative vs table).
  STEP 4 - make_documents(100) builds the batch; one oversized doc forces chunking.
  STEP 5 - gold labels drive the accuracy-by-type-and-field analysis.
"""

from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class Document(TypedDict):
    id: str            # used as the batch custom_id
    doc_type_label: str  # ground-truth document_type (for Step 5 analysis)
    text: str
    gold: Dict[str, object]  # gold field values for accuracy analysis


# ---------------------------------------------------------------------------
# Hand-crafted documents with deliberately VARIED formats (Step 3) and some
# deliberately ABSENT fields (Step 1).
# ---------------------------------------------------------------------------

SAMPLE_DOCUMENTS: List[Document] = [
    {
        # Format A: narrative prose with INLINE citations; year present, no DOI.
        "id": "doc-narrative-inline",
        "doc_type_label": "journal_article",
        "text": (
            "In their 2021 study, Alvarez and Okonkwo argue that retrieval-augmented "
            "generation reduces hallucination in long-context tasks (Alvarez & Okonkwo, "
            "2021). The work, titled 'Grounding Language Models with External Memory', "
            "appeared in the Journal of Applied NLP. The authors note prior results "
            "(see Smith 2019; Lee 2020) but report a 31% reduction over those baselines. "
            "No funding statement or DOI is included in this excerpt."
        ),
        "gold": {
            "title": "Grounding Language Models with External Memory",
            "authors": ["Alvarez", "Okonkwo"],
            "publication_year": 2021,
            "document_type": "journal_article",
            "doi": None,            # absent -> must be null
            "funding_source": None,  # absent -> must be null
            "citation_count": None,
        },
    },
    {
        # Format B: structured BIBLIOGRAPHY entry / table-like; DOI + funding present.
        "id": "doc-bibliography-table",
        "doc_type_label": "conference_paper",
        "text": (
            "Title: Efficient Sparse Attention for Edge Devices\n"
            "Authors: R. Mehta; J. Park; L. Fontaine\n"
            "Venue: Proceedings of the 2023 Conference on Machine Systems (CMS '23)\n"
            "DOI: 10.1145/1234567.8901234\n"
            "Funding: Supported by the European Research Council (ERC) grant 884422.\n"
            "Cited by: 87\n"
            "Abstract: We present a sparse attention kernel that cuts inference latency "
            "on microcontrollers by 4x with negligible accuracy loss."
        ),
        "gold": {
            "title": "Efficient Sparse Attention for Edge Devices",
            "authors": ["R. Mehta", "J. Park", "L. Fontaine"],
            "publication_year": 2023,
            "document_type": "conference_paper",
            "doi": "10.1145/1234567.8901234",
            "funding_source": "European Research Council (ERC) grant 884422",
            "citation_count": 87,
        },
    },
    {
        # Format C: an unusual type that should map to the enum "other" + detail.
        "id": "doc-other-type",
        "doc_type_label": "other",
        "text": (
            "DATASET RELEASE NOTE - 'OpenRoad-50k'\n"
            "Maintainers: The OpenRoad Consortium\n"
            "Year: 2022\n"
            "This is a dataset card describing 50,000 annotated driving scenes. "
            "It is neither a paper nor a report; it documents a public dataset release. "
            "No DOI assigned. No citation count available."
        ),
        "gold": {
            "title": "OpenRoad-50k",
            "authors": ["The OpenRoad Consortium"],
            "publication_year": 2022,
            "document_type": "other",
            "doi": None,
            "funding_source": None,
            "citation_count": None,
        },
    },
]


# ---------------------------------------------------------------------------
# STEP 4 - 100-document generator.
# ---------------------------------------------------------------------------
# Cycles through the three formats above with small variations so the batch
# exercises structural variety. Index 0 is intentionally OVERSIZED so the batch
# pipeline can demonstrate resubmission-with-chunking on failure.

def _padding(n_chars: int) -> str:
    sentence = ("This section repeats background discussion to inflate the document "
                "length for batch-size and chunking demonstrations. ")
    reps = (n_chars // len(sentence)) + 1
    return (sentence * reps)[:n_chars]


def make_documents(n: int = 100) -> List[Document]:
    docs: List[Document] = []
    for i in range(n):
        base = SAMPLE_DOCUMENTS[i % len(SAMPLE_DOCUMENTS)]
        doc: Document = {
            "id": f"doc-{i:03d}",
            "doc_type_label": base["doc_type_label"],
            "text": base["text"],
            "gold": dict(base["gold"]),
        }
        if i == 0:
            # Oversized variant: a very long preamble that may blow the token
            # budget for a single request and trigger the chunking path.
            doc["text"] = _padding(60_000) + "\n\n" + base["text"]
            doc["id"] = "doc-000-oversized"
        docs.append(doc)
    return docs


def gold_for(documents: List[Document]) -> Dict[str, Dict[str, object]]:
    """Map custom_id -> gold labels, for the Step 5 accuracy analysis."""
    return {d["id"]: {**d["gold"], "doc_type_label": d["doc_type_label"]} for d in documents}
