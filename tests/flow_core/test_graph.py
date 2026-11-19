from uuid import UUID

import pytest

from flow_core.context import ExecutionContext
from flow_core.errors import GraphLockedError, InvalidConnectionError
from flow_core.graph import FlowGraph
from flow_core.node import Node
from flow_core.node_port import (
    Connection,
    ListType,
    PortDirection,
    PortRef,
    PortSpec,
    PrimitiveType,
)


class DummyNode(Node):
    def __init__(self, n: int):
        super().__init__(node_id=UUID(int=n), title=f"Dummy {n}")
        self.port_specs.append(
            PortSpec(
                name="in",
                default_label="In",
                port_type=PrimitiveType.ANY,
                direction=PortDirection.INPUT,
            )
        )
        self.port_specs.append(
            PortSpec(
                name="out",
                default_label="Out",
                port_type=PrimitiveType.ANY,
                direction=PortDirection.OUTPUT,
            )
        )

    def execute(self, ctx: ExecutionContext):
        pass


@pytest.fixture
def graph() -> FlowGraph:
    return FlowGraph()


class TestInitialState:
    def test_empty_nodes(self, graph: FlowGraph):
        assert len(graph.nodes) == 0

    def test_empty_connections(self, graph: FlowGraph):
        assert graph.connections == frozenset()


class TestAddNode:
    def test_add_node(self, graph: FlowGraph):
        node = DummyNode(1)
        graph.add_node(node)

        assert graph.nodes[node.node_id] is node
        assert len(graph.nodes) == 1

    def test_add_multiple_nodes(self, graph: FlowGraph):
        a, b = DummyNode(1), DummyNode(2)
        graph.add_node(a)
        graph.add_node(b)

        assert set(graph.nodes) == {a.node_id, b.node_id}

    def test_add_same_id_replaces_node(self, graph: FlowGraph):
        first, second = DummyNode(1), DummyNode(1)
        graph.add_node(first)
        graph.add_node(second)

        assert len(graph.nodes) == 1
        assert graph.nodes[first.node_id] is second

    def test_add_node_when_locked_raises(self, graph: FlowGraph):
        graph._locked = True

        with pytest.raises(GraphLockedError):
            graph.add_node(DummyNode(1))

        assert len(graph.nodes) == 0


class TestContainsNodeId:
    def test_present(self, graph: FlowGraph):
        node = DummyNode(1)
        graph.add_node(node)

        assert graph.contains_node_id(node.node_id)

    def test_absent(self, graph: FlowGraph):
        assert not graph.contains_node_id(UUID(int=99))

    def test_absent_after_adding_other_node(self, graph: FlowGraph):
        graph.add_node(DummyNode(1))

        assert not graph.contains_node_id(UUID(int=2))


class TestNodesProperty:
    def test_is_read_only(self, graph: FlowGraph):
        graph.add_node(DummyNode(1))

        with pytest.raises(TypeError):
            graph.nodes[UUID(int=2)] = DummyNode(2)  # type: ignore

        with pytest.raises(TypeError):
            del graph.nodes[UUID(int=1)]  # type: ignore

    def test_is_live_view(self, graph: FlowGraph):
        view = graph.nodes
        node = DummyNode(1)
        graph.add_node(node)

        assert view[node.node_id] is node


