"""Tests for the term-tracking pass, its shared helpers, and the annotation format.

All offline. A canned client returns a fixed reply, so these tests check the plumbing: prompt
construction, parsing, anchoring and strict validation. Whether a real model finds the planted
equivocation, and leaves `clean.txt` alone, is the end-to-end metamorphic test's job.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from sophistry_eval.passes.common import PassOutputError, anchor_quote, parse_json_object
from sophistry_eval.passes.term_tracking import (
    SOURCE_NAME,
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
    text_sha256,
)

FIXTURES = Path(__file__).parent / "fixtures" / "equivocation"
PLANTED = (FIXTURES / "planted.txt").read_text()
CLEAN = (FIXTURES / "clean.txt").read_text()

FIRST_QUOTE = "In this essay, efficiency means using less water to accomplish the same task"
SHIFTED_QUOTE = (
    "Because efficiency means using less water, the utility's total use must therefore fall"
)


class CannedClient:
    """Returns one fixed reply and records what it was asked."""

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
        "shifted_sense": "less water in total",
        "explanation": "Per-task savings are treated as a fall in total use.",
    }
    item.update(overrides)
    return item


def _payload(*equivocations: dict[str, Any], terms: list[Any] | None = None) -> str:
    if terms is None:
        terms = [{"term": "efficiency", "senses": ["less water per task", "less water in total"]}]
    return json.dumps({"terms": terms, "equivocations": list(equivocations)})


# --- anchor_quote --------------------------------------------------------------------------


def test_anchor_quote_returns_offsets_of_the_unique_span() -> None:
    text = "alpha beta gamma"
    start, end = anchor_quote(text, "beta")
    assert (start, end) == (6, 10)
    assert text[start:end] == "beta"


def test_anchor_quote_rejects_a_missing_quote() -> None:
    with pytest.raises(PassOutputError, match="not found"):
        anchor_quote("alpha beta", "delta")


def test_anchor_quote_rejects_an_ambiguous_quote() -> None:
    with pytest.raises(PassOutputError, match="more than once"):
        anchor_quote("beta and beta", "beta")


def test_anchor_quote_counts_overlapping_occurrences_as_ambiguous() -> None:
    with pytest.raises(PassOutputError, match="more than once"):
        anchor_quote("aaa", "aa")


def test_anchor_quote_rejects_an_empty_quote() -> None:
    with pytest.raises(PassOutputError, match="empty"):
        anchor_quote("alpha", "")


# --- parse_json_object -------------------------------------------------------------------


def test_parse_json_object_accepts_bare_json() -> None:
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_json_object_accepts_one_fenced_block() -> None:
    assert parse_json_object('Here it is:\n```json\n{"a": 1}\n```\n') == {"a": 1}


def test_parse_json_object_rejects_two_fenced_blocks() -> None:
    with pytest.raises(PassOutputError):
        parse_json_object('```json\n{"a": 1}\n```\n```json\n{"b": 2}\n```')


@pytest.mark.parametrize("reply", ["[1, 2]", "not json", '"text"', ""])
def test_parse_json_object_rejects_non_objects(reply: str) -> None:
    with pytest.raises(PassOutputError):
        parse_json_object(reply)


# --- Annotation and its JSON form -------------------------------------------------------


def _annotation(**overrides: Any) -> Annotation:
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
    ("overrides", "message"),
    [
        ({"start": -1}, "start"),
        ({"start": 10, "end": 6}, "end"),
        ({"source": ""}, "source"),
        ({"end": 9}, "length"),
    ],
)
def test_annotation_rejects_bad_offsets_and_empty_source(
    overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _annotation(**overrides)


TEXT = "alpha beta gamma"


def test_annotation_json_round_trip_pins_key_names_format_and_text_hash() -> None:
    note = _annotation()
    encoded = annotations_to_json([note], text=TEXT)
    data = json.loads(encoded)
    assert set(data) == {"format", "text_sha256", "annotations"}
    assert data["format"] == ANNOTATION_FORMAT == 1
    assert data["text_sha256"] == text_sha256(TEXT)
    assert data["annotations"] == [
        {
            "kind": "equivocation",
            "quote": "beta",
            "start": 6,
            "end": 10,
            "note": "sense shifts",
            "source": "term_tracking",
        }
    ]
    assert annotations_from_json(encoded, text=TEXT) == (note,)


def test_text_sha256_hashes_utf8_bytes() -> None:
    assert text_sha256("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_offsets_count_code_points_not_utf16_units() -> None:
    text = "\U0001d400 beta"  # one astral character, two UTF-16 units
    note = _annotation(start=2, end=6)
    assert annotations_from_json(annotations_to_json([note], text=text), text=text) == (note,)


def test_annotation_json_refuses_to_write_offsets_that_miss_the_text() -> None:
    with pytest.raises(ValueError, match="does not match"):
        annotations_to_json([_annotation()], text="alpha delta gamma")


def test_annotation_json_rejects_a_different_text() -> None:
    encoded = annotations_to_json([_annotation()], text=TEXT)
    with pytest.raises(ValueError, match="text_sha256"):
        annotations_from_json(encoded, text=TEXT + " delta")


def _envelope(*items: object, fmt: object = 1) -> str:
    return json.dumps({"format": fmt, "text_sha256": text_sha256(TEXT), "annotations": list(items)})


def test_annotation_json_rejects_a_quote_that_misses_its_span() -> None:
    item = {"kind": "x", "quote": "beta", "start": 0, "end": 4, "note": "n", "source": "s"}
    with pytest.raises(ValueError, match="does not match"):
        annotations_from_json(_envelope(item), text=TEXT)


def test_annotation_json_rejects_unknown_keys() -> None:
    item = {"kind": "x", "quote": "beta", "start": 6, "end": 10, "note": "n", "source": "s"}
    item["extra"] = 1
    with pytest.raises(ValueError, match="extra"):
        annotations_from_json(_envelope(item), text=TEXT)


@pytest.mark.parametrize("fmt", [2, True, 1.0, "1", None])
def test_annotation_json_rejects_another_format(fmt: object) -> None:
    with pytest.raises(ValueError, match="format"):
        annotations_from_json(_envelope(fmt=fmt), text=TEXT)


def test_annotation_json_rejects_a_missing_key() -> None:
    item = {"kind": "x", "quote": "beta", "start": 6, "end": 10, "note": "n"}
    with pytest.raises(ValueError, match="source"):
        annotations_from_json(_envelope(item), text=TEXT)


@pytest.mark.parametrize(("key", "value"), [("start", "6"), ("start", True), ("note", 3)])
def test_annotation_json_rejects_a_wrong_type(key: str, value: object) -> None:
    item: dict[str, object] = {
        "kind": "x",
        "quote": "beta",
        "start": 6,
        "end": 10,
        "note": "n",
        "source": "s",
    }
    item[key] = value
    with pytest.raises(ValueError, match=key):
        annotations_from_json(_envelope(item), text=TEXT)


# --- track_terms: prompts ---------------------------------------------------------------


def test_track_terms_sends_the_text_and_the_system_prompt() -> None:
    client = CannedClient(_payload())
    track_terms(PLANTED, client=client)
    [(system, prompt)] = client.calls
    assert system == SYSTEM_PROMPT
    assert PLANTED in prompt


def test_track_terms_accepts_a_swapped_system_prompt() -> None:
    client = CannedClient(_payload())
    track_terms(PLANTED, client=client, system_prompt="variant")
    assert client.calls[0][0] == "variant"


def test_carriage_returns_are_refused_before_any_call() -> None:
    client = CannedClient(_payload())
    with pytest.raises(ValueError, match="newline"):
        track_terms(PLANTED.replace("\n", "\r\n"), client=client)
    assert client.calls == []


def test_system_prompt_defines_equivocation_and_its_exclusions() -> None:
    lowered = SYSTEM_PROMPT.lower()
    assert "equivocation" in lowered
    assert "inference" in lowered
    assert "distinction" in lowered  # an openly drawn distinction is not an equivocation
    assert "part-whole" in lowered  # a scope shift alone is a different flaw
    assert "meaning also changes" in lowered  # ...unless the sense shifts with it
    assert "polysemy" in lowered  # ordinary polysemy that carries no inference
    assert "figure" in lowered  # figures of speech are force...
    assert "literal" in lowered  # ...unless an inference reads them literally
    assert "exactly once" in lowered  # quotes must anchor uniquely
    assert "whole word" in lowered  # matches the validation's whole-word term check


# --- track_terms: the planted equivocation ------------------------------------------------


def test_planted_equivocation_anchors_at_the_shifted_use() -> None:
    report = track_terms(PLANTED, client=CannedClient(_payload(_equivocation())))
    [note] = report.annotations
    assert note.kind == "equivocation"
    assert note.source == SOURCE_NAME == "term_tracking"
    assert note.quote == SHIFTED_QUOTE
    assert PLANTED[note.start : note.end] == SHIFTED_QUOTE
    assert note.start == PLANTED.index(SHIFTED_QUOTE)


def test_annotation_note_names_the_term_both_senses_and_the_first_use() -> None:
    report = track_terms(PLANTED, client=CannedClient(_payload(_equivocation())))
    note = report.annotations[0].note
    for part in ("efficiency", "less water per task", "less water in total", FIRST_QUOTE):
        assert f'"{part}"' in note  # every part is quoted the same way


def test_annotation_note_does_not_use_python_repr_escapes() -> None:
    payload = _payload(_equivocation(shifted_sense="the utility's total use"))
    note = track_terms(PLANTED, client=CannedClient(payload)).annotations[0].note
    assert '"the utility\'s total use"' in note
    assert "\\" not in note


def test_report_keeps_both_uses_with_offsets_and_the_terms() -> None:
    report = track_terms(PLANTED, client=CannedClient(_payload(_equivocation())))
    assert isinstance(report, TermReport)
    assert report.terms == (
        TrackedTerm(term="efficiency", senses=("less water per task", "less water in total")),
    )
    [eq] = report.equivocations
    assert isinstance(eq, Equivocation)
    assert PLANTED[eq.first_start : eq.first_end] == FIRST_QUOTE
    assert PLANTED[eq.shifted_start : eq.shifted_end] == SHIFTED_QUOTE
    assert eq.first_sense == "less water per task"
    assert eq.shifted_sense == "less water in total"


def test_no_equivocations_gives_no_annotations() -> None:
    report = track_terms(CLEAN, client=CannedClient(_payload()))
    assert report.equivocations == ()
    assert report.annotations == ()
    assert report.terms[0].term == "efficiency"


def test_fenced_reply_is_accepted() -> None:
    reply = "```json\n" + _payload(_equivocation()) + "\n```"
    report = track_terms(PLANTED, client=CannedClient(reply))
    assert len(report.annotations) == 1


# --- track_terms: strict validation -------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"term": ""}, "term"),
        ({"first_sense": 3}, "first_sense"),
        ({"explanation": "  "}, "explanation"),
        ({"shifted_quote": "this sentence is not in the essay"}, "not found"),
        ({"first_quote": "efficiency"}, "more than once"),
        ({"shifted_quote": "the utility's total use must therefore fall"}, "term"),
        ({"shifted_quote": FIRST_QUOTE}, "same span"),
        ({"shifted_sense": "  Less water PER task "}, "senses"),
    ],
)
def test_invalid_equivocation_raises(overrides: dict[str, Any], message: str) -> None:
    client = CannedClient(_payload(_equivocation(**overrides)))
    with pytest.raises(PassOutputError, match=message):
        track_terms(PLANTED, client=client)


def test_missing_equivocation_field_raises() -> None:
    item = _equivocation()
    del item["explanation"]
    with pytest.raises(PassOutputError, match="explanation"):
        track_terms(PLANTED, client=CannedClient(_payload(item)))


def test_term_matches_case_insensitively() -> None:
    report = track_terms(PLANTED, client=CannedClient(_payload(_equivocation(term="Efficiency"))))
    assert len(report.equivocations) == 1


def test_term_must_appear_as_a_whole_word_not_inside_another() -> None:
    text = "The art of war is old. A part of the plan is new."
    item = _equivocation(
        term="art",
        first_quote="The art of war",
        first_sense="skill",
        shifted_quote="A part of the plan",
        shifted_sense="artwork",
    )
    with pytest.raises(PassOutputError, match="whole word"):
        track_terms(text, client=CannedClient(_payload(item)))


@pytest.mark.parametrize(
    "reply",
    [
        "not json at all",
        json.dumps({"terms": []}),
        json.dumps({"equivocations": []}),
        json.dumps({"terms": {}, "equivocations": []}),
        json.dumps({"terms": [], "equivocations": [["not", "an", "object"]]}),
        json.dumps({"terms": [{"term": "x", "senses": "one"}], "equivocations": []}),
        json.dumps({"terms": [{"term": "", "senses": ["a"]}], "equivocations": []}),
        json.dumps({"terms": [{"term": "x", "senses": [""]}], "equivocations": []}),
    ],
)
def test_malformed_payloads_raise(reply: str) -> None:
    with pytest.raises(PassOutputError):
        track_terms(PLANTED, client=CannedClient(reply))
