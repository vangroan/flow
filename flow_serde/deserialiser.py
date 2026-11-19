from pathlib import Path
from uuid import UUID

import yaml

from flow_core.errors import InvalidConnectionError
from flow_core.graph import FlowGraph
from flow_core.node import Node
from flow_core.node_port import PortRef
from flow_serde.reflection import find_type
from flow_serde.schema import validate

type PathLike = str | Path


def deserialise(data: dict) -> FlowGraph:
    validate(data)

    graph = FlowGraph()

    for node_data in data["nodes"]:
        qualname = node_data["pytype"]
        node_class = find_type(qualname)
        if not issubclass(node_class, Node):
            raise TypeError(f"{node_data['pytype']!r} is not a Node subclass")
        graph.add_node(node_class.from_data(node_data))

    for conn_data in data["connections"]:
        from_port_data = conn_data["from_port"]
        to_port_data = conn_data["to_port"]

        from_port = _lookup_port_ref(
            graph, UUID(from_port_data["node_id"]), from_port_data["port_name"]
        )
        to_port: PortRef = _lookup_port_ref(
            graph, UUID(to_port_data["node_id"]), to_port_data["port_name"]
        )

        graph.connect(from_port, to_port)

    return graph


def load_file(path: PathLike) -> FlowGraph:
    if isinstance(path, str):
        path = Path(path)

    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp)
        return deserialise(data)


def _lookup_port_ref(graph: FlowGraph, node_id: UUID, port_name: str) -> PortRef:
    node: Node | None = graph.get_node(node_id)
    if node is None:
        raise InvalidConnectionError(
            f"Graph file has invalid connection for node {node_id}"
        )

    try:
        return node.portref(port_name)
    except ValueError as e:
        raise InvalidConnectionError(
            f"Graph file has invalid connection for port {port_name!r} "
            f"on node {node_id}"
        ) from e
