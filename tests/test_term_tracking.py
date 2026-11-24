"""Offline tests for the term-tracking pass and the helpers every pass shares.

These test plumbing only: parsing, anchoring, validation and the annotation format. Whether a
model actually finds the planted equivocation, and leaves `clean.txt` alone, is the job of the
end-to-end metamorphic test once scoring exists. No test here calls a model.
"""

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
    """Returns one fixed reply and remembers what it was asked."""

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
        "shifted_sense": "less water used overall",
        "explanation": "Total use only falls if efficiency means overall use.",
    }
    item.update(overrides)
    return item


def _payload(*equivocations: dict[str, Any], terms: list[Any] | None = None) -> str:
    if terms is None:
        terms = [
            {"term": "efficiency", "senses": ["less water per task", "less water used overall"]}
        ]
    return json.dumps({"terms": terms, "equivocations": list(equivocations)})


def _run(text: str, reply: str) -> TermReport:
    return track_terms(text, client=CannedClient(reply))


# anchor_quote


def test_anchor_quote_returns_offsets_of_the_quote() -> None:
    start, end = anchor_quote("alpha beta gamma", "beta")
    assert (start, end) == (6, 10)


def test_anchor_quote_counts_code_points_not_utf16_units_or_bytes() -> None:
    # U+1F600 is one code point, two UTF-16 units and four UTF-8 bytes.
    assert anchor_quote("\U0001f600 beta", "beta") == (2, 6)


def test_anchor_quote_does_not_normalise_whitespace() -> None:
    with pytest.raises(PassOutputError, match="not found"):
        anchor_quote("alpha  beta", "alpha beta")


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


def test_pass_output_error_is_a_value_error() -> None:
    assert issubclass(PassOutputError, ValueError)


# parse_json_object


def test_parse_json_object_reads_bare_json() -> None:
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_json_object_reads_one_fenced_block() -> None:
    reply = 'Here you go:\n```json\n{"a": 1}\n```\n'
    assert parse_json_object(reply) == {"a": 1}


def test_parse_json_object_rejects_two_fenced_blocks() -> None:
    reply = '```json\n{"a": 1}\n```\n```json\n{"b": 2}\n```'
    with pytest.raises(PassOutputError):
        parse_json_object(reply)


@pytest.mark.parametrize("reply", ["[1, 2]", '"text"', "not json at all", ""])
def test_parse_json_object_rejects_non_objects(reply: str) -> None:
    with pytest.raises(PassOutputError):
        parse_json_object(reply)


# Annotation


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


