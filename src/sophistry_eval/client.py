"""The model client layer: one thin interface, so tests can replay recorded responses and cost
can be counted.

- `ModelClient` is the interface every pass uses.
- `ClaudeClient` calls the Claude API.
- `RecordingClient` wraps a live client and writes each reply to a JSON file.
- `RecordedClient` replays such a file offline and never goes live.

Recordings store only hashes of the prompts, never the prompt text, because prompts carry
essay text that may be copyrighted. See `Docs/testing-strategy.md` for where recordings live.
"""

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import anthropic
from anthropic.types import Message, MessageParam, TextBlock

PRIMARY_MODEL = "claude-sonnet-5-5"
"""The main scoring model (open question 4 in Specs/initial-build.md)."""

COMPARISON_MODEL = "claude-haiku-5-5"
"""The cheaper model used for stability comparisons (open question 4)."""

DEFAULT_MAX_TOKENS = 4096
API_KEY_VARIABLE = "ANTHROPIC_API_KEY"
RECORDING_FORMAT = 1

type Settings = dict[str, int | float | str | None]
"""Call settings that change a model's reply. Today only max_tokens."""


class ModelClient(Protocol):
    """Anything that can complete a prompt."""

    def complete(self, system: str, prompt: str) -> str:
        """Return the model's text reply for the given system and user prompts."""
        ...


class RecordableClient(ModelClient, Protocol):
    """A client whose replies can be recorded: it names its model and call settings."""

    @property
    def model(self) -> str: ...

    @property
    def settings(self) -> Settings: ...


@dataclass(frozen=True)
class UsageTotals:
    """Tokens spent so far. Converting these to dollars is left to the ledger."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> "UsageTotals":
        return UsageTotals(
            calls=self.calls + 1,
            input_tokens=self.input_tokens + input_tokens,
            output_tokens=self.output_tokens + output_tokens,
        )


@runtime_checkable
class Metered(Protocol):
    """A client that counts what it has spent."""

    @property
    def usage(self) -> UsageTotals | None: ...


class MissingCredentialError(RuntimeError):
    """The API key is not set. The message names the variable and never a value."""


class UnusableReplyError(RuntimeError):
    """The reply cannot be used as a pass's answer (refused, empty, or otherwise incomplete).

    Raising here keeps such replies out of recordings, where they would be replayed as valid.
    """


class TruncatedReplyError(UnusableReplyError):
    """The reply stopped at max_tokens, so it is incomplete and must not be parsed."""


class RecordingMissingError(LookupError):
    """Replay was asked for a reply that was never recorded."""


class MessagesAPI(Protocol):
    """The part of `anthropic.Anthropic().messages` that ClaudeClient uses."""

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: Iterable[MessageParam],
    ) -> Message: ...


class _SDKMessages:
    """Adapts the SDK's overloaded `messages.create` to the narrow MessagesAPI protocol."""

    def __init__(self, sdk: anthropic.Anthropic) -> None:
        self._sdk = sdk

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: Iterable[MessageParam],
    ) -> Message:
        return self._sdk.messages.create(
            model=model, max_tokens=max_tokens, system=system, messages=messages
        )


_COMPLETE_STOP_REASONS = frozenset({"end_turn", "stop_sequence"})
"""Stop reasons after which a text reply is whole. Anything else (refusal, pause, tool use,
context window exceeded) raises UnusableReplyError."""


class ClaudeClient:
    """A ModelClient backed by the Claude API.

    The SDK retries transient errors itself, so this class does not. There is no temperature
    setting: the installed SDK's `messages.create` has no temperature parameter. There is no
    sampling control, and replies vary from run to run at the API's default.
    """

    def __init__(
        self,
        model: str = PRIMARY_MODEL,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        messages_api: MessagesAPI | None = None,
    ) -> None:
        if messages_api is None:
            if not os.environ.get(API_KEY_VARIABLE):
                msg = f"{API_KEY_VARIABLE} is not set, so the Claude API cannot be called."
                raise MissingCredentialError(msg)
            messages_api = _SDKMessages(anthropic.Anthropic())
        self._api: MessagesAPI = messages_api
        self._model = model
        self._max_tokens = max_tokens
        self._usage = UsageTotals()

    @property
    def model(self) -> str:
        return self._model

    @property
    def settings(self) -> Settings:
        return {"max_tokens": self._max_tokens}

    @property
    def usage(self) -> UsageTotals:
        return self._usage

    def complete(self, system: str, prompt: str) -> str:
        messages: list[MessageParam] = [{"role": "user", "content": prompt}]
        reply = self._api.create(
            model=self._model, max_tokens=self._max_tokens, system=system, messages=messages
        )
        self._usage = self._usage.add(reply.usage.input_tokens, reply.usage.output_tokens)
        if reply.stop_reason == "max_tokens":
            msg = f"reply stopped at max_tokens={self._max_tokens} and is incomplete"
            raise TruncatedReplyError(msg)
        if reply.stop_reason not in _COMPLETE_STOP_REASONS:
            msg = f"reply stopped with stop_reason={reply.stop_reason!r} and cannot be used"
            raise UnusableReplyError(msg)
        text = "".join(block.text for block in reply.content if isinstance(block, TextBlock))
        if not text.strip():
            msg = "reply contained no text"
            raise UnusableReplyError(msg)
        return text


