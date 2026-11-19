from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class NodeResult:
    node_id: UUID
    exec_order: int
    time_ns: int
    logs: list[logging.LogRecord] = field(default_factory=list)
    exc: Exception | None = None


@dataclass(frozen=True)
class ExecutionResult:
    nodes: list[NodeResult] = field(default_factory=list)
