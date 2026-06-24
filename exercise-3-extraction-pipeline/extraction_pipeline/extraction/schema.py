"""
schema.py - Extraction tool JSON schema, Pydantic validation models, and
validation-error classification.

Covers:
  STEP 1 - the extraction tool schema: required + optional fields, an enum with
           an "other" + detail-string pattern, and nullable fields.
  STEP 2 - Pydantic models used to validate the model's tool output, plus a
           helper that classifies validation errors as resolvable-by-retry
           (format/logic mismatches) vs not (information genuinely absent).
"""

from __future__ import annotations

from typing import Optional, List, Literal, Dict
from pydantic import BaseModel, Field, ValidationError, model_validator


# ---------------------------------------------------------------------------
# Field inventory (single source of truth, kept in sync across schema + models)
# ---------------------------------------------------------------------------
# Required, non-nullable: title, authors, document_type, abstract_summary
# Nullable (may be absent in source -> the model MUST emit null, not omit):
#   publication_year, doi, funding_source, citation_count, document_type_detail
# Optional (may be omitted entirely): keywords

DOCUMENT_TYPES = [
    "journal_article",
    "conference_paper",
    "preprint",
    "technical_report",
    "book_chapter",
    "other",          # the "other" escape hatch; must be paired with a detail string
]

# The data fields we ask the model to score for confidence (Step 5).
CONFIDENCE_FIELDS = [
    "title",
    "authors",
    "publication_year",
    "document_type",
    "doi",
    "funding_source",
    "abstract_summary",
    "citation_count",
]


# ---------------------------------------------------------------------------
# STEP 1 - The extraction tool schema passed to the Messages API `tools` param.
# ---------------------------------------------------------------------------
# Design notes:
#  - Nullable fields use a union type ["<type>", "null"] AND are listed in
#    `required`. Requiring the key while allowing null forces the model to emit
#    an explicit null when the info is absent, instead of silently dropping the
#    key (which is how fabrication / omission creeps in).
#  - `document_type` is an enum including "other"; `document_type_detail` carries
#    the free-text detail and is null unless document_type == "other".
#  - `keywords` is the one genuinely OPTIONAL field (not in `required`).
#  - `field_confidence` (Step 5) carries a 0..1 score per data field.

EXTRACTION_TOOL = {
    "name": "extract_publication_metadata",
    "description": (
        "Extract structured bibliographic metadata from a source document. "
        "Only record information that is explicitly present in the document. "
        "For any field whose information is NOT present, return null - never "
        "guess, infer, or fabricate a value. Provide a calibrated confidence "
        "score in [0,1] for each field reflecting how certain the extraction is."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The full title of the work, verbatim.",
            },
            "authors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of author names as written.",
            },
            "publication_year": {
                "type": ["integer", "null"],
                "description": "Four-digit year of publication, or null if absent.",
            },
            "document_type": {
                "type": "string",
                "enum": DOCUMENT_TYPES,
                "description": "The document category. Use 'other' only if none fit.",
            },
            "document_type_detail": {
                "type": ["string", "null"],
                "description": (
                    "Free-text description of the type. REQUIRED (non-null) only "
                    "when document_type == 'other'; MUST be null otherwise."
                ),
            },
            "doi": {
                "type": ["string", "null"],
                "description": "Digital Object Identifier, or null if not present.",
            },
            "funding_source": {
                "type": ["string", "null"],
                "description": "Funding body/grant, or null if not stated.",
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional keyword list; omit if the document has none.",
            },
            "abstract_summary": {
                "type": "string",
                "description": "A 1-2 sentence summary of the document's content.",
            },
            "citation_count": {
                "type": ["integer", "null"],
                "description": "Stated citation count, or null if not present.",
            },
            "field_confidence": {
                "type": "object",
                "description": "Confidence in [0,1] for each extracted data field.",
                "properties": {f: {"type": "number"} for f in CONFIDENCE_FIELDS},
                "required": CONFIDENCE_FIELDS,
            },
        },
        # Nullable fields are intentionally REQUIRED so the model emits explicit
        # nulls. `keywords` is deliberately absent here (truly optional).
        "required": [
            "title",
            "authors",
            "publication_year",
            "document_type",
            "document_type_detail",
            "doi",
            "funding_source",
            "abstract_summary",
            "citation_count",
            "field_confidence",
        ],
    },
}

