from __future__ import annotations


class TriageSystemUnavailable(RuntimeError):
    """Raised when the configured AI triage reasoner cannot produce output."""

    default_message = (
        "The triage AI system is unresponsive right now. " "Please try again shortly."
    )

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)
