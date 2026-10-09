"""Abstract AI client interface. UI code must never import a concrete adapter directly."""

from abc import ABC, abstractmethod


class AiClient(ABC):
    """One method: send a prompt, get raw text back. Callers parse/validate the result."""

    @abstractmethod
    def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.2) -> str:
        """Return raw model output as text.

        Raises AiUnavailableError on timeout/network/auth failure.
        """
        raise NotImplementedError
