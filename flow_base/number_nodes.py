"""
Nodes for processing primitive numbers.
"""
from uuid import UUID

from flow_core.context import ExecutionContext
from flow_core.node import Node
from flow_core.node_port import PortDirection, PortSpec, PrimitiveType


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

        self.port_specs.append(
            PortSpec(
                name="value",
                default_label="Value",
                direction=PortDirection.INPUT,
                port_type=PrimitiveType.FLOAT,
            )
        )

        self.port_specs.append(
            PortSpec(
                name="result",
                default_label="Result",
                direction=PortDirection.OUTPUT,
                port_type=PrimitiveType.INT,
            )
        )

    def execute(self, ctx: ExecutionContext):
        value = ctx.inputs["value"]
        ctx.outputs["result"] = int(value)


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

        self.port_specs.append(
            PortSpec(
                name="value",
                default_label="Value",
                direction=PortDirection.OUTPUT,
                port_type=PrimitiveType.FLOAT,
                default=0.0,
            )
        )

    def execute(self, ctx: ExecutionContext):
        # Port value set by executor.
        pass
