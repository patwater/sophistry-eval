"""Helpers shared by every pass: reading a model's JSON reply and anchoring quotes."""

import json
import re
from typing import Any

_FENCE = re.compile(r"```[A-Za-z0-9_-]*[ \t]*\n(.*?)\n?```", re.DOTALL)


class PassOutputError(ValueError):
    """A model reply was received but cannot be used by the pass.

    Distinct from the client's `UnusableReplyError`, which covers transport-level failures such
    as truncation or refusal.
    """


def parse_json_object(reply: str) -> dict[str, Any]:
    """Parse a reply that is either bare JSON or contains exactly one fenced code block.

    The top level must be a JSON object.
    """
    stripped = reply.strip()
    try:
        data: Any = json.loads(stripped)
    except json.JSONDecodeError:
        blocks = _FENCE.findall(reply)
        if len(blocks) != 1:
            msg = f"reply is not bare JSON and has {len(blocks)} fenced blocks, expected exactly 1"
            raise PassOutputError(msg) from None
        try:
            data = json.loads(blocks[0])
        except json.JSONDecodeError as err:
            msg = f"fenced block is not valid JSON: {err}"
            raise PassOutputError(msg) from None
    if not isinstance(data, dict):
        msg = f"reply must be a JSON object, got {type(data).__name__}"
        raise PassOutputError(msg)
    return data


def anchor_quote(text: str, quote: str) -> tuple[int, int]:
    """Return `(start, end)` code-point offsets of the one place `quote` occurs in `text`.

    Matching is exact, with no whitespace or quote-mark normalisation. An empty, missing or
    ambiguous quote (one that occurs more than once, overlapping occurrences included) raises
    `PassOutputError` rather than being guessed.
    """
    if not quote:
        msg = "quote is empty"
        raise PassOutputError(msg)
    start = text.find(quote)
    if start == -1:
        msg = f"quote not found in the text: {quote!r}"
        raise PassOutputError(msg)
    if text.find(quote, start + 1) != -1:
        msg = f"quote occurs more than once in the text: {quote!r}"
        raise PassOutputError(msg)
    return start, start + len(quote)
