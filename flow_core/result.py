from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class ExecutionResult:
    logs: dict[UUID, list[logging.LogRecord]] = field(default_factory=dict)
