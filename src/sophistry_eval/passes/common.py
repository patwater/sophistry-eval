"""Helpers shared by every pass: strict reply parsing and quote anchoring."""

import json
import re
from typing import Any

_FENCE = re.compile(r"```[A-Za-z0-9_-]*[ \t]*\n(.*?)\n?```", re.DOTALL)


class PassOutputError(ValueError):
    """A model reply cannot be used as the pass's answer. Raised, never silently skipped."""


def parse_json_object(reply: str) -> dict[str, Any]:
    """Parse a reply that is bare JSON or holds exactly one fenced code block.

    The top level must be a JSON object.
    """
    blocks = _FENCE.findall(reply)
    if len(blocks) > 1:
        msg = f"reply holds {len(blocks)} fenced blocks, expected at most one"
        raise PassOutputError(msg)
    body = blocks[0] if blocks else reply
    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        msg = f"reply is not valid JSON: {error}"
        raise PassOutputError(msg) from error
    if not isinstance(data, dict):
        msg = f"reply's top level is {type(data).__name__}, expected an object"
        raise PassOutputError(msg)
    return data


def anchor_quote(text: str, quote: str) -> tuple[int, int]:
    """Return `(start, end)` of the one place `quote` occurs in `text`, in code points.

    An empty, missing or repeated quote raises, since guessing which occurrence was meant
    could put a note in the wrong place. Overlapping occurrences count as repeats.
    """
    if not quote:
        msg = "quote is empty"
        raise PassOutputError(msg)
    start = text.find(quote)
    if start < 0:
        msg = f"quote not found in the text: {quote!r}"
        raise PassOutputError(msg)
    if text.find(quote, start + 1) >= 0:
        msg = f"quote occurs more than once in the text, so it cannot be anchored: {quote!r}"
        raise PassOutputError(msg)
    return start, start + len(quote)
