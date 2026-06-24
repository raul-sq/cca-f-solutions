"""
batch.py - Batch processing strategy (STEP 4).

  - Submit a batch of 100 documents via the Message Batches API.
  - Poll until processing ends; collect results keyed by custom_id.
  - Handle failures (errored/expired) by custom_id.
  - Resubmit failed documents WITH modifications - oversized documents are
    chunked and merged.
  - Measure total processing time against SLA constraints.

Safety: nothing here hits the network until you call run_batch(..., submit=True).
With submit=False (default) it builds and validates the request payloads only.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pydantic import ValidationError

from .schema import (
    EXTRACTION_TOOL,
    TOOL_NAME,
    PublicationMetadata,
)
from .fewshot import few_shot_prefix, final_user_turn
from .extract import SYSTEM_PROMPT, get_client
from .documents import Document, make_documents

BATCH_MODEL = "claude-haiku-4-5-20251001"  # cheap + fast; batch is 50% off on top
MAX_TOKENS = 1024

# SLA constraints (Step 4). The API's hard ceiling is 24h; we also set an
# internal target the pipeline is expected to beat.
SLA_HARD_SECONDS = 24 * 60 * 60   # 24h API maximum
SLA_TARGET_SECONDS = 60 * 60      # 1h internal target

# Heuristic: documents whose text exceeds this many characters are treated as
# "oversized" and chunked on resubmission.
OVERSIZE_CHARS = 40_000
CHUNK_CHARS = 18_000


# ---------------------------------------------------------------------------
# Request construction
# ---------------------------------------------------------------------------

def build_request(custom_id: str, document_text: str) -> Dict:
    """One Batches API request: same params shape as messages.create()."""
    messages = few_shot_prefix()
    messages.append(final_user_turn(document_text))
    return {
        "custom_id": custom_id,
        "params": {
            "model": BATCH_MODEL,
            "max_tokens": MAX_TOKENS,
            "system": SYSTEM_PROMPT,
            "tools": [EXTRACTION_TOOL],
            "tool_choice": {"type": "tool", "name": TOOL_NAME},
            "messages": messages,
        },
    }


# ---------------------------------------------------------------------------
# Oversized-document chunking (used on resubmission)
# ---------------------------------------------------------------------------

def chunk_text(text: str, size: int = CHUNK_CHARS) -> List[str]:
    return [text[i:i + size] for i in range(0, len(text), size)]


def merge_chunk_extractions(parts: List[PublicationMetadata]) -> Optional[Dict]:
    """Merge per-chunk extractions into one record.

    Strategy: take the first non-null scalar across chunks; union list fields;
    keep the highest per-field confidence. Returns a plain dict (re-validated by
    the caller).
    """
    if not parts:
        return None
    merged: Dict[str, object] = {}
    scalars = ["title", "publication_year", "document_type", "document_type_detail",
               "doi", "funding_source", "abstract_summary", "citation_count"]
    for f in scalars:
        merged[f] = next((getattr(p, f) for p in parts if getattr(p, f) is not None), None)
    # Union list fields preserving order.
    authors: List[str] = []
    keywords: List[str] = []
    for p in parts:
        authors += [a for a in p.authors if a not in authors]
        keywords += [k for k in p.keywords if k not in keywords]
    merged["authors"] = authors
    merged["keywords"] = keywords
    # Highest confidence per field.
    conf_fields = parts[0].field_confidence.model_dump().keys()
    merged["field_confidence"] = {
        cf: max(getattr(p.field_confidence, cf) for p in parts) for cf in conf_fields
    }
    return merged


# ---------------------------------------------------------------------------
# Results handling
# ---------------------------------------------------------------------------

@dataclass
class BatchOutcome:
    succeeded: Dict[str, PublicationMetadata] = field(default_factory=dict)
    invalid: Dict[str, str] = field(default_factory=dict)   # validated -> failed locally
    failed: Dict[str, str] = field(default_factory=dict)    # API errored/expired/canceled
    elapsed_seconds: float = 0.0
    within_target: bool = False
    within_hard_sla: bool = False


def _parse_succeeded_message(message) -> PublicationMetadata:
    """Pull the tool_use input out of a succeeded batch message and validate it."""
    for block in message.content:
        if block.type == "tool_use" and block.name == TOOL_NAME:
            return PublicationMetadata.model_validate(block.input)
    raise ValueError("no tool_use block in succeeded message")


def submit_and_wait(requests: List[Dict], poll_seconds: int = 30) -> BatchOutcome:
    """Submit one batch, poll to completion, and collect results by custom_id."""
    client = get_client()
    start = time.monotonic()

    batch = client.messages.batches.create(requests=requests)
    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        time.sleep(poll_seconds)

    outcome = BatchOutcome()
    for entry in client.messages.batches.results(batch.id):
        cid = entry.custom_id
        rtype = entry.result.type
        if rtype == "succeeded":
            try:
                outcome.succeeded[cid] = _parse_succeeded_message(entry.result.message)
            except (ValidationError, ValueError) as e:
                outcome.invalid[cid] = str(e)
        else:
            # errored | expired | canceled -> needs handling by custom_id
            err = getattr(entry.result, "error", None)
            outcome.failed[cid] = f"{rtype}: {err}"

    outcome.elapsed_seconds = time.monotonic() - start
    outcome.within_target = outcome.elapsed_seconds <= SLA_TARGET_SECONDS
    outcome.within_hard_sla = outcome.elapsed_seconds <= SLA_HARD_SECONDS
    return outcome


def resubmit_failed(failed_ids: List[str], docs_by_id: Dict[str, Document],
                    poll_seconds: int = 30) -> Dict[str, PublicationMetadata]:
    """Resubmit failed docs WITH modifications: chunk the oversized ones, then merge.

    Oversized docs become several chunk-requests (custom_id 'cid#chunkN'); other
    failures are simply retried once as-is.
    """
    client = get_client()
    requests: List[Dict] = []
    chunk_owner: Dict[str, str] = {}  # chunk custom_id -> original custom_id

    for cid in failed_ids:
        text = docs_by_id[cid]["text"]
        if len(text) > OVERSIZE_CHARS:
            for j, part in enumerate(chunk_text(text)):
                ccid = f"{cid}#chunk{j}"
                chunk_owner[ccid] = cid
                requests.append(build_request(ccid, part))
        else:
            requests.append(build_request(cid, text))

    if not requests:
        return {}

    outcome = submit_and_wait(requests, poll_seconds=poll_seconds)

    # Reassemble: group chunk extractions back under their original custom_id.
    grouped: Dict[str, List[PublicationMetadata]] = {}
    resolved: Dict[str, PublicationMetadata] = {}
    for cid, meta in outcome.succeeded.items():
        owner = chunk_owner.get(cid, cid)
        grouped.setdefault(owner, []).append(meta)

    for owner, parts in grouped.items():
        if len(parts) == 1 and owner not in chunk_owner.values():
            resolved[owner] = parts[0]
        else:
            merged = merge_chunk_extractions(parts)
            if merged is not None:
                try:
                    resolved[owner] = PublicationMetadata.model_validate(merged)
                except ValidationError:
                    pass  # still unresolved -> caller routes to human review
    return resolved


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_batch(n: int = 100, submit: bool = False, poll_seconds: int = 30) -> Dict:
    """Build (and optionally submit) a batch of n documents end to end."""
    docs = make_documents(n)
    docs_by_id = {d["id"]: d for d in docs}
    requests = [build_request(d["id"], d["text"]) for d in docs]

    report: Dict[str, object] = {
        "requested": len(requests),
        "oversized_docs": [d["id"] for d in docs if len(d["text"]) > OVERSIZE_CHARS],
        "model": BATCH_MODEL,
    }

    if not submit:
        # Dry run: payloads built and ready; no network call.
        report["mode"] = "dry_run"
        report["note"] = "Pass submit=True to actually create the batch via the API."
        return report

    outcome = submit_and_wait(requests, poll_seconds=poll_seconds)
    report["mode"] = "submitted"
    report["succeeded"] = len(outcome.succeeded)
    report["invalid_local"] = list(outcome.invalid)
    report["failed_api"] = list(outcome.failed)
    report["elapsed_seconds"] = round(outcome.elapsed_seconds, 1)
    report["within_target_sla"] = outcome.within_target
    report["within_hard_sla"] = outcome.within_hard_sla

    # Handle failures by custom_id: resubmit with chunking.
    to_fix = list(outcome.failed) + list(outcome.invalid)
    if to_fix:
        recovered = resubmit_failed(to_fix, docs_by_id, poll_seconds=poll_seconds)
        report["recovered_after_resubmit"] = list(recovered)
        report["still_unresolved"] = [c for c in to_fix if c not in recovered]
        outcome.succeeded.update(recovered)

    report["final_succeeded"] = len(outcome.succeeded)
    report["_outcome"] = outcome  # in-memory handle for downstream analysis
    return report
