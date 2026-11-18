"""
Node class representing a node in a flow.
"""
from __future__ import annotations

import abc
from collections.abc import Mapping
from uuid import UUID

from flow_core.node_port import Connection, PortSpec


class Node(abc.ABC):

    node_id: UUID
    """Unique identifier for the node."""

    title: str
    """Human readable title of the node."""

    description: str
    """Optional description of the node."""

    port_specs: dict[str, PortSpec]
    """Mapping of port names to their specifications."""

    def __init__(self, node_id: UUID, title: str, description: str = ""):
        self.node_id = node_id
        self.title = title
        self.description = description
        self.port_specs = {}

    @abc.abstractmethod
    def execute(self):
        """Execute the node's logic."""
        raise NotImplementedError("Subclasses must implement the execute method.")


type NodeMapping = Mapping[UUID, "Node"]
"""Mapping of node IDs to Node instances."""


class FlowGraph:
    _nodes: dict[UUID, Node]
    _port_specs: dict[str, PortSpec]
    _connections: dict[UUID, list[Connection]]


    def __init__(self):
        self._nodes = {}
        self._port_specs = {}
        self._connections = {}

    @property
    def nodes(self) -> NodeMapping:
        return self._nodes
