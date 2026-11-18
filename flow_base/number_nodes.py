"""
Nodes for processing primitive numbers.
"""
from uuid import UUID

from flow_core.node import Node


class FloatToInteger(Node):
    """
    Float → Integer Converter.
    """

    def __init__(self, *, node_id: UUID):
        super().__init__(
            node_id=node_id,
            title="Float → Integer",
            description="Converts a floating point number to an integer.",
        )

    def execute(self):
        raise NotImplementedError("TODO: Execution model still needs to be defined.")


class FloatLiteral(Node):
    """
    Represents a floating point literal node.
    """

    def __init__(self, *, node_id: UUID):
        super().__init__(
            node_id=node_id,
            title="Float Literal",
            description="Represents a floating point literal.",
        )

    def execute(self):
        raise NotImplementedError("TODO: Execution model still needs to be defined.")