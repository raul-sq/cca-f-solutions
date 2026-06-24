"""
extract.py - Single-document structured extraction.

Covers:
  STEP 1 - forces structured output via tool_use (tool_choice) and instructs the
           model to emit null for absent fields rather than fabricating.
  STEP 2 - validation-retry loop: on Pydantic failure, send a follow-up that
           includes the document (already in history), the failed extraction, and
           the specific validation error; track resolvable vs non-resolvable.
  STEP 5 - field-level confidence -> route low-confidence extractions to review.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import anthropic
from pydantic import ValidationError

from .schema import (
    EXTRACTION_TOOL,
    TOOL_NAME,
    PublicationMetadata,
    classify_validation_error,
)
from .fewshot import few_shot_prefix, final_user_turn

MODEL = "claude-sonnet-4-6"   # strong at structure; batch can use Haiku (see batch.py)
MAX_RETRIES = 3
CONFIDENCE_THRESHOLD = 0.70   # required-field confidence below this -> human review

SYSTEM_PROMPT = (
    "You are a careful bibliographic metadata extractor. Extract ONLY information "
    "explicitly present in the document. For any field that is absent, output null "
    "- never guess or fabricate. Always call the extraction tool. Provide a "
    "calibrated confidence in [0,1] per field: high when the value is stated "
    "verbatim, low when you had to interpret. Use document_type 'other' (with a "
    "document_type_detail) only when no specific category fits."
)


_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    """Lazily construct the client so importing this module needs no API key."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


@dataclass
class ExtractionResult:
    custom_id: str
    metadata: Optional[PublicationMetadata]      # None if it never validated
    raw_input: Optional[Dict]                    # last tool_use payload seen
    attempts: int
    resolved_by_retry: bool                      # a retry fixed an earlier failure
    needs_human_review: bool
    review_reasons: List[str] = field(default_factory=list)
    error_history: List[Dict] = field(default_factory=list)  # per-attempt classification


def _force_tool_kwargs(messages: List[Dict]) -> Dict:
    return dict(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": TOOL_NAME},  # force structured output
        messages=messages,
    )


def _first_tool_use(content) -> Optional[Dict]:
    for block in content:
        if block.type == "tool_use" and block.name == TOOL_NAME:
            return {"id": block.id, "input": block.input}
    return None


def _confidence_routing(meta: PublicationMetadata) -> Dict:
    """STEP 5: flag required fields whose confidence is below threshold."""
    conf = meta.field_confidence
    required = ["title", "authors", "document_type", "abstract_summary"]
    low = [f for f in required if getattr(conf, f) < CONFIDENCE_THRESHOLD]
    reasons = [f"low confidence on required field '{f}' ({getattr(conf, f):.2f})" for f in low]
    return {"needs_review": bool(low), "reasons": reasons}


def extract_document(custom_id: str, document_text: str) -> ExtractionResult:
    """Run the forced-tool extraction with a validation-retry loop."""
    messages: List[Dict] = few_shot_prefix()
    messages.append(final_user_turn(document_text))

    last_input: Optional[Dict] = None
    error_history: List[Dict] = []
    had_failure = False

    for attempt in range(1, MAX_RETRIES + 1):
        resp = get_client().messages.create(**_force_tool_kwargs(messages))
        tool_use = _first_tool_use(resp.content)
        if tool_use is None:
            # Should not happen with forced tool_choice, but handle defensively.
            error_history.append({"attempt": attempt, "error": "no tool_use returned"})
            return ExtractionResult(custom_id, None, last_input, attempt, False, True,
                                    ["model did not return the extraction tool"], error_history)

        last_input = tool_use["input"]

        try:
            meta = PublicationMetadata.model_validate(last_input)
        except ValidationError as err:
            had_failure = True
            classified = classify_validation_error(err)
            error_history.append({"attempt": attempt, **classified})

            if not classified["resolvable"]:
                # STEP 2: information genuinely absent / not fixable -> stop, route to human.
                return ExtractionResult(
                    custom_id, None, last_input, attempt, False, True,
                    ["non-resolvable validation error: " + "; ".join(classified["details"])],
                    error_history,
                )
            if attempt == MAX_RETRIES:
                break  # retries exhausted -> route to human below

            # Build the corrective follow-up: append the failed assistant turn,
            # then a tool_result carrying the exact validation error and a re-ask.
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use["id"],
                    "is_error": True,
                    "content": (
                        "Your extraction failed schema validation. Fix ONLY the "
                        "problems below and call the tool again. Do not invent values; "
                        "use null for anything not in the document.\n"
                        + "\n".join("- " + d for d in classified["details"])
                    ),
                }],
            })
            continue

        # Validated OK.
        routing = _confidence_routing(meta)
        return ExtractionResult(
            custom_id=custom_id,
            metadata=meta,
            raw_input=last_input,
            attempts=attempt,
            resolved_by_retry=had_failure,   # we recovered from an earlier failure
            needs_human_review=routing["needs_review"],
            review_reasons=routing["reasons"],
            error_history=error_history,
        )

    # Fell through: retries exhausted while still failing format validation.
    return ExtractionResult(
        custom_id, None, last_input, MAX_RETRIES, False, True,
        ["retries exhausted; last errors: "
         + "; ".join(error_history[-1].get("details", []))],
        error_history,
    )