def prompt_key(system: str, prompt: str) -> str:
    """A stable hash of a system prompt and a user prompt.

    Each part is length-prefixed, so ("ab", "c") and ("a", "bc") differ. The future input-hash
    cache must build its key from this helper (plus model and settings) so the two schemes
    cannot drift apart.
    """
    digest = hashlib.sha256()
    for part in (system, prompt):
        data = part.encode("utf-8")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


@dataclass(frozen=True)
class _Recording:
    model: str
    settings: Settings
    replies: dict[str, list[str]]


def _load(path: Path) -> _Recording:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("format") != RECORDING_FORMAT:
        found = data.get("format") if isinstance(data, dict) else None
        msg = f"{path}: unsupported recording format {found!r}, expected {RECORDING_FORMAT}"
        raise ValueError(msg)
    model, settings, replies = data.get("model"), data.get("settings"), data.get("replies")
    if not (
        isinstance(model, str)
        and isinstance(settings, dict)
        and all(isinstance(k, str) for k in settings)
        and all(v is None or isinstance(v, int | float | str) for v in settings.values())
        and isinstance(replies, dict)
        and all(
            isinstance(key, str)
            and isinstance(texts, list)
            and all(isinstance(t, str) for t in texts)
            for key, texts in replies.items()
        )
    ):
        msg = f"{path}: malformed recording (needs a str model, a settings object, replies lists)"
        raise ValueError(msg)
    return _Recording(model=model, settings=settings, replies=replies)


def _save(path: Path, recording: _Recording) -> None:
    """Write atomically, so a crash mid-write never leaves a half-written file."""
    payload = {
        "format": RECORDING_FORMAT,
        "model": recording.model,
        "settings": recording.settings,
        "replies": recording.replies,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class RecordingClient:
    """Wraps a live client and appends each reply to a recording file.

    The file is re-read before every write, so two recorders on one path in the same process
    do not overwrite each other. The file pins one model and one set of call settings, and a
    mismatch is refused both at construction and at every write.
    """

    def __init__(self, inner: RecordableClient, path: Path) -> None:
        self._inner = inner
        self._path = path
        self._check_header()

    @property
    def usage(self) -> UsageTotals | None:
        """The inner client's usage, or None when the inner client does not count it."""
        if isinstance(self._inner, Metered):
            usage = self._inner.usage
            if isinstance(usage, UsageTotals):
                return usage
        return None

    def _check_header(self) -> _Recording | None:
        if not self._path.exists():
            return None
        recording = _load(self._path)
        if recording.model != self._inner.model:
            msg = (
                f"{self._path} was recorded with model {recording.model!r}, "
                f"not {self._inner.model!r}"
            )
            raise ValueError(msg)
        if recording.settings != self._inner.settings:
            msg = (
                f"{self._path} was recorded with settings {recording.settings!r}, "
                f"not {self._inner.settings!r}"
            )
            raise ValueError(msg)
        return recording

    def complete(self, system: str, prompt: str) -> str:
        self._check_header()  # before the paid call, so a doomed reply is never bought
        reply = self._inner.complete(system, prompt)
        recording = self._check_header() or _Recording(
            model=self._inner.model, settings=self._inner.settings, replies={}
        )
        recording.replies.setdefault(prompt_key(system, prompt), []).append(reply)
        _save(self._path, recording)
        return reply


class RecordedClient:
    """Replays a recording offline. Never calls a live model.

    The nth call with a given prompt returns the nth reply recorded for it, so the spread of
    repeated runs survives replay. An unknown prompt, or more calls than were recorded, raises
    RecordingMissingError.
    """

    def __init__(self, path: Path) -> None:
        recording = _load(path)
        self._path = path
        self.model = recording.model
        self.settings = recording.settings
        self._replies = recording.replies
        self._served: dict[str, int] = {}

    def complete(self, system: str, prompt: str) -> str:
        key = prompt_key(system, prompt)
        replies = self._replies.get(key)
        if replies is None:
            msg = f"{self._path}: no recording for this prompt (key {key[:12]})"
            raise RecordingMissingError(msg)
        served = self._served.get(key, 0)
        if served >= len(replies):
            msg = (
                f"{self._path}: only {len(replies)} recorded replies for key {key[:12]}, "
                f"asked for reply {served + 1}"
            )
            raise RecordingMissingError(msg)
        self._served[key] = served + 1
        return replies[served]
