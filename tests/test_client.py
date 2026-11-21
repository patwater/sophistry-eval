"""Tests for the model client layer: the Claude client, recording and replay.

None of these call a live model. The Claude client is exercised against a fake `messages` API
that returns real SDK `Message` objects, so the parsing and usage accounting are tested against
the SDK's own types.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from anthropic.types import Message, TextBlock, Usage

from sophistry_eval.client import (
    COMPARISON_MODEL,
    PRIMARY_MODEL,
    ClaudeClient,
    MissingCredentialError,
    ModelClient,
    RecordedClient,
    RecordingClient,
    RecordingMissingError,
    Settings,
    TruncatedReplyError,
    UnusableReplyError,
    UsageTotals,
    prompt_key,
)

# --- helpers -----------------------------------------------------------------


def _message(*texts: str, stop_reason: str = "end_turn", inp: int = 10, out: int = 5) -> Message:
    return Message(
        id="msg_test",
        type="message",
        role="assistant",
        model=PRIMARY_MODEL,
        content=[TextBlock(type="text", text=t) for t in texts],
        stop_reason=stop_reason,  # type: ignore[arg-type]
        stop_sequence=None,
        usage=Usage(input_tokens=inp, output_tokens=out),
    )


class FakeMessages:
    """Stands in for `anthropic.Anthropic().messages`. Records every call's keyword arguments."""

    def __init__(self, *replies: Message) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Message:
        self.calls.append(kwargs)
        return self.replies.pop(0)


class ScriptedClient:
    """A ModelClient that returns scripted replies in order, for recording tests."""

    def __init__(self, *replies: str, model: str = "scripted-model", max_tokens: int = 100) -> None:
        self.model = model
        self.settings: Settings = {"max_tokens": max_tokens}
        self.replies = list(replies)
        self.calls = 0

    def complete(self, system: str, prompt: str) -> str:
        del system, prompt
        self.calls += 1
        return self.replies.pop(0)


# --- models --------------------------------------------------------------------


def test_default_models_follow_the_spec() -> None:
    """Open question 4 in Specs/initial-build.md: Sonnet primary, Haiku comparison."""
    assert PRIMARY_MODEL == "claude-sonnet-5-5"
    assert COMPARISON_MODEL == "claude-haiku-5-5"


# --- ClaudeClient ----------------------------------------------------------------


def test_claude_client_sends_system_and_prompt_and_returns_text() -> None:
    fake = FakeMessages(_message("hello"))
    client = ClaudeClient(messages_api=fake)

    assert client.complete("be terse", "say hello") == "hello"

    (call,) = fake.calls
    assert call["model"] == PRIMARY_MODEL
    assert call["system"] == "be terse"
    assert call["messages"] == [{"role": "user", "content": "say hello"}]
    assert call["max_tokens"] > 0


def test_claude_client_uses_the_model_it_was_given() -> None:
    fake = FakeMessages(_message("ok"))
    ClaudeClient(model=COMPARISON_MODEL, messages_api=fake).complete("s", "p")
    assert fake.calls[0]["model"] == COMPARISON_MODEL


def test_claude_client_joins_multiple_text_blocks() -> None:
    fake = FakeMessages(_message("one ", "two"))
    assert ClaudeClient(messages_api=fake).complete("s", "p") == "one two"


def test_claude_client_counts_calls_and_tokens() -> None:
    fake = FakeMessages(_message("a", inp=100, out=7), _message("b", inp=50, out=3))
    client = ClaudeClient(messages_api=fake)
    client.complete("s", "p")
    client.complete("s", "p")
    assert client.usage == UsageTotals(calls=2, input_tokens=150, output_tokens=10)


def test_claude_client_refuses_a_truncated_reply() -> None:
    """A reply cut off at max_tokens is silently wrong (half a JSON object), so it is an error."""
    fake = FakeMessages(_message('{"half":', stop_reason="max_tokens"))
    with pytest.raises(TruncatedReplyError, match="max_tokens"):
        ClaudeClient(messages_api=fake).complete("s", "p")


def test_claude_client_counts_usage_even_when_the_reply_is_truncated() -> None:
    """Tokens were spent, so the cost count must include them."""
    fake = FakeMessages(_message("x", stop_reason="max_tokens", inp=9, out=4))
    client = ClaudeClient(messages_api=fake)
    with pytest.raises(TruncatedReplyError):
        client.complete("s", "p")
    assert client.usage == UsageTotals(calls=1, input_tokens=9, output_tokens=4)


def test_claude_client_without_a_key_names_the_missing_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingCredentialError, match="ANTHROPIC_API_KEY"):
        ClaudeClient()


def test_claude_client_settings_match_what_it_sends() -> None:
    """Recordings pin `settings`, so they must equal what actually reaches the API."""
    fake = FakeMessages(_message("x"))
    client = ClaudeClient(max_tokens=1234, messages_api=fake)
    client.complete("s", "p")
    assert client.settings == {"max_tokens": 1234}
    assert fake.calls[0]["max_tokens"] == client.settings["max_tokens"]


