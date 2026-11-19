from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from flow_core.errors import InvalidConnectionError
from flow_core.node import Node
from flow_core.node_port import Connection, PortRef

type NodeMapping = Mapping[UUID, "Node"]
"""Mapping of node IDs to Node instances."""


class FlowGraph:
    _nodes: dict[UUID, Node]
    _connections: set[Connection]

    def __init__(self):
        self._nodes = {}
        self._connections = set()

    @property
    def nodes(self) -> NodeMapping:
        return MappingProxyType(self._nodes)

    def add_node(self, node: Node):
        """Add a node instance to the flow graph."""
        self._nodes[node.node_id] = node

    def contains_node_id(self, node_id: UUID) -> bool:
        return node_id in self._nodes

    def connect(self, from_port: PortRef, to_port: PortRef) -> Connection:
        if not self.contains_node_id(from_port.node_id):
            raise InvalidConnectionError(f"Node {from_port.node_id} is not part of this graph.")

        if not self.contains_node_id(to_port.node_id):
            raise InvalidConnectionError(f"Node {to_port.node_id} is not part of this graph.")

        conn = Connection(from_port, to_port)
        self._connections.add(conn)

        return conn
