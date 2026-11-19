"""
Node class representing a node in a flow.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from uuid import UUID

from flow_core.context import ExecutionContext
from flow_core.node_port import PortRef, PortSpec

type PortIdentifier = str | int
"""Either the port name or index."""


@dataclass(frozen=True)
class NodeValidationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


class Node(abc.ABC):

    node_id: UUID
    """Unique identifier for the node."""

    title: str
    """Human readable title of the node."""

    description: str
    """Optional description of the node."""

    port_specs: list[PortSpec]
    """Mapping of port names to their specifications."""

    def __init__(self, *, node_id: UUID, title: str, description: str = ""):
        self.node_id = node_id
        self.title = title
        self.description = description
        self.port_specs = []

    def portref(self, port: PortIdentifier) -> PortRef:
        """Create a reference to the port at the given index."""

        match port:
            case int():
                return PortRef(self.node_id, self.port_specs[port])
            case str():
                if port_spec := next((p for p in self.port_specs if p.name == port), None):
                    return PortRef(self.node_id, port_spec)
                raise ValueError(f"Port not found: {port}")
            case _:
                raise TypeError("Argument must be a string or integer: 'port'")

    def validate(self) -> NodeValidationResult:
        """
        Validate the internal integrity of this node.
        """
        seen: set[str] = set()
        errors: list[str] = []

        for port_spec in self.port_specs:
            if port_spec.name in seen:
                errors.append(f"Port already decalred: {port_spec.name}")
            else:
                seen.add(port_spec.name)

        return NodeValidationResult(errors)

    @abc.abstractmethod
    def execute(self, ctx: ExecutionContext):
        """Execute the node's logic."""
        raise NotImplementedError("Subclasses must implement the execute method.")
