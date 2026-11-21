"""Core data types and the score combination rule."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Annotation:
    """A margin note that points at a quoted span of the text."""

    kind: str
    quote: str
    note: str


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
