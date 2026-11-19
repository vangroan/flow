"""
Nodes for input and output operations.
"""
from uuid import UUID

from flow_core.context import ExecutionContext
from flow_core.node import Node
from flow_core.node_port import PortDirection, PortSpec, PrimitiveType


class PrintNode(Node):
    """
    Node for printing output to ``stdout``.
    """

    def __init__(self, *, node_id: UUID):
        super().__init__(
            node_id=node_id,
            title="Print",
            description="Prints the given input to the console.",
        )

        self.port_specs.append(
            PortSpec(
                name="message",
                default_label="Message",
                port_type=PrimitiveType.ANY,
                direction=PortDirection.INPUT,
            )
        )

    def execute(self, ctx: ExecutionContext):
        message = ctx.inputs["message"]
        print(message)