class TestConnect:
    def test_connect_returns_connection(self, graph: FlowGraph):
        a, b = DummyNode(1), DummyNode(2)
        graph.add_node(a)
        graph.add_node(b)

        conn = graph.connect(a.portref("out"), b.portref("in"))

        assert isinstance(conn, Connection)
        assert conn.from_port == a.portref("out")
        assert conn.to_port == b.portref("in")

    def test_connect_registers_connection(self, graph: FlowGraph):
        a, b = DummyNode(1), DummyNode(2)
        graph.add_node(a)
        graph.add_node(b)

        conn = graph.connect(a.portref("out"), b.portref("in"))

        assert graph.connections == frozenset({conn})

    def test_connect_duplicate_is_idempotent(self, graph: FlowGraph):
        a, b = DummyNode(1), DummyNode(2)
        graph.add_node(a)
        graph.add_node(b)

        c1 = graph.connect(a.portref("out"), b.portref("in"))
        c2 = graph.connect(a.portref("out"), b.portref("in"))

        assert c1 == c2
        assert len(graph.connections) == 1

    def test_connect_multiple(self, graph: FlowGraph):
        a, b, c = DummyNode(1), DummyNode(2), DummyNode(3)
        for n in (a, b, c):
            graph.add_node(n)

        c1 = graph.connect(a.portref("out"), b.portref("in"))
        c2 = graph.connect(b.portref("out"), c.portref("in"))

        assert graph.connections == frozenset({c1, c2})

    def test_unknown_source_node_raises(self, graph: FlowGraph):
        a, ghost = DummyNode(1), DummyNode(2)
        graph.add_node(a)

        with pytest.raises(InvalidConnectionError):
            graph.connect(ghost.portref("out"), a.portref("in"))

        assert graph.connections == frozenset()

    def test_unknown_target_node_raises(self, graph: FlowGraph):
        a, ghost = DummyNode(1), DummyNode(2)
        graph.add_node(a)

        with pytest.raises(InvalidConnectionError):
            graph.connect(a.portref("out"), ghost.portref("in"))

        assert graph.connections == frozenset()

    def test_connect_when_locked_raises(self, graph: FlowGraph):
        a, b = DummyNode(1), DummyNode(2)
        graph.add_node(a)
        graph.add_node(b)
        graph._locked = True

        with pytest.raises(GraphLockedError):
            graph.connect(a.portref("out"), b.portref("in"))

        assert graph.connections == frozenset()

    def test_locked_checked_before_validation(self, graph: FlowGraph):
        ghost = DummyNode(1)
        graph._locked = True

        with pytest.raises(GraphLockedError):
            graph.connect(ghost.portref("out"), ghost.portref("in"))


class TypedNode(Node):
    """Node with one port of the given type and direction."""

    def __init__(self, n: int, port_type, direction):
        super().__init__(node_id=UUID(int=n), title=f"Typed {n}")
        self.port_specs.append(
            PortSpec(
                name="p",
                default_label="P",
                port_type=port_type,
                direction=direction,
            )
        )

    def execute(self, ctx: ExecutionContext):
        pass


