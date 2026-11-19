"""
Execution context.
"""
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    inputs: Mapping[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
