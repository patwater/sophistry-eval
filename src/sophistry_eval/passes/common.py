"""Helpers shared by every pass: parsing a model's JSON reply, anchoring quotes, and matching
a term as a whole word."""

import json
import re
from typing import Any

_FENCE = re.compile(r"```[A-Za-z0-9_-]*[ \t]*\n(.*?)\n?```", re.DOTALL)


class PassOutputError(ValueError):
    """A model reply cannot be used as a pass's answer. Raised, never silently skipped."""


def parse_json_object(reply: str) -> dict[str, Any]:
    """Parse a reply that is bare JSON or holds exactly one fenced code block.

    The top level must be an object.
    """
    stripped = reply.strip()
    if stripped.startswith("{"):
        body = stripped
    else:
        blocks = _FENCE.findall(reply)
        if len(blocks) != 1:
            msg = f"expected bare JSON or exactly one fenced block, found {len(blocks)} blocks"
            raise PassOutputError(msg)
        body = blocks[0]
    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        msg = f"reply is not valid JSON: {error}"
        raise PassOutputError(msg) from error
    if not isinstance(data, dict):
        msg = f"reply must be a JSON object, got {type(data).__name__}"
        raise PassOutputError(msg)
    return data


def anchor_quote(text: str, quote: str) -> tuple[int, int]:
    """Return the `(start, end)` code-point offsets of the one place `quote` occurs in `text`.

    Raises if the quote is empty, missing, or occurs more than once (overlaps count). An
    ambiguous quote is rejected rather than guessed.
    """
    if not quote:
        msg = "quote is empty"
        raise PassOutputError(msg)
    start = text.find(quote)
    if start < 0:
        msg = f"quote not found in the text: {quote!r}"
        raise PassOutputError(msg)
    if text.find(quote, start + 1) >= 0:
        msg = f"quote occurs more than once in the text: {quote!r}"
        raise PassOutputError(msg)
    return start, start + len(quote)


def contains_whole_word(text: str, word: str) -> bool:
    """True when `word` occurs in `text` as a whole word, ignoring case.

    A whole word is not preceded or followed by a word character, so "efficiency" is found in
    "the efficiency." but not in "inefficiency". The term-tracking pass and the end-to-end gate
    both use this, so the two cannot disagree about what counts as the term.
    """
    pattern = rf"(?<!\w){re.escape(word)}(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None