class TestConnectValidity:
    def test_port_not_declared_on_node_raises(self, graph: FlowGraph):
        a, b = DummyNode(1), DummyNode(2)
        graph.add_node(a)
        graph.add_node(b)
        foreign = PortRef(
            a.node_id,
            PortSpec(
                name="nope",
                default_label="Nope",
                port_type=PrimitiveType.ANY,
                direction=PortDirection.OUTPUT,
            ),
        )

        with pytest.raises(InvalidConnectionError):
            graph.connect(foreign, b.portref("in"))

        with pytest.raises(InvalidConnectionError):
            graph.connect(a.portref("out"), PortRef(b.node_id, foreign.spec))

        assert graph.connections == frozenset()

    def test_input_port_as_source_raises(self, graph: FlowGraph):
        a, b = DummyNode(1), DummyNode(2)
        graph.add_node(a)
        graph.add_node(b)

        with pytest.raises(InvalidConnectionError):
            graph.connect(a.portref("in"), b.portref("in"))

    def test_output_port_as_target_raises(self, graph: FlowGraph):
        a, b = DummyNode(1), DummyNode(2)
        graph.add_node(a)
        graph.add_node(b)

        with pytest.raises(InvalidConnectionError):
            graph.connect(a.portref("out"), b.portref("out"))

    def test_inout_allowed_on_both_sides(self, graph: FlowGraph):
        a = TypedNode(1, PrimitiveType.INT, PortDirection.INOUT)
        b = TypedNode(2, PrimitiveType.INT, PortDirection.INOUT)
        graph.add_node(a)
        graph.add_node(b)

        conn = graph.connect(a.portref("p"), b.portref("p"))

        assert conn in graph.connections

    def test_matching_types_allowed(self, graph: FlowGraph):
        a = TypedNode(1, PrimitiveType.FLOAT, PortDirection.OUTPUT)
        b = TypedNode(2, PrimitiveType.FLOAT, PortDirection.INPUT)
        graph.add_node(a)
        graph.add_node(b)

        graph.connect(a.portref("p"), b.portref("p"))

        assert len(graph.connections) == 1

    def test_mismatched_types_raise(self, graph: FlowGraph):
        a = TypedNode(1, PrimitiveType.FLOAT, PortDirection.OUTPUT)
        b = TypedNode(2, PrimitiveType.STRING, PortDirection.INPUT)
        graph.add_node(a)
        graph.add_node(b)

        with pytest.raises(InvalidConnectionError):
            graph.connect(a.portref("p"), b.portref("p"))

        assert graph.connections == frozenset()

    @pytest.mark.parametrize("any_side", ["source", "target"])
    def test_any_is_compatible_with_everything(
        self, graph: FlowGraph, any_side: str
    ):
        any_ty, other = PrimitiveType.ANY, PrimitiveType.INT
        src_ty, dst_ty = (
            (any_ty, other) if any_side == "source" else (other, any_ty)
        )
        a = TypedNode(1, src_ty, PortDirection.OUTPUT)
        b = TypedNode(2, dst_ty, PortDirection.INPUT)
        graph.add_node(a)
        graph.add_node(b)

        graph.connect(a.portref("p"), b.portref("p"))

        assert len(graph.connections) == 1

    def test_list_types_must_match_item_type(self, graph: FlowGraph):
        a = TypedNode(1, ListType(PrimitiveType.INT), PortDirection.OUTPUT)
        ok = TypedNode(2, ListType(PrimitiveType.INT), PortDirection.INPUT)
        bad = TypedNode(3, ListType(PrimitiveType.STRING), PortDirection.INPUT)
        for n in (a, ok, bad):
            graph.add_node(n)

        graph.connect(a.portref("p"), ok.portref("p"))

        with pytest.raises(InvalidConnectionError):
            graph.connect(a.portref("p"), bad.portref("p"))

    def test_list_not_compatible_with_primitive(self, graph: FlowGraph):
        a = TypedNode(1, ListType(PrimitiveType.INT), PortDirection.OUTPUT)
        b = TypedNode(2, PrimitiveType.INT, PortDirection.INPUT)
        graph.add_node(a)
        graph.add_node(b)

        with pytest.raises(InvalidConnectionError):
            graph.connect(a.portref("p"), b.portref("p"))


class TestConnectionsProperty:
    def test_returns_snapshot(self, graph: FlowGraph):
        a, b = DummyNode(1), DummyNode(2)
        graph.add_node(a)
        graph.add_node(b)

        snapshot = graph.connections
        graph.connect(a.portref("out"), b.portref("in"))

        assert snapshot == frozenset()
        assert len(graph.connections) == 1

    def test_is_immutable(self, graph: FlowGraph):
        assert isinstance(graph.connections, frozenset)


class TestLocking:
    def test_unlocking_restores_mutation(self, graph: FlowGraph):
        graph._locked = True
        with pytest.raises(GraphLockedError):
            graph.add_node(DummyNode(1))

        graph._locked = False
        graph.add_node(DummyNode(1))

        assert graph.contains_node_id(UUID(int=1))

    def test_read_access_allowed_when_locked(self, graph: FlowGraph):
        node = DummyNode(1)
        graph.add_node(node)
        graph._locked = True

        assert graph.contains_node_id(node.node_id)
        assert graph.nodes[node.node_id] is node
        assert graph.connections == frozenset()
