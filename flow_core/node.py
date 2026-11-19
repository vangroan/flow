"""
Node class representing a node in a flow.
"""

from __future__ import annotations

import abc
from uuid import UUID

from flow_core.node_port import PortRef, PortSpec


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

    def ref_port(self, port_index: int) -> PortRef:
        """Create a reference to the port at the given index."""
        return PortRef(self.node_id, self.port_specs[port_index])

    @abc.abstractmethod
    def execute(self):
        """Execute the node's logic."""
        raise NotImplementedError("Subclasses must implement the execute method.")