def test_annotation_holds_offsets_and_source() -> None:
    note = _note()
    assert (note.start, note.end, note.source) == (6, 10, "term_tracking")


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"start": -1}, "start"),
        ({"start": 10, "end": 6}, "end"),
        ({"source": ""}, "source"),
        ({"kind": ""}, "kind"),
    ],
)
def test_annotation_rejects_bad_fields(overrides: dict[str, Any], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        _note(**overrides)


def test_annotation_rejects_a_quote_whose_length_does_not_match_the_offsets() -> None:
    with pytest.raises(ValueError, match="quote"):
        _note(quote="beta", start=6, end=12)


def test_annotations_json_uses_fixed_key_names_and_a_format_version() -> None:
    data = json.loads(annotations_to_json([_note()]))
    assert data == {
        "format": ANNOTATION_FORMAT,
        "annotations": [
            {
                "kind": "equivocation",
                "quote": "beta",
                "start": 6,
                "end": 10,
                "note": "sense shifts",
                "source": "term_tracking",
            }
        ],
    }
    assert ANNOTATION_FORMAT == 1


def test_annotations_json_round_trips() -> None:
    notes = (_note(), _note(kind="other", note="second"))
    assert annotations_from_json(annotations_to_json(notes)) == notes


@pytest.mark.parametrize("version", [2, 1.0, True, "1", None])
def test_annotations_json_rejects_another_format(version: object) -> None:
    """Only the exact int 1 is format 1. In Python, 1.0 == 1 and True == 1."""
    with pytest.raises(ValueError, match="format"):
        annotations_from_json(json.dumps({"format": version, "annotations": []}))


def test_annotations_json_rejects_a_missing_key() -> None:
    raw = {"format": 1, "annotations": [{"kind": "x", "quote": "a", "start": 0, "end": 1}]}
    with pytest.raises(ValueError, match="note"):
        annotations_from_json(json.dumps(raw))


def test_annotations_json_rejects_an_unknown_key() -> None:
    item = json.loads(annotations_to_json([_note()]))
    item["annotations"][0]["extra"] = 1
    with pytest.raises(ValueError, match="extra"):
        annotations_from_json(json.dumps(item))


def test_annotations_json_rejects_an_unknown_top_level_key() -> None:
    item = json.loads(annotations_to_json([_note()]))
    item["extra"] = 1
    with pytest.raises(ValueError, match="extra"):
        annotations_from_json(json.dumps(item))


@pytest.mark.parametrize("value", ["6", True, 6.0])
def test_annotations_json_rejects_a_wrongly_typed_offset(value: object) -> None:
    item = json.loads(annotations_to_json([_note()]))
    item["annotations"][0]["start"] = value
    with pytest.raises(ValueError, match="start"):
        annotations_from_json(json.dumps(item))


# track_terms: the prompt


def test_track_terms_sends_the_text_and_the_system_prompt() -> None:
    client = CannedClient(_payload())
    track_terms(PLANTED, client=client)
    [(system, prompt)] = client.calls
    assert system == SYSTEM_PROMPT
    assert PLANTED in prompt


def test_track_terms_accepts_another_system_prompt() -> None:
    client = CannedClient(_payload())
    track_terms(PLANTED, client=client, system_prompt="variant")
    assert client.calls[0][0] == "variant"


def test_system_prompt_defines_equivocation_and_its_exclusions() -> None:
    lowered = SYSTEM_PROMPT.lower()
    for phrase in (
        "equivocation",
        "keeps apart",
        "part-whole",
        "figure",
        "literal",
        "exactly once",
        "json",
    ):
        assert phrase in lowered, phrase


def test_system_prompt_never_mentions_fixture_content() -> None:
    """A prompt tuned to the fixture would make the e2e test show less than it seems to."""
    lowered = SYSTEM_PROMPT.lower()
    for word in ("efficiency", "water", "toilet", "utility", "flush", "retrofit"):
        assert word not in lowered, word


# track_terms: a well-formed reply


def test_planted_equivocation_is_anchored_at_the_shifted_use() -> None:
    report = _run(PLANTED, _payload(_equivocation()))
    [note] = report.annotations
    assert note.kind == "equivocation"
    assert note.source == SOURCE == "term_tracking"
    assert PLANTED[note.start : note.end] == note.quote == SHIFTED_QUOTE


def test_annotation_note_names_the_term_both_senses_and_the_first_use() -> None:
    [note] = _run(PLANTED, _payload(_equivocation())).annotations
    for part in ("efficiency", "less water per task", "less water used overall", FIRST_QUOTE):
        assert part in note.note, part


def test_report_keeps_both_uses_and_the_terms() -> None:
    report = _run(PLANTED, _payload(_equivocation()))
    [eq] = report.equivocations
    assert isinstance(eq, Equivocation)
    assert PLANTED[eq.first_start : eq.first_end] == eq.first_quote == FIRST_QUOTE
    assert PLANTED[eq.shifted_start : eq.shifted_end] == eq.shifted_quote == SHIFTED_QUOTE
    assert eq.first_sense == "less water per task"
    assert eq.shifted_sense == "less water used overall"
    assert report.terms == (
        TrackedTerm(term="efficiency", senses=("less water per task", "less water used overall")),
    )


def test_no_equivocations_gives_no_annotations() -> None:
    terms = [{"term": "efficiency", "senses": ["less water per task"]}]
    report = _run(CLEAN, _payload(terms=terms))
    assert report.equivocations == ()
    assert report.annotations == ()
    assert report.terms[0].term == "efficiency"


def test_term_match_ignores_case() -> None:
    report = _run(PLANTED, _payload(_equivocation(term="Efficiency")))
    assert len(report.equivocations) == 1


def test_fenced_reply_is_accepted() -> None:
    reply = "```json\n" + _payload(_equivocation()) + "\n```"
    assert len(_run(PLANTED, reply).annotations) == 1


# track_terms: validation, nothing silently dropped


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"first_quote": "this sentence is not in the text"}, "not found"),
        ({"shifted_quote": "efficiency"}, "more than once"),
        ({"shifted_quote": "the utility's total use must therefore fall"}, "whole word"),
        ({"shifted_quote": FIRST_QUOTE}, "overlap"),
        ({"shifted_quote": "In this essay, " + FIRST_QUOTE}, "overlap"),
        ({"shifted_sense": "  Less water PER task "}, "are the same"),
        ({"explanation": ""}, "explanation"),
        ({"term": 7}, "field 'term'"),
    ],
)
def test_invalid_equivocation_raises(overrides: dict[str, Any], match: str) -> None:
    with pytest.raises(PassOutputError, match=match):
        _run(PLANTED, _payload(_equivocation(**overrides)))


