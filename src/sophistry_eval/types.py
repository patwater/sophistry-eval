"""Core data types, the score combination rule, and the annotation format."""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass

ANNOTATION_FORMAT = 1
"""Version of the serialized annotation format. Any change to its keys means a new version.

Offsets count Unicode code points (Python `str` indexing, as in W3C TextPositionSelector), not
UTF-16 units. They index the exact text the pass was given, which uses `\\n` newlines only.
See the Output section of Docs/overview.md.
"""

_ANNOTATION_KEYS = ("kind", "quote", "start", "end", "note", "source")


@dataclass(frozen=True)
class Annotation:
    """A margin note anchored to `text[start:end] == quote` in the text that was scored.

    `source` names the pass that produced the note, so notes from several passes can share
    one list and the same `kind` from two passes can be told apart.
    """

    kind: str
    quote: str
    start: int
    end: int
    note: str
    source: str

    def __post_init__(self) -> None:
        if self.start < 0:
            msg = f"start must be non-negative, got {self.start}"
            raise ValueError(msg)
        if self.end < self.start:
            msg = f"end ({self.end}) must not be before start ({self.start})"
            raise ValueError(msg)
        if self.end - self.start != len(self.quote):
            msg = f"span length {self.end - self.start} differs from quote length {len(self.quote)}"
            raise ValueError(msg)
        if not self.source:
            msg = "source must name the pass that produced the annotation"
            raise ValueError(msg)


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


def text_sha256(text: str) -> str:
    """The SHA-256 hex digest of the text's UTF-8 bytes, which ties annotations to their text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check_anchor(annotation: Annotation, text: str) -> None:
    span = text[annotation.start : annotation.end]
    if span != annotation.quote:
        msg = (
            f"quote {annotation.quote!r} does not match the text at "
            f"[{annotation.start}:{annotation.end}], which is {span!r}"
        )
        raise ValueError(msg)


def annotations_to_json(annotations: Iterable[Annotation], *, text: str) -> str:
    """Serialize annotations for `text` in format 1. Refuses notes that miss their span."""
    items = list(annotations)
    for annotation in items:
        _check_anchor(annotation, text)
    payload = {
        "format": ANNOTATION_FORMAT,
        "text_sha256": text_sha256(text),
        "annotations": [asdict(a) for a in items],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _annotation_from_item(item: object, index: int) -> Annotation:
    if not isinstance(item, dict):
        msg = f"annotation {index} is not an object"
        raise ValueError(msg)
    keys = set(item)
    missing = [k for k in _ANNOTATION_KEYS if k not in keys]
    if missing:
        msg = f"annotation {index} is missing {', '.join(missing)}"
        raise ValueError(msg)
    unknown = sorted(keys - set(_ANNOTATION_KEYS))
    if unknown:
        msg = f"annotation {index} has unknown keys {', '.join(unknown)} (format 1 is closed)"
        raise ValueError(msg)
    for key in ("start", "end"):
        value = item[key]
        if not isinstance(value, int) or isinstance(value, bool):
            msg = f"annotation {index}: {key} must be an integer"
            raise ValueError(msg)
    for key in ("kind", "quote", "note", "source"):
        if not isinstance(item[key], str):
            msg = f"annotation {index}: {key} must be a string"
            raise ValueError(msg)
    return Annotation(
        kind=item["kind"],
        quote=item["quote"],
        start=item["start"],
        end=item["end"],
        note=item["note"],
        source=item["source"],
    )


def annotations_from_json(encoded: str, *, text: str) -> tuple[Annotation, ...]:
    """Read format-1 annotations and check that they belong to `text` and anchor in it."""
    data = json.loads(encoded)
    found = data.get("format") if isinstance(data, dict) else None
    if type(found) is not int or found != ANNOTATION_FORMAT:  # refuses True and 1.0
        msg = f"unsupported annotation format {found!r}, expected {ANNOTATION_FORMAT}"
        raise ValueError(msg)
    if data.get("text_sha256") != text_sha256(text):
        msg = "text_sha256 does not match the given text, so the offsets would be wrong"
        raise ValueError(msg)
    items = data.get("annotations")
    if not isinstance(items, list):
        msg = "annotations must be a list"
        raise ValueError(msg)
    result = tuple(_annotation_from_item(item, i) for i, item in enumerate(items))
    for annotation in result:
        _check_anchor(annotation, text)
    return result