def test_claude_client_is_a_model_client() -> None:
    """Checked statically by mypy --strict through the annotated assignment. The runtime
    assertion is incidental."""
    client: ModelClient = ClaudeClient(messages_api=FakeMessages())
    assert client is not None


# --- RecordingClient and RecordedClient ------------------------------------------


def test_record_then_replay_returns_the_same_replies_offline(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    live = ScriptedClient("first", "second")
    recorder = RecordingClient(live, path)
    assert recorder.complete("sys", "a") == "first"
    assert recorder.complete("sys", "b") == "second"

    replay = RecordedClient(path)
    assert replay.complete("sys", "b") == "second"
    assert replay.complete("sys", "a") == "first"


def test_repeated_calls_replay_in_recorded_order_so_variance_is_preserved(
    tmp_path: Path,
) -> None:
    """The same prompt asked three times gave three replies. Replay must not collapse them,
    or a stability test run offline would report zero variance."""
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("0.6", "0.7", "0.8"), path)
    for _ in range(3):
        recorder.complete("sys", "same")

    replay = RecordedClient(path)
    assert [replay.complete("sys", "same") for _ in range(3)] == ["0.6", "0.7", "0.8"]


def test_replay_fails_when_more_calls_are_made_than_were_recorded(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("only"), path)
    recorder.complete("sys", "p")

    replay = RecordedClient(path)
    replay.complete("sys", "p")
    with pytest.raises(RecordingMissingError, match="1 recorded"):
        replay.complete("sys", "p")


def test_replay_fails_on_an_unrecorded_prompt_and_never_goes_live(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("x"), path)
    recorder.complete("sys", "known")

    with pytest.raises(RecordingMissingError, match="no recording"):
        RecordedClient(path).complete("sys", "unknown")


def test_the_system_prompt_is_part_of_the_key(tmp_path: Path) -> None:
    """Changing a pass's instructions must invalidate its recordings."""
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("x"), path)
    recorder.complete("old instructions", "p")

    with pytest.raises(RecordingMissingError):
        RecordedClient(path).complete("new instructions", "p")


def test_recordings_store_hashes_not_prompt_text(tmp_path: Path) -> None:
    """Prompts carry essay text, which may be copyrighted. Recordings must not contain it."""
    path = tmp_path / "rec.json"
    essay_text = "A copyrighted paragraph that must never be written to a recording."
    recorder = RecordingClient(ScriptedClient("reply"), path)
    recorder.complete("sys prompt text", essay_text)

    raw = path.read_text()
    assert essay_text not in raw
    assert "sys prompt text" not in raw
    assert "reply" in raw


def test_recording_file_names_the_model_and_a_format_version(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("r"), path)
    recorder.complete("s", "p")

    data = json.loads(path.read_text())
    assert data["format"] == 1
    assert data["model"] == "scripted-model"


def test_recording_extends_an_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("one"), path)
    recorder.complete("s", "p")
    recorder = RecordingClient(ScriptedClient("two"), path)
    recorder.complete("s", "p")

    replay = RecordedClient(path)
    assert [replay.complete("s", "p"), replay.complete("s", "p")] == ["one", "two"]


def test_recording_refuses_to_mix_models_in_one_file(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("one"), path)
    recorder.complete("s", "p")

    with pytest.raises(ValueError, match="another-model"):
        RecordingClient(ScriptedClient("two", model="another-model"), path)


def test_recording_refuses_to_mix_call_settings_in_one_file(tmp_path: Path) -> None:
    """Raising max_tokens to fix a truncation must not silently replay the old replies."""
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("one", max_tokens=100), path)
    recorder.complete("s", "p")

    with pytest.raises(ValueError, match="max_tokens"):
        RecordingClient(ScriptedClient("two", max_tokens=200), path)


def test_recording_file_pins_the_call_settings(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("r", max_tokens=321), path)
    recorder.complete("s", "p")
    data = json.loads(path.read_text())
    assert data["settings"] == {"max_tokens": 321}


def test_two_recorders_on_one_file_do_not_lose_each_others_replies(tmp_path: Path) -> None:
    """Each write re-reads the file, so a recorder never overwrites with a stale copy."""
    path = tmp_path / "rec.json"
    first = RecordingClient(ScriptedClient("a1", "a2"), path)
    second = RecordingClient(ScriptedClient("b1"), path)
    first.complete("s", "p")
    second.complete("s", "p")
    first.complete("s", "p")

    replay = RecordedClient(path)
    assert [replay.complete("s", "p") for _ in range(3)] == ["a1", "b1", "a2"]


def test_recording_client_passes_through_the_inner_clients_usage(tmp_path: Path) -> None:
    claude = ClaudeClient(messages_api=FakeMessages(_message("r", inp=11, out=2)))
    recorder = RecordingClient(claude, tmp_path / "rec.json")
    recorder.complete("s", "p")
    assert recorder.usage == UsageTotals(calls=1, input_tokens=11, output_tokens=2)


