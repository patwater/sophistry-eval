"""Term tracking: follow each key term across the text and flag equivocation.

An equivocation is one term used in two different senses where an inference only goes through
if the senses are treated as one. See `Docs/rubrics.md` for how it differs from a part-whole
slide and from a rate-versus-total non-sequitur.

v0.1 can only report shifts where the same word appears at both uses. That is a limit on what
the pass detects, not part of the definition: a near-synonym conflation is also an equivocation.
"""

import re
from dataclasses import dataclass
from typing import Any

from sophistry_eval.client import ModelClient
from sophistry_eval.passes.common import PassOutputError, anchor_quote, parse_json_object
from sophistry_eval.types import Annotation

SOURCE = "term_tracking"
"""The `source` value on every annotation this pass makes."""

# The prompt must never mention fixture content (tests/test_term_tracking.py checks this), so
# the e2e test measures the pass, not a prompt tuned to one essay.
SYSTEM_PROMPT = """\
You audit the conceptual integrity of a piece of writing by tracking its key terms.

Task:
1. List the key terms the argument relies on. For each, give every sense in which the text \
uses it, as short plain-language glosses.
2. Report every equivocation the argument relies on.

Definition. An equivocation is one term used in two different senses, where an inference only \
goes through if the two senses are treated as one.

Do not report:
- Two senses or two quantities that the author distinguishes and then keeps apart \
throughout. Stating a definition or a distinction and then sliding across it is still an \
equivocation, and should be reported.
- Ordinary polysemy that carries no inference.
- Figures of speech the reader is meant to read as figures. They are a matter of persuasive \
force, not integrity. Report a figure only if the argument later relies on it read literally.
- A part-whole slide, which shifts the scope of a property from parts to a whole ("every \
brick is light, so the wall is light"). That is a different flaw, not an equivocation, unless \
the term's meaning also changes.

Quoting rules:
- Quotes must be copied verbatim from the text, character for character.
- Each quote must be long enough to occur exactly once in the text.
- Report an equivocation only when the term itself appears as a word in both quotes. The two \
quotes must not overlap.
- The equivocated term must also appear in your list of terms, with both of its senses.

Reply with one JSON object and nothing else, in this shape:
{"terms": [{"term": "...", "senses": ["...", "..."]}],
 "equivocations": [{"term": "...", "first_quote": "...", "first_sense": "...", \
"shifted_quote": "...", "shifted_sense": "...", "explanation": "..."}]}
Either list may be empty. The explanation says which inference depends on the shift.
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
    """A term that shifts sense between two uses, with code-point offsets for both uses."""

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
    """What the pass found. `annotations` holds one note per equivocation."""

    terms: tuple[TrackedTerm, ...]
    equivocations: tuple[Equivocation, ...]
    annotations: tuple[Annotation, ...]


def track_terms(
    text: str, *, client: ModelClient, system_prompt: str = SYSTEM_PROMPT
) -> TermReport:
    """Run the term-tracking pass on `text` with one model call.

    Raises `PassOutputError` if the reply is malformed or any item fails validation. Nothing is
    silently dropped, so a bad reply cannot quietly lower the equivocation count.
    """
    reply = client.complete(system_prompt, _prompt(text))
    data = parse_json_object(reply)
    terms = _parse_terms(data.get("terms"))
    raw_equivocations = data.get("equivocations")
    if not isinstance(raw_equivocations, list):
        msg = "reply must hold an 'equivocations' list"
        raise PassOutputError(msg)
    equivocations = tuple(_parse_equivocation(text, item, terms) for item in raw_equivocations)
    annotations = tuple(_annotate(eq) for eq in equivocations)
    return TermReport(terms=terms, equivocations=equivocations, annotations=annotations)


def _prompt(text: str) -> str:
    return f"Here is the text to audit, between the markers.\n\n<text>\n{text}\n</text>"


def _parse_terms(raw: object) -> tuple[TrackedTerm, ...]:
    if not isinstance(raw, list):
        msg = "reply must hold a 'terms' list"
        raise PassOutputError(msg)
    terms: list[TrackedTerm] = []
    for item in raw:
        if not isinstance(item, dict):
            msg = f"each entry in 'terms' must be an object, got {item!r}"
            raise PassOutputError(msg)
        term = item.get("term")
        senses = item.get("senses")
        if not isinstance(term, str) or not term:
            msg = f"each entry in 'terms' needs a non-empty 'term' string, got {term!r}"
            raise PassOutputError(msg)
        if (
            not isinstance(senses, list)
            or not senses
            or not all(isinstance(s, str) and s for s in senses)
        ):
            msg = f"term {term!r} needs a non-empty list of non-empty 'senses' strings"
            raise PassOutputError(msg)
        terms.append(TrackedTerm(term=term, senses=tuple(senses)))
    return tuple(terms)


def _parse_equivocation(text: str, item: object, terms: tuple[TrackedTerm, ...]) -> Equivocation:
    if not isinstance(item, dict):
        msg = f"each equivocation must be an object, got {item!r}"
        raise PassOutputError(msg)
    fields = _required_strings(item)
    term = fields["term"]

    first_start, first_end = anchor_quote(text, fields["first_quote"])
    shifted_start, shifted_end = anchor_quote(text, fields["shifted_quote"])

    for name in ("first_quote", "shifted_quote"):
        if not _contains_word(fields[name], term):
            msg = f"the term {term!r} does not appear as a whole word in {name}"
            raise PassOutputError(msg)
    if first_start < shifted_end and shifted_start < first_end:
        msg = f"the two quotes for {term!r} overlap, so they are one use, not two"
        raise PassOutputError(msg)
    if _normalise(fields["first_sense"]) == _normalise(fields["shifted_sense"]):
        msg = f"the two senses given for {term!r} are the same"
        raise PassOutputError(msg)

    listed = [t for t in terms if t.term.casefold() == term.casefold()]
    if not listed:
        msg = f"the equivocated term {term!r} is not listed in 'terms'"
        raise PassOutputError(msg)
    sense_count = len({_normalise(s) for t in listed for s in t.senses})
    if sense_count < 2:
        msg = (
            f"the equivocated term {term!r} is listed in 'terms' with only one distinct sense, "
            "but an equivocation needs at least two senses"
        )
        raise PassOutputError(msg)

    return Equivocation(
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


def _required_strings(item: dict[str, Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in _EQUIVOCATION_FIELDS:
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            msg = f"equivocation field {key!r} must be a non-empty string, got {value!r}"
            raise PassOutputError(msg)
        fields[key] = value
    return fields


def _contains_word(quote: str, term: str) -> bool:
    """True if `term` occurs in `quote` as a whole word, ignoring case, matched literally."""
    pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
    return re.search(pattern, quote, re.IGNORECASE) is not None


def _normalise(sense: str) -> str:
    return " ".join(sense.split()).casefold()


def _annotate(eq: Equivocation) -> Annotation:
    note = (
        f"Equivocation on {eq.term!r}: elsewhere used to mean {eq.first_sense!r} "
        f'("{eq.first_quote}"), here used to mean {eq.shifted_sense!r}. {eq.explanation}'
    )
    return Annotation(
        kind="equivocation",
        quote=eq.shifted_quote,
        start=eq.shifted_start,
        end=eq.shifted_end,
        note=note,
        source=SOURCE,
    )
