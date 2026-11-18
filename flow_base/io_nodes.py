"""
Nodes for input and output operations.
"""
from uuid import UUID

from flow_core.node import Node


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

    def execute(self):
        raise NotImplementedError("TODO: Execution model still needs to be defined.")
