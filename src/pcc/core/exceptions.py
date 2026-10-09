"""PccError hierarchy. All raised errors in this codebase subclass PccError."""


class PccError(Exception):
    """Base class for all application errors."""


class ContentValidationError(PccError):
    """Raised when curated content (careers, skills, roadmaps, questions) fails validation."""


class AiUnavailableError(PccError):
    """Raised when the configured AI provider cannot be reached (timeout, network, no key)."""


class AiOutputInvalidError(PccError):
    """Raised when an AI response fails schema or business-rule validation."""


class WorkflowStateError(PccError):
    """Raised when a workflow transition is attempted from an invalid state."""
