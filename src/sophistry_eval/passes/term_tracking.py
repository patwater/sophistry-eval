"""Term tracking: follow each key term across the text and flag equivocation.

An equivocation is one term used in two different senses, where an inference goes through only
if the two senses are treated as one. See `Docs/rubrics.md`, Term tracking.

The pass reads only its input text, so its result depends only on the text, the system prompt,
the model and the call settings, and can be cached by input hash.
"""

import re
from dataclasses import dataclass
from typing import Any

from sophistry_eval.client import ModelClient
from sophistry_eval.passes.common import PassOutputError, anchor_quote, parse_json_object
from sophistry_eval.types import Annotation

SOURCE = "term_tracking"
"""The `source` this pass writes on its annotations."""

SYSTEM_PROMPT = """\
You audit the conceptual integrity of a piece of writing by tracking its key terms.

1. List the key terms the argument relies on. For each, list every sense in which the text \
uses it.
2. Report every equivocation. An equivocation is one term used in two different senses, \
where an inference in the argument goes through only if the two senses are treated as one.

Do not report:
- a distinction the author draws openly between two senses or two quantities;
- ordinary polysemy that carries no inference;
- figures of speech on which no inference depends. Their craft is a matter of persuasive \
force, not integrity. A figure that is later read literally to carry an inference is still \
an equivocation if the inference depends on it.

A shift in the scope of a property, from a part to the whole (for example from one device to \
a whole community), is a part-whole slide, not an equivocation, unless the term's meaning \
also changes. Do not report a part-whole slide here.

Report an equivocation only when the term itself, as a whole word, appears in both quotes. \
Each quote must be copied verbatim from the text and be long enough to occur exactly once in \
it. The two quotes must not overlap.

Reply with one JSON object and nothing else, in this shape:
{
  "terms": [{"term": "...", "senses": ["...", "..."]}],
  "equivocations": [{
    "term": "...",
    "first_quote": "...", "first_sense": "...",
    "shifted_quote": "...", "shifted_sense": "...",
    "explanation": "how the argument relies on treating the two senses as one"
  }]
}
Use an empty list when there are no equivocations.
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
    """One term used in two senses, with both uses anchored in the text."""

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
    """The output of the term-tracking pass."""

    terms: tuple[TrackedTerm, ...]
    equivocations: tuple[Equivocation, ...]
    annotations: tuple[Annotation, ...]


def build_prompt(text: str) -> str:
    """The user prompt for one text."""
    return f"Audit the key terms of this text.\n\n<text>\n{text}\n</text>"


def track_terms(
    text: str, *, client: ModelClient, system_prompt: str = SYSTEM_PROMPT
) -> TermReport:
    """Run the term-tracking pass on `text`. Raises `PassOutputError` on an unusable reply."""
    payload = parse_json_object(client.complete(system_prompt, build_prompt(text)))
    terms = _parse_terms(payload.get("terms"))
    equivocations = _parse_equivocations(payload.get("equivocations"), text)
    annotations = tuple(_annotate(eq) for eq in equivocations)
    return TermReport(terms=terms, equivocations=equivocations, annotations=annotations)


def _require_str(item: dict[str, Any], name: str, where: str) -> str:
    if name not in item:
        msg = f"{where} is missing {name!r}"
        raise PassOutputError(msg)
    value = item[name]
    if not isinstance(value, str) or not value.strip():
        msg = f"{where} field {name!r} must be a non-empty string"
        raise PassOutputError(msg)
    return value


def _require_list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        msg = f"reply field {name!r} must be a list"
        raise PassOutputError(msg)
    return value


def _require_object(value: object, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = f"{where} must be an object"
        raise PassOutputError(msg)
    return value


def _parse_terms(raw: object) -> tuple[TrackedTerm, ...]:
    terms = []
    for i, entry in enumerate(_require_list(raw, "terms")):
        where = f"term {i}"
        item = _require_object(entry, where)
        term = _require_str(item, "term", where)
        senses = item.get("senses")
        if (
            not isinstance(senses, list)
            or not senses
            or not all(isinstance(s, str) and s.strip() for s in senses)
        ):
            msg = f"{where} needs a non-empty list of non-empty string 'senses'"
            raise PassOutputError(msg)
        terms.append(TrackedTerm(term=term, senses=tuple(senses)))
    return tuple(terms)


def _contains_word(quote: str, term: str) -> bool:
    pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
    return re.search(pattern, quote, flags=re.IGNORECASE) is not None


def _normalise(sense: str) -> str:
    return " ".join(sense.split()).casefold()


def _parse_equivocations(raw: object, text: str) -> tuple[Equivocation, ...]:
    found = []
    for i, entry in enumerate(_require_list(raw, "equivocations")):
        where = f"equivocation {i}"
        item = _require_object(entry, where)
        fields = {name: _require_str(item, name, where) for name in _EQUIVOCATION_FIELDS}
        term = fields["term"]
        first_start, first_end = anchor_quote(text, fields["first_quote"])
        shifted_start, shifted_end = anchor_quote(text, fields["shifted_quote"])
        for name in ("first_quote", "shifted_quote"):
            if not _contains_word(fields[name], term):
                msg = f"{where}: {name} does not contain the term {term!r} as a whole word"
                raise PassOutputError(msg)
        if first_start < shifted_end and shifted_start < first_end:
            msg = f"{where}: the two quotes overlap, so they are not two separate uses"
            raise PassOutputError(msg)
        if _normalise(fields["first_sense"]) == _normalise(fields["shifted_sense"]):
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
        f"Equivocation on {eq.term!r}: first used to mean {eq.first_sense!r} "
        f"({eq.first_quote!r}), here used to mean {eq.shifted_sense!r}. {eq.explanation}"
    )
    return Annotation(
        kind="equivocation",
        quote=eq.shifted_quote,
        start=eq.shifted_start,
        end=eq.shifted_end,
        note=note,
        source=SOURCE,
    )