def test_term_must_match_as_a_whole_word() -> None:
    text = "Inefficiency is costly here. Later on, efficiency means less overall."
    item = _equivocation(
        first_quote="Inefficiency is costly here", shifted_quote="efficiency means less overall"
    )
    with pytest.raises(PassOutputError, match="whole word in first_quote"):
        _run(text, _payload(item))


def test_term_with_a_regex_metacharacter_matches_literally() -> None:
    text = "C++ is fast. Later, C++ means the community, not the language."
    item = _equivocation(
        term="C++",
        first_quote="C++ is fast",
        shifted_quote="C++ means the community",
    )
    terms = [{"term": "C++", "senses": ["a language", "a community"]}]
    report = _run(text, _payload(item, terms=terms))
    assert report.equivocations[0].shifted_start == text.index("C++ means")


def test_equivocated_term_must_be_listed_in_terms() -> None:
    terms = [{"term": "total use", "senses": ["water used overall"]}]
    with pytest.raises(PassOutputError, match="not listed in 'terms'"):
        _run(PLANTED, _payload(_equivocation(), terms=terms))


def test_equivocated_term_must_be_listed_with_at_least_two_senses() -> None:
    terms = [{"term": "Efficiency", "senses": ["less water per task"]}]
    with pytest.raises(PassOutputError, match="two senses"):
        _run(PLANTED, _payload(_equivocation(), terms=terms))


def test_a_missing_field_raises() -> None:
    item = _equivocation()
    del item["shifted_sense"]
    with pytest.raises(PassOutputError, match="shifted_sense"):
        _run(PLANTED, _payload(item))


def test_one_bad_equivocation_fails_the_whole_reply() -> None:
    good = _equivocation()
    bad = _equivocation(first_quote="not in the text anywhere")
    with pytest.raises(PassOutputError):
        _run(PLANTED, _payload(good, bad))


@pytest.mark.parametrize(
    "reply",
    [
        "no json here",
        json.dumps({"terms": []}),
        json.dumps({"equivocations": []}),
        json.dumps({"terms": "efficiency", "equivocations": []}),
        json.dumps({"terms": [], "equivocations": {}}),
        json.dumps({"terms": [{"term": "efficiency"}], "equivocations": []}),
        json.dumps({"terms": [{"term": "efficiency", "senses": [3]}], "equivocations": []}),
        json.dumps({"terms": [{"term": "", "senses": ["x"]}], "equivocations": []}),
        json.dumps({"terms": [], "equivocations": ["efficiency"]}),
    ],
)
def test_malformed_payloads_raise(reply: str) -> None:
    with pytest.raises(PassOutputError):
        _run(PLANTED, reply)
