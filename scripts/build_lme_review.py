"""Emit a review sheet for labelling LongMemEval's superseded values by hand.

The old value is the one thing the benchmark does not provide and no rule
recovers reliably, so it gets labelled by a person. This lays each instance out
as a card -- the question, the gold updated value, the two dated sessions, and
ranked candidate sentences -- so confirming one takes seconds rather than
requiring a reader to hold a whole conversation in mind.

    python scripts/build_lme_review.py            # write the sheet
    python scripts/build_lme_review.py --stats    # coverage only
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from temvera.lme_bitemporal import load

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "longmemeval_oracle.json"
SHEET = ROOT / "data" / "lme-bitemporal-review.json"
# The sheet quotes the corpus, so it is a local working file. Only LABELS -- the
# superseded values we recover, which the benchmark does not ship -- are tracked.
LABELS = ROOT / "data" / "lme-bitemporal-labels.json"


def main() -> int:
    if not SOURCE.exists():
        print(f"FAIL: {SOURCE} not found; see REPRODUCING.md for the download")
        return 1
    pairs = load(SOURCE)
    if "--stats" in sys.argv:
        with_candidates = sum(1 for p in pairs if p.old_value_candidates)
        print(f"well-formed update pairs : {len(pairs)}")
        print(f"with ranked candidates   : {with_candidates}")
        spans = [(p.later.recorded_at - p.earlier.recorded_at).days for p in pairs]
        print(f"supersession gap in days : min {min(spans)}, median "
              f"{sorted(spans)[len(spans) // 2]}, max {max(spans)}")
        return 0

    cards = []
    for pair in pairs:
        cards.append({
            "question_id": pair.question_id,
            "question": pair.question,
            "new_value": pair.new_value,
            "recorded_old": pair.earlier.recorded_at.isoformat(),
            "recorded_new": pair.later.recorded_at.isoformat(),
            "asked_at": pair.asked_at.isoformat(),
            "candidates": list(pair.old_value_candidates),
            "earlier_session": list(pair.earlier.user_turns),
            "later_session": list(pair.later.user_turns),
            # filled in by a person; "" means unlabelled, "n/a" means the
            # instance carries no recoverable superseded value and is excluded.
            "old_value": "",
            "labelled_by": "",
        })
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    SHEET.write_text(json.dumps(cards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not LABELS.exists():
        LABELS.write_text(
            json.dumps(
                {"schema_version": 1,
                 "note": ("Superseded values recovered by hand from LongMemEval "
                          "knowledge-update instances. The benchmark ships only the "
                          "updated value; these make an as-of query answerable. "
                          "'n/a' marks an instance with no recoverable prior value."),
                 "labels": {}}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
    print(f"wrote {SHEET.relative_to(ROOT)}: {len(cards)} cards to label")
    print(f"labels go in {LABELS.relative_to(ROOT)} (tracked; the sheet is not)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
