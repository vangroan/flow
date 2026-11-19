from pathlib import Path
from uuid import UUID

import jsonschema
import pytest

from flow_base.io_nodes import PrintNode
from flow_base.number_nodes import FloatLiteral, FloatToInteger
from flow_core.context import ExecutionContext
from flow_core.errors import InvalidConnectionError
from flow_core.node import Node
from flow_core.node_port import (
    Connection,
    PortDirection,
    PortSpec,
    PrimitiveType,
)
from flow_serde import deserialise, load_file
from flow_serde.reflection import TypeNotFoundError

ID_1 = "a0000000-0000-4000-9000-000000000001"
ID_2 = "a0000000-0000-4000-9000-000000000002"
ID_3 = "a0000000-0000-4000-9000-000000000003"

FLOAT_LITERAL = "flow_base.number_nodes:FloatLiteral"
FLOAT_TO_INT = "flow_base.number_nodes:FloatToInteger"
PRINT = "flow_base.io_nodes:PrintNode"

EXAMPLE_FILE = Path(__file__).parent / "example.yaml"


class ConfigurableNode(Node):
    """Node that restores extra configuration in ``from_data``."""

    def __init__(self, *, node_id: UUID, factor: int = 1):
        super().__init__(node_id=node_id)
        self.factor = factor
        self.port_specs.append(
            PortSpec(
                name="out",
                default_label="Out",
                port_type=PrimitiveType.INT,
                direction=PortDirection.OUTPUT,
            )
        )

    def execute(self, ctx: ExecutionContext):
        pass

    @classmethod
    def from_data(cls, data: dict) -> Node:
        return cls(node_id=UUID(data["node_id"]), factor=data["factor"])


class NotANode:
    pass


def node(node_id: str, pytype: str, **extra) -> dict:
    return {"node_id": node_id, "pytype": pytype, **extra}


def conn(from_id: str, from_port: str, to_id: str, to_port: str) -> dict:
    return {
        "from_port": {"node_id": from_id, "port_name": from_port},
        "to_port": {"node_id": to_id, "port_name": to_port},
    }


def graph_data(nodes=(), connections=()) -> dict:
    return {"nodes": list(nodes), "connections": list(connections)}


class TestDeserialiseNodes:
    def test_empty_graph(self):
        graph = deserialise(graph_data())

        assert len(graph.nodes) == 0
        assert graph.connections == frozenset()

    def test_node_type_and_id(self):
        graph = deserialise(graph_data([node(ID_1, FLOAT_LITERAL)]))

        node_ = graph.nodes[UUID(ID_1)]
        assert isinstance(node_, FloatLiteral)
        assert node_.node_id == UUID(ID_1)

    def test_multiple_nodes(self):
        graph = deserialise(
            graph_data(
                [
                    node(ID_1, FLOAT_LITERAL),
                    node(ID_2, FLOAT_TO_INT),
                    node(ID_3, PRINT),
                ]
            )
        )

        assert set(graph.nodes) == {UUID(ID_1), UUID(ID_2), UUID(ID_3)}
        assert isinstance(graph.nodes[UUID(ID_2)], FloatToInteger)
        assert isinstance(graph.nodes[UUID(ID_3)], PrintNode)

    def test_title_is_restored(self):
        graph = deserialise(graph_data([node(ID_1, FLOAT_LITERAL, title="Pi")]))

        assert graph.nodes[UUID(ID_1)].title == "Pi"

    def test_default_title_when_omitted(self):
        graph = deserialise(graph_data([node(ID_1, FLOAT_LITERAL)]))

        assert graph.nodes[UUID(ID_1)].title == "Float Literal"

    def test_custom_from_data(self):
        graph = deserialise(
            graph_data([node(ID_1, f"{__name__}:ConfigurableNode", factor=7)])
        )

        node_ = graph.nodes[UUID(ID_1)]
        assert isinstance(node_, ConfigurableNode)
        assert node_.factor == 7

    def test_unknown_module(self):
        with pytest.raises(TypeNotFoundError):
            deserialise(graph_data([node(ID_1, "no_such_module:Thing")]))

    def test_unknown_class(self):
        with pytest.raises(TypeNotFoundError):
            deserialise(graph_data([node(ID_1, "flow_base.number_nodes:Nope")]))

    def test_type_not_a_node(self):
        with pytest.raises(TypeError, match="not a Node subclass"):
            deserialise(graph_data([node(ID_1, f"{__name__}:NotANode")]))


