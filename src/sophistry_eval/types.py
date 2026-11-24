"""Core data types, the annotation format, and the score combination rule."""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

ANNOTATION_FORMAT = 1
"""Version of the serialized annotation format. Any new or changed field bumps it."""

_ANNOTATION_FIELDS: dict[str, type] = {
    "kind": str,
    "quote": str,
    "start": int,
    "end": int,
    "note": str,
    "source": str,
}


@dataclass(frozen=True)
class Annotation:
    """A margin note that points at a quoted span of the text.

    `start` and `end` are Unicode code-point indices (Python string indices) into the exact
    string the pass received, with no normalisation, so `text[start:end] == quote`. A consumer
    that counts UTF-16 units or bytes must convert. `source` names the pass that made the note.
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
            msg = f"annotation end ({self.end}) must not precede start ({self.start})"
            raise ValueError(msg)
        if self.end - self.start != len(self.quote):
            msg = (
                f"annotation quote has {len(self.quote)} characters but the offsets "
                f"span {self.end - self.start}"
            )
            raise ValueError(msg)


def annotations_to_json(annotations: Iterable[Annotation]) -> str:
    """Serialize annotations as `{"format": 1, "annotations": [...]}` with fixed key names."""
    items = [
        {
            "kind": a.kind,
            "quote": a.quote,
            "start": a.start,
            "end": a.end,
            "note": a.note,
            "source": a.source,
        }
        for a in annotations
    ]
    return json.dumps({"format": ANNOTATION_FORMAT, "annotations": items}, ensure_ascii=False)


def annotations_from_json(raw: str) -> tuple[Annotation, ...]:
    """Read annotations written by `annotations_to_json`.

    Strict: another format, a missing or unknown key, or a wrongly typed value raises
    `ValueError`. A reader never silently drops a field it does not understand.
    """
    data: Any = json.loads(raw)
    if not isinstance(data, dict):
        msg = "annotation JSON must be an object"
        raise ValueError(msg)
    unknown = set(data) - {"format", "annotations"}
    if unknown:
        msg = f"unknown top-level keys in annotation JSON: {sorted(unknown)}"
        raise ValueError(msg)
    version = data.get("format")
    # Exact type check: in Python, 1.0 == 1 and True == 1.
    if type(version) is not int or version != ANNOTATION_FORMAT:
        msg = f"unsupported annotation format {version!r}, expected {ANNOTATION_FORMAT}"
        raise ValueError(msg)
    items = data.get("annotations")
    if not isinstance(items, list):
        msg = "annotation JSON must hold an 'annotations' list"
        raise ValueError(msg)
    return tuple(_annotation_from_dict(item) for item in items)


def _annotation_from_dict(item: object) -> Annotation:
    if not isinstance(item, dict):
        msg = "each annotation must be an object"
        raise ValueError(msg)
    unknown = set(item) - set(_ANNOTATION_FIELDS)
    if unknown:
        msg = f"unknown annotation keys: {sorted(unknown)}"
        raise ValueError(msg)
    for key, expected in _ANNOTATION_FIELDS.items():
        if key not in item:
            msg = f"annotation is missing the key {key!r}"
            raise ValueError(msg)
        value = item[key]
        # bool is a subclass of int, so check the exact type.
        if type(value) is not expected:
            msg = f"annotation key {key!r} must be {expected.__name__}, got {value!r}"
            raise ValueError(msg)
    return Annotation(
        kind=item["kind"],
        quote=item["quote"],
        start=item["start"],
        end=item["end"],
        note=item["note"],
        source=item["source"],
    )


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
