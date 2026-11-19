from uuid import UUID

from flow_base.io_nodes import PrintNode
from flow_base.number_nodes import FloatLiteral, FloatToInteger
from flow_core.graph import FlowGraph


class TestFloatToIntegerNode:

    def test_basic_execution(self):
        graph = FlowGraph()

        node1 = FloatLiteral(node_id=UUID(int=1))
        node2 = FloatToInteger(node_id=UUID(int=2))
        node3 = PrintNode(node_id=UUID(int=3))

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(node3)

        graph.connect(node1.ref_port(0), node2.ref_port(0))
        graph.connect(node2.ref_port(1), node3.ref_port(0))
