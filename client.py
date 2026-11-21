"""A thin model client interface, so tests can replay recorded responses and cost can be counted."""

from typing import Protocol


class ModelClient(Protocol):
    """Anything that can complete a prompt. The real implementation will wrap the Claude API."""

    def complete(self, system: str, prompt: str) -> str:
        """Return the model's text reply for the given system and user prompts."""
        ...
