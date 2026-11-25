"""Offline tests for the term-tracking pass and the shared pass helpers.

These test plumbing only: parsing, anchoring, validation and the annotation format. Whether a
model actually finds the planted equivocation, and leaves `clean.txt` alone, is the job of the
end-to-end metamorphic test once scoring exists.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from sophistry_eval.passes.common import PassOutputError, anchor_quote, parse_json_object
from sophistry_eval.passes.term_tracking import (
    SOURCE,
    SYSTEM_PROMPT,
    Equivocation,
    TermReport,
    TrackedTerm,
    track_terms,
)
from sophistry_eval.types import (
    ANNOTATION_FORMAT,
    Annotation,
    annotations_from_json,
    annotations_to_json,
)

FIXTURES = Path(__file__).parent / "fixtures" / "equivocation"
PLANTED = (FIXTURES / "planted.txt").read_text()
CLEAN = (FIXTURES / "clean.txt").read_text()

FIRST_QUOTE = "efficiency means using less water to accomplish the same task"
SHIFTED_QUOTE = (
    "Because efficiency means using less water, the utility's total use must therefore fall"
)


class CannedClient:
    """Returns one fixed reply and remembers every prompt it was given."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        return self.reply


def _equivocation(**overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "term": "efficiency",
        "first_quote": FIRST_QUOTE,
        "first_sense": "less water per task",
        "shifted_quote": SHIFTED_QUOTE,
        "shifted_sense": "less water used in total",
        "explanation": "Total use only falls if per-task efficiency is read as total use.",
    }
    item.update(overrides)
    return item


def _reply(equivocations: list[dict[str, Any]] | None = None, **extra: Any) -> str:
    payload: dict[str, Any] = {
        "terms": [{"term": "efficiency", "senses": ["less water per task", "less water overall"]}],
        "equivocations": [_equivocation()] if equivocations is None else equivocations,
    }
    payload.update(extra)
    return json.dumps(payload)


def _run(reply: str, text: str = PLANTED) -> TermReport:
    return track_terms(text, client=CannedClient(reply))


# anchor_quote


def test_anchor_quote_returns_offsets_of_the_unique_span() -> None:
    text = "alpha beta gamma"
    start, end = anchor_quote(text, "beta")
    assert (start, end) == (6, 10)
    assert text[start:end] == "beta"


def test_anchor_quote_counts_unicode_code_points() -> None:
    """Offsets are code points of the exact input string, so a non-BMP character counts as 1."""
    text = "\N{GRINNING FACE} beta"
    assert anchor_quote(text, "beta") == (2, 6)


def test_anchor_quote_rejects_a_missing_quote() -> None:
    with pytest.raises(PassOutputError, match="not found"):
        anchor_quote("alpha beta", "delta")


def test_anchor_quote_rejects_an_ambiguous_quote() -> None:
    with pytest.raises(PassOutputError, match="more than once"):
        anchor_quote("beta and beta", "beta")


def test_anchor_quote_rejects_overlapping_repeats_as_ambiguous() -> None:
    with pytest.raises(PassOutputError, match="more than once"):
        anchor_quote("aaa", "aa")


def test_anchor_quote_rejects_an_empty_quote() -> None:
    with pytest.raises(PassOutputError, match="empty"):
        anchor_quote("alpha", "")


# parse_json_object


def test_parse_json_object_accepts_bare_json() -> None:
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_json_object_accepts_one_fenced_block() -> None:
    reply = 'Here you go.\n```json\n{"a": 1}\n```\n'
    assert parse_json_object(reply) == {"a": 1}


def test_parse_json_object_rejects_two_fenced_blocks() -> None:
    reply = '```json\n{"a": 1}\n```\n```json\n{"b": 2}\n```'
    with pytest.raises(PassOutputError):
        parse_json_object(reply)


@pytest.mark.parametrize("reply", ["[1, 2]", '"text"', "not json at all", ""])
def test_parse_json_object_rejects_non_objects(reply: str) -> None:
    with pytest.raises(PassOutputError):
        parse_json_object(reply)


# Annotation and its JSON form


