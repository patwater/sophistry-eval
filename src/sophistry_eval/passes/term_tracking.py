"""The term-tracking pass: follow each key term across the text and flag equivocation.

Input: the text (with `\\n` newlines only) and a ModelClient. Output: a TermReport. The pass
reads no other pass's output, so it can be tested and re-run on its own.

Validation is strict. Any malformed item raises PassOutputError rather than being dropped,
so a bad reply fails loudly instead of quietly lowering the equivocation count.
"""

import re
from dataclasses import dataclass
from typing import Any

from sophistry_eval.client import ModelClient
from sophistry_eval.passes.common import PassOutputError, anchor_quote, parse_json_object
from sophistry_eval.types import Annotation

SOURCE_NAME = "term_tracking"

SYSTEM_PROMPT = """\
You audit the key terms of an argumentative text for equivocation.

Definitions:
- An equivocation is one term used in two different senses, where an inference in the \
argument goes through only if the two senses are treated as one.
- Do not flag a distinction the author draws openly between two senses or two quantities. \
Keeping them apart is good practice, not a flaw.
- Do not flag ordinary polysemy that carries no inference.
- Do not flag a figure of speech the reader is meant to read as a figure; figures are a \
matter of persuasive force, not of integrity. The exception: if an inference later depends \
on reading the figure literally, the shift between the figurative and the literal sense is \
an equivocation.
- A part-whole slide (composition or division) carries the same property between parts and \
the whole. A pure scope shift of that kind is not an equivocation. But when the move also \
changes the property itself, and a term carries it, the meaning also changes and you must \
report it as an equivocation. Example: "productivity" defined as output per hour, then \
treated as total output, so that a plant whose productivity rose is said to have produced \
more, though it ran fewer hours.

Report:
- "terms": the key terms the argument relies on, each with every sense in which the text \
uses it.
- "equivocations": only the shifts the argument relies on. For each, quote the first use \
and the shifted use verbatim. Each quote must contain the term as a whole word, spelled \
exactly as given under "term", and must be long enough to occur exactly once in the text. \
If the shift is carried only by a pronoun, a synonym, or an inflected form (such as a \
plural or an adjective), leave it out.

Reply with one JSON object and nothing else, in this shape:
{"terms": [{"term": "...", "senses": ["...", "..."]}],
 "equivocations": [{"term": "...", "first_quote": "...", "first_sense": "...", \
"shifted_quote": "...", "shifted_sense": "...", "explanation": "..."}]}
Use empty lists when there is nothing to report.
"""

_EQUIVOCATION_FIELDS = (
    "term",
    "first_quote",
    "first_sense",
    "shifted_quote",
    "shifted_sense",
    "explanation",
)


@dataclass(frozen=True)
class TrackedTerm:
    """A key term and every sense in which the text uses it."""

    term: str
    senses: tuple[str, ...]


@dataclass(frozen=True)
class Equivocation:
    """A term whose sense shifts between two uses that an inference treats as one.

    Offsets count code points into the text the pass was given.
    """

    term: str
    first_quote: str
    first_start: int
    first_end: int
    first_sense: str
    shifted_quote: str
    shifted_start: int
    shifted_end: int
    shifted_sense: str
    explanation: str


@dataclass(frozen=True)
class TermReport:
    """What the pass found. Only equivocations become annotations in v0.1."""

    terms: tuple[TrackedTerm, ...]
    equivocations: tuple[Equivocation, ...]
    annotations: tuple[Annotation, ...]


def build_prompt(text: str) -> str:
    """The user prompt for one text."""
    return f"Audit the key terms of this text.\n\n<text>\n{text}\n</text>"


def track_terms(
    text: str, *, client: ModelClient, system_prompt: str = SYSTEM_PROMPT
) -> TermReport:
    """Run the pass on `text`. Raises ValueError on `\\r`, PassOutputError on a bad reply."""
    if "\r" in text:
        msg = "text contains \\r; normalize newlines to \\n before running a pass"
        raise ValueError(msg)
    data = parse_json_object(client.complete(system_prompt, build_prompt(text)))
    terms = _parse_terms(data)
    equivocations = _parse_equivocations(data, text)
    annotations = tuple(_annotate(eq) for eq in equivocations)
    return TermReport(terms=terms, equivocations=equivocations, annotations=annotations)


def _list_field(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        msg = f"reply needs a list under {key!r}"
        raise PassOutputError(msg)
    return value


def _nonempty_str(item: dict[str, Any], key: str, where: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"{where}: {key} must be a non-empty string"
        raise PassOutputError(msg)
    return value


def _parse_terms(data: dict[str, Any]) -> tuple[TrackedTerm, ...]:
    terms: list[TrackedTerm] = []
    for index, item in enumerate(_list_field(data, "terms")):
        where = f"term {index}"
        if not isinstance(item, dict):
            msg = f"{where} is not an object"
            raise PassOutputError(msg)
        term = _nonempty_str(item, "term", where)
        senses = item.get("senses")
        if (
            not isinstance(senses, list)
            or not senses
            or not all(isinstance(s, str) and s.strip() for s in senses)
        ):
            msg = f"{where}: senses must be a non-empty list of non-empty strings"
            raise PassOutputError(msg)
        terms.append(TrackedTerm(term=term, senses=tuple(senses)))
    return tuple(terms)


def _contains_word(quote: str, term: str) -> bool:
    """Case-insensitive whole-word match, so "art" does not match inside "part"."""
    pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
    return re.search(pattern, quote, flags=re.IGNORECASE) is not None


def _normalize(sense: str) -> str:
    return " ".join(sense.lower().split())


def _parse_equivocations(data: dict[str, Any], text: str) -> tuple[Equivocation, ...]:
    found: list[Equivocation] = []
    for index, item in enumerate(_list_field(data, "equivocations")):
        where = f"equivocation {index}"
        if not isinstance(item, dict):
            msg = f"{where} is not an object"
            raise PassOutputError(msg)
        fields = {key: _nonempty_str(item, key, where) for key in _EQUIVOCATION_FIELDS}
        term = fields["term"]
        first_start, first_end = anchor_quote(text, fields["first_quote"])
        shifted_start, shifted_end = anchor_quote(text, fields["shifted_quote"])
        for key in ("first_quote", "shifted_quote"):
            if not _contains_word(fields[key], term):
                msg = f"{where}: {key} does not contain the term {term!r} as a whole word"
                raise PassOutputError(msg)
        if (first_start, first_end) == (shifted_start, shifted_end):
            msg = f"{where}: both quotes are the same span"
            raise PassOutputError(msg)
        if _normalize(fields["first_sense"]) == _normalize(fields["shifted_sense"]):
            msg = f"{where}: the two senses are the same, so there is no shift"
            raise PassOutputError(msg)
        found.append(
            Equivocation(
                term=term,
                first_quote=fields["first_quote"],
                first_start=first_start,
                first_end=first_end,
                first_sense=fields["first_sense"],
                shifted_quote=fields["shifted_quote"],
                shifted_start=shifted_start,
                shifted_end=shifted_end,
                shifted_sense=fields["shifted_sense"],
                explanation=fields["explanation"],
            )
        )
    return tuple(found)


def _annotate(eq: Equivocation) -> Annotation:
    note = (
        f'"{eq.term}" shifts from "{eq.first_sense}" (first use: "{eq.first_quote}") '
        f'to "{eq.shifted_sense}" here. {eq.explanation}'
    )
    return Annotation(
        kind="equivocation",
        quote=eq.shifted_quote,
        start=eq.shifted_start,
        end=eq.shifted_end,
        note=note,
        source=SOURCE_NAME,
    )