class TestDeserialiseConnections:
    def test_connection(self):
        graph = deserialise(
            graph_data(
                [node(ID_1, FLOAT_LITERAL), node(ID_2, FLOAT_TO_INT)],
                [conn(ID_1, "value", ID_2, "value")],
            )
        )

        src = graph.nodes[UUID(ID_1)]
        dst = graph.nodes[UUID(ID_2)]
        assert graph.connections == frozenset(
            {Connection(src.portref("value"), dst.portref("value"))}
        )

    def test_chained_connections(self):
        graph = deserialise(
            graph_data(
                [
                    node(ID_1, FLOAT_LITERAL),
                    node(ID_2, FLOAT_TO_INT),
                    node(ID_3, PRINT),
                ],
                [
                    conn(ID_1, "value", ID_2, "value"),
                    conn(ID_2, "result", ID_3, "message"),
                ],
            )
        )

        assert len(graph.connections) == 2

    def test_connections_may_precede_nodes_in_file(self):
        # Connections are resolved after all nodes exist, regardless of order.
        data = {
            "connections": [conn(ID_1, "value", ID_2, "value")],
            "nodes": [node(ID_2, FLOAT_TO_INT), node(ID_1, FLOAT_LITERAL)],
        }

        assert len(deserialise(data).connections) == 1

    def test_unknown_source_node(self):
        with pytest.raises(InvalidConnectionError, match=ID_3):
            deserialise(
                graph_data(
                    [node(ID_2, FLOAT_TO_INT)],
                    [conn(ID_3, "value", ID_2, "value")],
                )
            )

    def test_unknown_target_node(self):
        with pytest.raises(InvalidConnectionError, match=ID_3):
            deserialise(
                graph_data(
                    [node(ID_1, FLOAT_LITERAL)],
                    [conn(ID_1, "value", ID_3, "value")],
                )
            )

    def test_unknown_port(self):
        with pytest.raises(InvalidConnectionError, match="'missing'"):
            deserialise(
                graph_data(
                    [node(ID_1, FLOAT_LITERAL), node(ID_2, FLOAT_TO_INT)],
                    [conn(ID_1, "missing", ID_2, "value")],
                )
            )

    def test_wrong_direction_is_rejected(self):
        # Graph-level rules still apply: an input can't be a source.
        with pytest.raises(InvalidConnectionError, match="source"):
            deserialise(
                graph_data(
                    [node(ID_1, FLOAT_LITERAL), node(ID_2, FLOAT_TO_INT)],
                    [conn(ID_2, "value", ID_1, "value")],
                )
            )

    def test_incompatible_types_are_rejected(self):
        # INT output into FLOAT input.
        with pytest.raises(InvalidConnectionError, match="Incompatible"):
            deserialise(
                graph_data(
                    [node(ID_1, FLOAT_TO_INT), node(ID_2, FLOAT_TO_INT)],
                    [conn(ID_1, "result", ID_2, "value")],
                )
            )


class TestSchemaValidation:
    @pytest.mark.parametrize(
        "data",
        [
            pytest.param({"connections": []}, id="missing-nodes"),
            pytest.param({"nodes": []}, id="missing-connections"),
            pytest.param({**graph_data(), "extra": 1}, id="extra-top-level-key"),
            pytest.param(graph_data([{"pytype": FLOAT_LITERAL}]), id="no-node-id"),
            pytest.param(graph_data([{"node_id": ID_1}]), id="no-pytype"),
            pytest.param(
                graph_data([node("not-a-uuid", FLOAT_LITERAL)]), id="bad-node-uuid"
            ),
            pytest.param(
                graph_data([node(ID_1, FLOAT_LITERAL, title=5)]), id="bad-title"
            ),
            pytest.param(
                graph_data(
                    connections=[{"to_port": {"node_id": ID_2, "port_name": "b"}}]
                ),
                id="no-from-port",
            ),
            pytest.param(
                graph_data(
                    connections=[{"from_port": {"node_id": ID_1, "port_name": "a"}}]
                ),
                id="no-to-port",
            ),
            pytest.param(
                graph_data(
                    connections=[
                        {
                            "from_port": {"node_id": ID_1},
                            "to_port": {"node_id": ID_2, "port_name": "b"},
                        }
                    ]
                ),
                id="no-port-name",
            ),
            pytest.param(
                graph_data(connections=[conn("bad", "a", ID_2, "b")]),
                id="bad-port-uuid",
            ),
        ],
    )
    def test_invalid_data_rejected(self, data: dict):
        with pytest.raises(jsonschema.ValidationError):
            deserialise(data)


class TestLoadFile:
    def test_example_file(self):
        graph = load_file(EXAMPLE_FILE)

        assert isinstance(graph.nodes[UUID(ID_1)], FloatLiteral)
        assert isinstance(graph.nodes[UUID(ID_2)], FloatToInteger)
        assert isinstance(graph.nodes[UUID(ID_3)], PrintNode)
        assert len(graph.connections) == 2

    def test_str_path(self):
        assert len(load_file(str(EXAMPLE_FILE)).nodes) == 3

    def test_utf8_content(self, tmp_path: Path):
        path = tmp_path / "graph.yaml"
        path.write_text(
            f"nodes:\n- node_id: {ID_1}\n  title: Float → Integer ✓\n"
            f"  pytype: {FLOAT_TO_INT}\n"
            "connections: []\n",
            encoding="utf-8",
        )

        graph = load_file(path)

        assert graph.nodes[UUID(ID_1)].title == "Float → Integer ✓"

    def test_empty_file(self, tmp_path: Path):
        path = tmp_path / "empty.yaml"
        path.write_text("", encoding="utf-8")

        with pytest.raises(jsonschema.ValidationError):
            load_file(path)

    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_file(tmp_path / "nope.yaml")