TOOL_NAME = EXTRACTION_TOOL["name"]


# ---------------------------------------------------------------------------
# STEP 2 - Pydantic models mirroring the schema for strict local validation.
# ---------------------------------------------------------------------------

class FieldConfidence(BaseModel):
    title: float = Field(ge=0.0, le=1.0)
    authors: float = Field(ge=0.0, le=1.0)
    publication_year: float = Field(ge=0.0, le=1.0)
    document_type: float = Field(ge=0.0, le=1.0)
    doi: float = Field(ge=0.0, le=1.0)
    funding_source: float = Field(ge=0.0, le=1.0)
    abstract_summary: float = Field(ge=0.0, le=1.0)
    citation_count: float = Field(ge=0.0, le=1.0)


class PublicationMetadata(BaseModel):
    title: str = Field(min_length=1)
    authors: List[str] = Field(min_length=1)
    publication_year: Optional[int] = None
    document_type: Literal[
        "journal_article",
        "conference_paper",
        "preprint",
        "technical_report",
        "book_chapter",
        "other",
    ]
    document_type_detail: Optional[str] = None
    doi: Optional[str] = None
    funding_source: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    abstract_summary: str = Field(min_length=1)
    citation_count: Optional[int] = None
    field_confidence: FieldConfidence

    @model_validator(mode="after")
    def check_other_detail_rule(self) -> "PublicationMetadata":
        # The enum "other" + detail pattern: detail is required iff type is other.
        if self.document_type == "other" and not self.document_type_detail:
            raise ValueError(
                "document_type_detail must be a non-empty string when "
                "document_type == 'other'"
            )
        if self.document_type != "other" and self.document_type_detail:
            raise ValueError(
                "document_type_detail must be null when document_type != 'other'"
            )
        return self


# ---------------------------------------------------------------------------
# STEP 2 - Classify validation errors: resolvable-by-retry vs not.
# ---------------------------------------------------------------------------
# Pydantic v2 error "type" codes that represent a FORMAT/LOGIC mismatch the model
# can plausibly fix on a second attempt (wrong shape, wrong enum, omitted-but-
# should-be-null key, the other/detail rule, out-of-range confidence, etc.).
RETRYABLE_ERROR_TYPES = {
    "enum",
    "literal_error",
    "int_parsing",
    "int_type",
    "float_parsing",
    "string_type",
    "list_type",
    "missing",            # a required key was omitted - re-prompt to emit null
    "value_error",        # our custom other/detail rule lands here
    "greater_than_equal",
    "less_than_equal",
    "too_short",
}


def classify_validation_error(err: ValidationError) -> Dict[str, object]:
    """Return {'resolvable': bool, 'fields': [...], 'details': [...]}.

    'resolvable' is True when EVERY individual error is a format/logic mismatch
    (Step 2: resolvable via retry). If any error falls outside that set - for
    example a required, non-nullable field that the model cannot populate because
    the information is absent from the source - we treat the whole extraction as
    not-resolvable and route it to human review instead of looping forever.
    """
    fields, details, resolvable = [], [], True
    for e in err.errors():
        loc = ".".join(str(p) for p in e["loc"])
        fields.append(loc)
        details.append(f"{loc}: {e['msg']} (type={e['type']})")
        if e["type"] not in RETRYABLE_ERROR_TYPES:
            resolvable = False
    return {"resolvable": resolvable, "fields": fields, "details": details}