def test_recording_client_reports_no_usage_for_an_unmetered_inner_client(
    tmp_path: Path,
) -> None:
    recorder = RecordingClient(ScriptedClient("r"), tmp_path / "rec.json")
    recorder.complete("s", "p")
    assert recorder.usage is None


def test_prompt_key_is_stable_and_separates_its_two_parts() -> None:
    assert prompt_key("s", "p") == prompt_key("s", "p")
    assert prompt_key("s", "p") != prompt_key("s", "q")
    assert prompt_key("ab", "c") != prompt_key("a", "bc")


def test_the_recorder_keys_replies_with_the_shared_prompt_key(tmp_path: Path) -> None:
    """The future input-hash cache must reuse prompt_key, so the recorder must use it too."""
    path = tmp_path / "rec.json"
    RecordingClient(ScriptedClient("r"), path).complete("s", "p")
    assert set(json.loads(path.read_text())["replies"]) == {prompt_key("s", "p")}


def test_unknown_recording_format_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    path.write_text(json.dumps({"format": 99, "model": "m", "settings": {}, "replies": {}}))
    with pytest.raises(ValueError, match="format"):
        RecordedClient(path)


def test_recorded_and_recording_clients_are_model_clients(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    recorder = RecordingClient(ScriptedClient("r"), path)
    as_client: ModelClient = recorder
    as_client.complete("s", "p")
    replayed: ModelClient = RecordedClient(path)
    assert replayed.complete("s", "p") == "r"


@pytest.mark.parametrize("stop_reason", ["refusal", "pause_turn", "model_context_window_exceeded"])
def test_claude_client_refuses_an_incomplete_or_refused_reply(stop_reason: str) -> None:
    fake = FakeMessages(_message("partial", stop_reason=stop_reason))
    with pytest.raises(UnusableReplyError, match=stop_reason):
        ClaudeClient(messages_api=fake).complete("s", "p")


@pytest.mark.parametrize("texts", [(), ("  \n",)])
def test_claude_client_refuses_a_reply_with_no_text(texts: tuple[str, ...]) -> None:
    """An empty or whitespace-only reply must raise, or a recorder would save it and replay
    it as valid."""
    fake = FakeMessages(_message(*texts))
    with pytest.raises(UnusableReplyError, match="no text"):
        ClaudeClient(messages_api=fake).complete("s", "p")


def test_claude_client_accepts_a_stop_sequence_stop() -> None:
    fake = FakeMessages(_message("done", stop_reason="stop_sequence"))
    assert ClaudeClient(messages_api=fake).complete("s", "p") == "done"


def test_an_unusable_reply_is_not_recorded(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    claude = ClaudeClient(messages_api=FakeMessages(_message("no", stop_reason="refusal")))
    recorder = RecordingClient(claude, path)
    with pytest.raises(UnusableReplyError):
        recorder.complete("s", "p")
    assert not path.exists()


@pytest.mark.parametrize(
    "payload",
    [
        {"format": 1, "settings": {}, "replies": {}},
        {"format": 1, "model": "m", "replies": {}},
        {"format": 1, "model": "m", "settings": {}},
        {"format": 1, "model": "m", "settings": {}, "replies": {"k": "not a list"}},
        {"format": 1, "model": "m", "settings": {}, "replies": {"k": [1, 2]}},
        {"format": 1, "model": 3, "settings": {}, "replies": {}},
    ],
)
def test_a_malformed_recording_is_rejected_with_value_error(
    tmp_path: Path, payload: dict[str, object]
) -> None:
    path = tmp_path / "rec.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="malformed"):
        RecordedClient(path)


def test_a_header_mismatch_is_also_caught_at_write_time(tmp_path: Path) -> None:
    """Another recorder creates the file during this one's live call, so only the write-time
    check, not the pre-call check, can catch the mismatch."""
    path = tmp_path / "rec.json"
    other = RecordingClient(ScriptedClient("a", max_tokens=100), path)

    class RacingClient(ScriptedClient):
        def complete(self, system: str, prompt: str) -> str:
            other.complete(system, prompt)
            return super().complete(system, prompt)

    large = RecordingClient(RacingClient("b", max_tokens=200), path)
    with pytest.raises(ValueError, match="max_tokens"):
        large.complete("s", "p")


def test_a_header_mismatch_is_caught_before_the_paid_call(tmp_path: Path) -> None:
    path = tmp_path / "rec.json"
    inner = ScriptedClient("b", max_tokens=200)
    large = RecordingClient(inner, path)
    RecordingClient(ScriptedClient("a", max_tokens=100), path).complete("s", "p")
    with pytest.raises(ValueError, match="max_tokens"):
        large.complete("s", "p")
    assert inner.calls == 0


def test_claude_client_builds_the_real_sdk_client_when_a_key_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Construction makes no network call, so this checks the default path offline."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    client = ClaudeClient()
    assert client.model == PRIMARY_MODEL
    assert client.usage == UsageTotals()
