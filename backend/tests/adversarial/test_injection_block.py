"""Adversarial corpus — CI gate for 100% block on known injection payloads.

Spec §11 Success Criteria #3: any failure here fails the build. The corpus also
contains a small bank of benign control queries that MUST NOT trigger any
pattern (false-positive guard).
"""
import json
from pathlib import Path

from kindred.facilitator.sanitizer import detect_injection_patterns

CORPUS_PATH = Path(__file__).parent / "injection_corpus.json"
CORPUS = json.loads(CORPUS_PATH.read_text())


def test_corpus_has_at_least_50_blocked_entries():
    blocked = [e for e in CORPUS if e["expected"] == "blocked"]
    assert len(blocked) >= 50, f"corpus too small: {len(blocked)} blocked entries"


def test_adversarial_corpus_100_percent_block():
    blocked_expected = sum(1 for e in CORPUS if e["expected"] == "blocked")
    blocked_total = 0
    missed: list[str] = []
    false_positives: list[str] = []
    for entry in CORPUS:
        hits = detect_injection_patterns(entry["payload"])
        if entry["expected"] == "blocked":
            if not hits:
                missed.append(f"{entry['id']}: {entry['payload']!r}")
            else:
                blocked_total += 1
        else:  # "allowed" — control
            if hits:
                false_positives.append(
                    f"{entry['id']}: hit={hits[0].pattern} on {entry['payload']!r}"
                )
    assert not missed, f"failed to block {len(missed)} payloads:\n  " + "\n  ".join(missed)
    assert blocked_total == blocked_expected
    assert not false_positives, (
        f"{len(false_positives)} false positives on clean payloads:\n  "
        + "\n  ".join(false_positives)
    )
