"""
fewshot.py - Few-shot examples (STEP 3).

Two (user document -> assistant tool_use) examples covering DIFFERENT formats:
narrative prose with inline citations, and a structured bibliography/table that
maps to document_type == 'other'. They also model the behaviours we want: emit
null for absent fields (no fabrication) and produce calibrated confidence.

The turns are built to keep STRICT user/assistant alternation when the real
document is appended, which is the canonical few-shot-with-tools layout:

    user(DOC1) -> assistant(tool_use ex1)
    user[tool_result ex1 + "DOC2"] -> assistant(tool_use ex2)
    user[tool_result ex2 + REAL_DOC]            <- built by final_user_turn()

Use:  messages = few_shot_prefix() + [final_user_turn(real_document_text)]
"""

from __future__ import annotations

from typing import List, Dict

from .schema import TOOL_NAME

_EX_ID_1 = "toolu_example_1"
_EX_ID_2 = "toolu_example_2"


def _assistant_tool_use(tool_use_id: str, payload: Dict) -> Dict:
    return {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": tool_use_id, "name": TOOL_NAME, "input": payload}
        ],
    }


def _user_extract(text: str) -> Dict:
    return {"role": "user", "content": f"Extract metadata from this document:\n\n{text}"}


def _user_result_then_next(tool_use_id: str, next_text: str) -> Dict:
    """One user turn: accept the previous tool_use AND give the next instruction."""
    return {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": tool_use_id, "content": "Accepted."},
            {"type": "text", "text": f"Extract metadata from this document:\n\n{next_text}"},
        ],
    }


# Example 1: narrative prose with inline citations; DOI and funding ABSENT.
_EXAMPLE_DOC_1 = (
    "In a widely cited 2018 paper, 'Curriculum Sampling for Robust Detectors', "
    "Nguyen and Bauer describe a sampling schedule that improves rare-class recall "
    "(Nguyen & Bauer, 2018). Published in Vision Letters. Earlier work is noted "
    "(Hahn 2016) but no grant or DOI is mentioned in this excerpt."
)
_EXAMPLE_EXTRACTION_1 = {
    "title": "Curriculum Sampling for Robust Detectors",
    "authors": ["Nguyen", "Bauer"],
    "publication_year": 2018,
    "document_type": "journal_article",
    "document_type_detail": None,
    "doi": None,
    "funding_source": None,
    "keywords": [],
    "abstract_summary": "A curriculum sampling schedule that improves recall on rare classes for object detectors.",
    "citation_count": None,
    "field_confidence": {
        "title": 0.97, "authors": 0.95, "publication_year": 0.96,
        "document_type": 0.8, "doi": 0.99, "funding_source": 0.99,
        "abstract_summary": 0.9, "citation_count": 0.99,
    },
}

# Example 2: structured bibliography/table; unusual type -> 'other' + detail.
_EXAMPLE_DOC_2 = (
    "Record Type: Standards Document\n"
    "Title: Wire Protocol for Telemetry Exchange v2\n"
    "Authors: Telemetry Working Group\n"
    "Year: 2020\n"
    "DOI: 10.5555/telemetry.v2\n"
    "Funding: not applicable\n"
    "Note: This is a formal standard, not an article, report, or book chapter."
)
_EXAMPLE_EXTRACTION_2 = {
    "title": "Wire Protocol for Telemetry Exchange v2",
    "authors": ["Telemetry Working Group"],
    "publication_year": 2020,
    "document_type": "other",
    "document_type_detail": "Formal technical standard / specification document",
    "doi": "10.5555/telemetry.v2",
    "funding_source": None,
    "keywords": [],
    "abstract_summary": "A formal standard defining a v2 wire protocol for exchanging telemetry data.",
    "citation_count": None,
    "field_confidence": {
        "title": 0.98, "authors": 0.9, "publication_year": 0.97,
        "document_type": 0.85, "doi": 0.98, "funding_source": 0.92,
        "abstract_summary": 0.9, "citation_count": 0.99,
    },
}


def few_shot_prefix() -> List[Dict]:
    """Few-shot turns ending on an assistant tool_use (see module docstring)."""
    return [
        _user_extract(_EXAMPLE_DOC_1),
        _assistant_tool_use(_EX_ID_1, _EXAMPLE_EXTRACTION_1),
        _user_result_then_next(_EX_ID_1, _EXAMPLE_DOC_2),
        _assistant_tool_use(_EX_ID_2, _EXAMPLE_EXTRACTION_2),
    ]


def final_user_turn(document_text: str) -> Dict:
    """Closing user turn: accept example 2 AND present the real document."""
    return _user_result_then_next(_EX_ID_2, document_text)
