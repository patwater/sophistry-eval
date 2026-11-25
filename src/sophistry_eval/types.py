"""Core data types, the score combination rule, and the annotation format."""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass

ANNOTATION_FORMAT = 1
"""Version of the serialized annotation format. See `Docs/overview.md`, Output."""

_ANNOTATION_STR_FIELDS = ("kind", "quote", "note", "source")
_ANNOTATION_INT_FIELDS = ("start", "end")


@dataclass(frozen=True)
class Annotation:
    """A margin note that points at a quoted span of the text.

    `start` and `end` count Unicode code points (Python `str` indices) into the exact string
    the pass was given, with no normalisation, so `text[start:end] == quote`. `source` names
    the pass that made the note.
    """

    kind: str
    quote: str
    start: int
    end: int
    note: str
    source: str

    def __post_init__(self) -> None:
        if not self.kind:
            msg = "annotation kind must not be empty"
            raise ValueError(msg)
        if not self.source:
            msg = "annotation source must not be empty"
            raise ValueError(msg)
        if self.start < 0:
            msg = f"annotation start must not be negative, got {self.start}"
            raise ValueError(msg)
        if self.end < self.start:
            msg = f"annotation end {self.end} is before start {self.start}"
            raise ValueError(msg)
        if self.end - self.start != len(self.quote):
            msg = (
                f"annotation span {self.start}:{self.end} has length {self.end - self.start}, "
                f"but the quote has length {len(self.quote)}"
            )
            raise ValueError(msg)


def text_sha256(text: str) -> str:
    """The SHA-256 of the UTF-8 encoding of a text, as hex."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def annotations_to_json(annotations: Iterable[Annotation], *, text: str) -> str:
    """Serialize annotations with the format version and the hash of the text they index."""
    payload = {
        "format": ANNOTATION_FORMAT,
        "text_sha256": text_sha256(text),
        "annotations": [
            {
                "kind": a.kind,
                "quote": a.quote,
                "start": a.start,
                "end": a.end,
                "note": a.note,
                "source": a.source,
            }
            for a in annotations
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _annotation_from_dict(item: object, index: int) -> Annotation:
    if not isinstance(item, dict):
        msg = f"annotation {index} is not an object"
        raise ValueError(msg)
    for name in _ANNOTATION_STR_FIELDS + _ANNOTATION_INT_FIELDS:
        if name not in item:
            msg = f"annotation {index} is missing {name!r}"
            raise ValueError(msg)
    for name in _ANNOTATION_STR_FIELDS:
        if not isinstance(item[name], str):
            msg = f"annotation {index} field {name!r} must be a string"
            raise ValueError(msg)
    for name in _ANNOTATION_INT_FIELDS:
        value = item[name]
        if isinstance(value, bool) or not isinstance(value, int):
            msg = f"annotation {index} field {name!r} must be an integer"
            raise ValueError(msg)
    return Annotation(
        kind=item["kind"],
        quote=item["quote"],
        start=item["start"],
        end=item["end"],
        note=item["note"],
        source=item["source"],
    )


def annotations_from_json(data: str, *, text: str | None = None) -> tuple[Annotation, ...]:
    """Read annotations written by `annotations_to_json`.

    When `text` is given, the stored hash must match it, so offsets never land in the wrong text.
    """
    payload = json.loads(data)
    if not isinstance(payload, dict) or payload.get("format") != ANNOTATION_FORMAT:
        found = payload.get("format") if isinstance(payload, dict) else None
        msg = f"unsupported annotation format {found!r}, expected {ANNOTATION_FORMAT}"
        raise ValueError(msg)
    stored_hash = payload.get("text_sha256")
    if not isinstance(stored_hash, str):
        msg = "annotation file is missing a string 'text_sha256'"
        raise ValueError(msg)
    if text is not None and stored_hash != text_sha256(text):
        msg = "annotation file's text_sha256 does not match the given text"
        raise ValueError(msg)
    items = payload.get("annotations")
    if not isinstance(items, list):
        msg = "annotation file's 'annotations' must be a list"
        raise ValueError(msg)
    return tuple(_annotation_from_dict(item, i) for i, item in enumerate(items))


@dataclass(frozen=True)
class Scores:
    """The three axes, each from 0 to 1, and their combination."""

    force: float
    integrity: float
    difficulty: float

    @property
    def sophistry(self) -> float:
        return combine(self.force, self.integrity, self.difficulty)


@dataclass(frozen=True)
class Evaluation:
    """The result of scoring one piece of writing."""

    scores: Scores
    annotations: tuple[Annotation, ...]


def combine(force: float, integrity: float, difficulty: float) -> float:
    """Sophistry strength is force x integrity x difficulty (see Docs/rubrics.md).

    Each input must be between 0 and 1. Difficulty acts as a multiplier that rewards holding
    a hard case. Whether to use a minimum instead is an open question in the draft spec.
    """
    for name, value in (("force", force), ("integrity", integrity), ("difficulty", difficulty)):
        if not 0.0 <= value <= 1.0:
            msg = f"{name} must be between 0 and 1, got {value}"
            raise ValueError(msg)
    return force * integrity * difficulty
