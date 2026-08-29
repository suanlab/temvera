"""The documentation quotes in the paper are checked against the packages.

The claims-vs-documentation table contrasts what each system advertises with
what we measured, which only carries weight if the advertised half is verbatim.
Quotes are therefore re-extracted from the installed distributions rather than
trusted, so paraphrase drift fails the suite. Systems that ran in isolated
interpreters are not installed here; their quotes carry a recorded METADATA
sha256 for offline checking instead.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
from pathlib import Path

import pytest

CLAIMS = Path(__file__).resolve().parents[1] / "data" / "literature" / "system-claims-2026-08-20.json"


def _record() -> dict:
    return json.loads(CLAIMS.read_text(encoding="utf-8"))


def test_claim_file_covers_every_compared_system() -> None:
    systems = set(_record()["systems"])
    assert systems == {"mem0", "langmem", "graphiti", "cognee", "hindsight"}


@pytest.mark.parametrize("name", ["mem0", "graphiti"])
def test_installed_package_still_contains_its_quotes(name: str) -> None:
    entry = _record()["systems"][name]
    dist = md.distribution(entry["package"])
    assert dist.version == entry["version"], "quotes were captured from another version"
    text = dist.read_text("METADATA") or ""
    assert hashlib.sha256(text.encode()).hexdigest() == entry["metadata_sha256"]
    normalised = " ".join(text.split())
    for quote in entry["quotes"]:
        assert quote in normalised, f"{name} no longer documents: {quote[:60]}"


def test_quotes_are_stored_whitespace_normalised() -> None:
    for name, entry in _record()["systems"].items():
        for quote in entry["quotes"]:
            assert quote == " ".join(quote.split()), f"{name} quote is not normalised"
            assert quote.strip(), f"{name} has an empty quote"


DELETION = CLAIMS.parent / "deletion-api-2026-08-20.json"


def _deletion() -> dict:
    return json.loads(DELETION.read_text(encoding="utf-8"))


def test_no_compared_system_exposes_predicate_scoped_deletion() -> None:
    """The claim the paper draws from this file, asserted rather than narrated."""
    scoped = {
        name: entry["predicate_scoped"]
        for name, entry in _deletion()["systems"].items()
        if entry["predicate_scoped"]
    }
    assert not scoped, f"a system gained predicate-scoped deletion: {scoped}"


def test_recorded_deletion_signatures_match_the_installed_packages() -> None:
    import inspect

    from graphiti_core import Graphiti
    from mem0 import Memory

    live = {
        "mem0": {
            "Memory.delete": str(inspect.signature(Memory.delete)),
            "Memory.delete_all": str(inspect.signature(Memory.delete_all)),
            "Memory.reset": str(inspect.signature(Memory.reset)),
        },
        "graphiti": {"Graphiti.remove_episode": str(inspect.signature(Graphiti.remove_episode))},
    }
    systems = _deletion()["systems"]
    for name, operations in live.items():
        assert systems[name]["operations"] == operations, f"{name} deletion API changed"
