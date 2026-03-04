from __future__ import annotations

from pathlib import PurePath

import pytest

from dpost_v2.application.ingestion.models.candidate import (
    Candidate,
    CandidatePathError,
    CandidateTransitionError,
)


def test_candidate_identity_is_deterministic_for_same_inputs() -> None:
    event = {
        "path": "./incoming/file.txt",
        "event_kind": "created",
        "observed_at": 123.0,
    }
    fs_facts = {"size": 10, "modified_at": 120.0, "fingerprint": "abc"}

    left = Candidate.from_event(event, fs_facts)
    right = Candidate.from_event(event, fs_facts)

    assert left.identity_token == right.identity_token
    assert left.source_path == str(PurePath("incoming/file.txt"))


def test_candidate_enrichment_is_immutable() -> None:
    candidate = Candidate.from_event(
        {"path": "incoming/file.txt", "event_kind": "modified", "observed_at": 123.0},
        {"size": 10, "modified_at": 120.0},
    )

    resolved = candidate.with_resolution(plugin_id="plug", processor_key="proc")

    assert candidate.plugin_id is None
    assert resolved.plugin_id == "plug"


def test_candidate_invalid_path_raises() -> None:
    with pytest.raises(CandidatePathError):
        Candidate.from_event(
            {"path": "", "event_kind": "created", "observed_at": 1.0},
            {},
        )


def test_candidate_route_requires_resolution() -> None:
    candidate = Candidate.from_event(
        {"path": "incoming/file.txt", "event_kind": "created", "observed_at": 1.0},
        {},
    )

    with pytest.raises(CandidateTransitionError):
        candidate.with_route(target_path="C:/dest/file.txt", route_tokens={"rule": "x"})
