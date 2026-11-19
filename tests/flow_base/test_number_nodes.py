from uuid import UUID

import pytest

from flow_base.io_nodes import PrintNode
from flow_base.number_nodes import FloatLiteral, FloatToInteger
from flow_core.executor import ForwardExecutor, NodeData
from flow_core.graph import FlowGraph


class TestFloatToIntegerNode:

    def test_basic_execution(self, capsys: pytest.CaptureFixture):
        graph = FlowGraph()

        node1 = FloatLiteral(node_id=UUID(int=1))
        node2 = FloatToInteger(node_id=UUID(int=2))
        node3 = PrintNode(node_id=UUID(int=3))

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)

        graph.connect(node1.portref(0), node2.portref(0))
        graph.connect(node2.portref(1), node3.portref(0))

        node_data = NodeData()
        node_data.set(node1.node_id, "value", 42.0)

        exec = ForwardExecutor()

        exec.execute(graph, node_data)

        captured = capsys.readouterr()
        assert captured.out.endswith("42\n")
