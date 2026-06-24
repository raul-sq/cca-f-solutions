"""
run_demo.py - End-to-end entry point for CCA-F Exercise 3.

Usage:
  python run_demo.py            # cheap: single-document extraction over the 3 samples
                                #   exercises Steps 1, 2, 3, 5 (a few API calls)
  python run_demo.py --batch    # builds the 100-doc batch payloads WITHOUT submitting
  python run_demo.py --batch --submit
                                # actually submits the 100-doc batch (Step 4; costs money,
                                # async - may take up to the 24h SLA, usually < 1h)

Requires ANTHROPIC_API_KEY in the environment and `pip install -r requirements.txt`.
"""

from __future__ import annotations

import argparse
import json

from extraction.documents import SAMPLE_DOCUMENTS, make_documents, gold_for
from extraction.extract import extract_document
from extraction.analysis import accuracy_report, routing_summary, format_report
from extraction.batch import run_batch


def run_single_doc_demo() -> None:
    """Steps 1, 2, 3, 5 on the three sample documents (inexpensive)."""
    print("=" * 70)
    print("SINGLE-DOCUMENT EXTRACTION DEMO (Steps 1, 2, 3, 5)")
    print("=" * 70)

    results = []
    extractions = {}
    for doc in SAMPLE_DOCUMENTS:
        res = extract_document(doc["id"], doc["text"])
        results.append(res)
        print(f"\n[{doc['id']}]  attempts={res.attempts}  "
              f"resolved_by_retry={res.resolved_by_retry}  "
              f"review={res.needs_human_review}")
        if res.metadata is not None:
            extractions[doc["id"]] = res.metadata
            print("  title         :", res.metadata.title)
            print("  authors       :", res.metadata.authors)
            print("  pub_year      :", res.metadata.publication_year)
            print("  document_type :", res.metadata.document_type,
                  f"(detail={res.metadata.document_type_detail})")
            print("  doi           :", res.metadata.doi)
            print("  funding_source:", res.metadata.funding_source)
            print("  citation_count:", res.metadata.citation_count)
        if res.review_reasons:
            print("  review_reasons:", res.review_reasons)
        if res.error_history:
            print("  error_history :", res.error_history)

    # Step 5: routing summary + accuracy against gold.
    print("\n" + "-" * 70)
    print("HUMAN-REVIEW ROUTING SUMMARY (Step 5)")
    print(json.dumps(routing_summary(results), indent=2))

    gold = gold_for(SAMPLE_DOCUMENTS)
    acc = accuracy_report(extractions, gold)
    print("\nACCURACY BY FIELD AND DOCUMENT TYPE (Step 5)")
    print(format_report(acc))


def run_batch_demo(submit: bool) -> None:
    """Step 4: build (and optionally submit) the 100-document batch."""
    print("=" * 70)
    print(f"BATCH PROCESSING (Step 4)  submit={submit}")
    print("=" * 70)
    report = run_batch(n=100, submit=submit)
    # Drop the in-memory handle before printing.
    report.pop("_outcome", None)
    print(json.dumps(report, indent=2))

    if submit and "final_succeeded" in report:
        # Accuracy analysis over what came back.
        outcome = run_batch  # placeholder; real outcome is inside report when submitted
        print("\nNote: see report['final_succeeded'] for recovered totals. "
              "Feed outcome.succeeded + gold_for(make_documents(100)) into "
              "accuracy_report() for the full Step 5 breakdown on the batch.")


def main() -> None:
    parser = argparse.ArgumentParser(description="CCA-F Exercise 3 demo")
    parser.add_argument("--batch", action="store_true", help="run the Step 4 batch path")
    parser.add_argument("--submit", action="store_true",
                        help="actually submit the batch (costs money; async)")
    args = parser.parse_args()

    if args.batch:
        run_batch_demo(submit=args.submit)
    else:
        run_single_doc_demo()


if __name__ == "__main__":
    main()
