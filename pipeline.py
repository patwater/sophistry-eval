"""The scoring pipeline. Not implemented yet: the first night shift builds it from the spec."""

from sophistry_eval.client import ModelClient
from sophistry_eval.types import Evaluation


def score_text(text: str, *, client: ModelClient | None = None) -> Evaluation:
    """Score a piece of writing on force, integrity and difficulty, with margin annotations."""
    del text, client
    msg = "The pipeline is not built yet. See Specs/draft-initial-build.md."
    raise NotImplementedError(msg)
