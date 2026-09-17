"""Immutable-ish context describing one agent run invocation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """Everything the loop needs to know about a single run."""

    task: str  # the user instruction / goal for this run
    extra: dict[str, Any] = field(default_factory=dict)  # subscription snapshot etc.