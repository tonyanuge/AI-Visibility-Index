from abc import ABC, abstractmethod

class EngineRunner(ABC):
    name: str = "base"
    @property
    @abstractmethod
    def available(self) -> bool: ...
    @abstractmethod
    def run(self, prompt: str) -> str:
        """Return the assistant's raw answer text for a prompt. Mention extraction
        from this raw text is a human/assisted review step (see raw_responses table)."""
        ...
