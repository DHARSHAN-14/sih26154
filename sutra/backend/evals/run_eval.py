"""
evals/run_eval.py — CLI evaluation runner for the 6-document golden set.
Usage:
    python evals/run_eval.py
    python evals/run_eval.py --ablation
"""
from __future__ import annotations
import json
import sys
import pathlib
from evals.ablations import run_ablation_comparison
from evals.report import format_ablation_table


def main():
    print("Loading golden set metadata from evals/golden/labels.json...")
    labels_file = pathlib.Path(__file__).parent / "golden" / "labels.json"
    if labels_file.exists():
        labels = json.loads(labels_file.read_text(encoding="utf-8"))
        print(f"Loaded {len(labels)} golden test documents:")
        for name, meta in labels.items():
            print(f"  - [{meta.get('doc_id')}] {meta.get('filename')} ({meta.get('type')})")
    print("")

    results = run_ablation_comparison()
    table = format_ablation_table(results)
    print(table)


if __name__ == "__main__":
    main()