def _note(**overrides: Any) -> Annotation:
    fields: dict[str, Any] = {
        "kind": "equivocation",
        "quote": "beta",
        "start": 6,
        "end": 10,
        "note": "sense shifts",
        "source": "term_tracking",
    }
    fields.update(overrides)
    return Annotation(**fields)


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"start": -1, "end": 3}, "start"),
        ({"start": 10, "end": 6}, "end"),
        ({"source": ""}, "source"),
        ({"kind": ""}, "kind"),
        ({"end": 11}, "quote"),
    ],
)
def test_annotation_rejects_bad_fields(overrides: dict[str, Any], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        _note(**overrides)


TEXT = "alpha beta gamma"
TEXT_SHA256 = hashlib.sha256(TEXT.encode("utf-8")).hexdigest()


def _envelope(*items: dict[str, Any], fmt: Any = 1, sha: Any = TEXT_SHA256) -> str:
    return json.dumps({"format": fmt, "text_sha256": sha, "annotations": list(items)})


def test_annotation_json_round_trip_uses_fixed_key_names() -> None:
    notes = (_note(), _note(quote="gamma", start=11, end=16, note="second"))
    encoded = annotations_to_json(notes, text=TEXT)
    data = json.loads(encoded)
    assert set(data) == {"format", "text_sha256", "annotations"}
    assert data["format"] == ANNOTATION_FORMAT == 1
    assert data["text_sha256"] == TEXT_SHA256
    assert set(data["annotations"][0]) == {"kind", "quote", "start", "end", "note", "source"}
    assert annotations_from_json(encoded) == notes
    assert annotations_from_json(encoded, text=TEXT) == notes


def test_annotation_json_rejects_a_different_text() -> None:
    encoded = annotations_to_json((_note(),), text=TEXT)
    with pytest.raises(ValueError, match="text_sha256"):
        annotations_from_json(encoded, text=TEXT + " delta")


def test_annotation_json_rejects_another_format() -> None:
    with pytest.raises(ValueError, match="format"):
        annotations_from_json(_envelope(fmt=2))


def test_annotation_json_rejects_a_missing_hash() -> None:
    with pytest.raises(ValueError, match="text_sha256"):
        annotations_from_json(json.dumps({"format": 1, "annotations": []}))


def test_annotation_json_rejects_a_missing_key() -> None:
    item = {"kind": "k", "quote": "q", "start": 0, "end": 1, "note": "n"}
    with pytest.raises(ValueError, match="source"):
        annotations_from_json(_envelope(item))


@pytest.mark.parametrize(("field", "value"), [("start", "0"), ("start", True), ("end", False)])
def test_annotation_json_rejects_a_wrong_type(field: str, value: Any) -> None:
    item: dict[str, Any] = {"kind": "k", "quote": "q", "start": 0, "end": 1, "note": "n"}
    item["source"] = "s"
    item[field] = value
    with pytest.raises(ValueError, match=field):
        annotations_from_json(_envelope(item))


# track_terms: the prompt


def test_track_terms_sends_the_text_and_the_system_prompt() -> None:
    client = CannedClient(_reply())
    track_terms(PLANTED, client=client)
    assert len(client.calls) == 1
    system, prompt = client.calls[0]
    assert system == SYSTEM_PROMPT
    assert PLANTED in prompt


def test_system_prompt_defines_equivocation_and_its_exclusions() -> None:
    lowered = SYSTEM_PROMPT.lower()
    assert "equivocation" in lowered
    assert "distinction" in lowered
    assert "part-whole" in lowered
    assert "figures of speech on which no inference depends" in lowered
    assert "exactly once" in lowered


def test_track_terms_accepts_a_swapped_system_prompt() -> None:
    client = CannedClient(_reply())
    track_terms(PLANTED, client=client, system_prompt="variant")
    assert client.calls[0][0] == "variant"


# track_terms: the report


def test_planted_equivocation_anchors_at_the_shifted_use() -> None:
    report = _run(_reply())
    assert len(report.annotations) == 1
    note = report.annotations[0]
    assert note.kind == "equivocation"
    assert note.source == SOURCE == "term_tracking"
    assert note.quote == SHIFTED_QUOTE
    assert PLANTED[note.start : note.end] == SHIFTED_QUOTE
    assert "efficiency" in note.note
    assert "less water per task" in note.note
    assert "less water used in total" in note.note


def test_report_keeps_both_uses_and_the_terms() -> None:
    report = _run(_reply())
    assert report.terms == (
        TrackedTerm(term="efficiency", senses=("less water per task", "less water overall")),
    )
    (eq,) = report.equivocations
    assert isinstance(eq, Equivocation)
    assert PLANTED[eq.first_start : eq.first_end] == FIRST_QUOTE
    assert PLANTED[eq.shifted_start : eq.shifted_end] == SHIFTED_QUOTE
    assert eq.first_sense == "less water per task"
    assert eq.shifted_sense == "less water used in total"


def test_no_equivocations_gives_no_annotations() -> None:
    report = _run(_reply(equivocations=[]), text=CLEAN)
    assert report.equivocations == ()
    assert report.annotations == ()
    assert report.terms[0].term == "efficiency"


def test_fenced_reply_is_accepted() -> None:
    report = _run(f"```json\n{_reply()}\n```")
    assert len(report.annotations) == 1


# track_terms: validation, nothing silently dropped


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"first_quote": "not in the text at all, efficiency"}, "not found"),
        ({"first_quote": "efficiency means using less water"}, "more than once"),
        ({"shifted_quote": "the utility's total use must therefore fall"}, "whole word"),
        ({"shifted_quote": FIRST_QUOTE}, "overlap"),
        (
            {
                "first_quote": "Because efficiency means using less water,",
                "shifted_quote": "efficiency means using less water, the utility's total use",
            },
            "overlap",
        ),
        (
            {
                "term": "fund",
                "first_quote": "Efficiency programs are worth funding",
                "shifted_quote": "the utility fund retrofits and treat",
            },
            "whole word",
        ),
        ({"shifted_sense": "  Less water PER task "}, "senses"),
        ({"term": ""}, "term"),
        ({"explanation": 3}, "explanation"),
    ],
)
def test_invalid_equivocation_raises(overrides: dict[str, Any], match: str) -> None:
    with pytest.raises(PassOutputError, match=match):
        _run(_reply(equivocations=[_equivocation(**overrides)]))


def test_missing_equivocation_field_raises() -> None:
    item = _equivocation()
    del item["shifted_sense"]
    with pytest.raises(PassOutputError, match="shifted_sense"):
        _run(_reply(equivocations=[item]))


def test_term_matches_case_insensitively() -> None:
    report = _run(_reply(equivocations=[_equivocation(term="Efficiency")]))
    assert len(report.equivocations) == 1


@pytest.mark.parametrize(
    "reply",
    [
        json.dumps({"equivocations": []}),
        json.dumps({"terms": [], "equivocations": {}}),
        json.dumps({"terms": [{"term": "x"}], "equivocations": []}),
        json.dumps({"terms": [{"term": "x", "senses": []}], "equivocations": []}),
        json.dumps({"terms": [{"term": "x", "senses": [1]}], "equivocations": []}),
        json.dumps({"terms": [], "equivocations": ["not an object"]}),
    ],
)
def test_malformed_payloads_raise(reply: str) -> None:
    with pytest.raises(PassOutputError):
        _run(reply)
