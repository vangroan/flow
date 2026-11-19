from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from flow_core.errors import GraphLockedError, InvalidConnectionError
from flow_core.node import Node
from flow_core.node_port import (
    Connection,
    PortDirection,
    PortRef,
    PortType,
    PrimitiveType,
)

type NodeMapping = Mapping[UUID, "Node"]
"""Mapping of node IDs to Node instances."""


class FlowGraph:
    _nodes: dict[UUID, Node]
    _connections: set[Connection]
    _locked: bool

    def __init__(self):
        self._nodes = {}
        self._connections = set()
        self._locked = False

    @property
    def nodes(self) -> NodeMapping:
        return MappingProxyType(self._nodes)

    @property
    def connections(self) -> frozenset[Connection]:
        return frozenset(self._connections)

    def _check_lock(self):
        if self._locked:
            raise GraphLockedError("Flow graph is locked for execution.")

    def add_node(self, node: Node):
        """Add a node instance to the flow graph."""
        self._check_lock()
        self._nodes[node.node_id] = node

    def contains_node_id(self, node_id: UUID) -> bool:
        return node_id in self._nodes

    def connect(self, from_port: PortRef, to_port: PortRef) -> Connection:
        self._check_lock()

        if not self.contains_node_id(from_port.node_id):
            raise InvalidConnectionError(
                f"Node {from_port.node_id} is not part of this graph."
            )

        if not self.contains_node_id(to_port.node_id):
            raise InvalidConnectionError(
                f"Node {to_port.node_id} is not part of this graph."
            )

        self._check_port_exists(from_port)
        self._check_port_exists(to_port)

        if from_port.spec.direction not in _SOURCE_DIRECTIONS:
            raise InvalidConnectionError(
                f"Port '{from_port.spec.name}' cannot be used as a source: "
                f"direction is {from_port.spec.direction.name}."
            )

        if to_port.spec.direction not in _TARGET_DIRECTIONS:
            raise InvalidConnectionError(
                f"Port '{to_port.spec.name}' cannot be used as a target: "
                f"direction is {to_port.spec.direction.name}."
            )

        if not _types_compatible(from_port.spec.port_type, to_port.spec.port_type):
            raise InvalidConnectionError(
                f"Incompatible port types: '{from_port.spec.name}' "
                f"({from_port.spec.port_type}) cannot connect to "
                f"'{to_port.spec.name}' ({to_port.spec.port_type})."
            )

        conn = Connection(from_port, to_port)
        self._connections.add(conn)

        return conn

    def _check_port_exists(self, port: PortRef):
        """Ensure the referenced port is declared by its node."""
        node = self._nodes[port.node_id]

        if port.spec not in node.port_specs:
            raise InvalidConnectionError(
                f"Port '{port.spec.name}' does not exist on node {port.node_id}."
            )


_SOURCE_DIRECTIONS = frozenset({PortDirection.OUTPUT, PortDirection.INOUT})
_TARGET_DIRECTIONS = frozenset({PortDirection.INPUT, PortDirection.INOUT})


def _types_compatible(source: PortType, target: PortType) -> bool:
    """
    Whether a value of the source type may flow into the target type.

    Types are compatible when they are equal or either side is ANY.
    """
    if source == target:
        return True

    return PrimitiveType.ANY in (source, target)
