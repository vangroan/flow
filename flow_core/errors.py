"""
Flow core error types.
"""
from uuid import UUID


class FlowError(Exception):
    """
    Base class for all flow core errors.
    """


class GraphLockedError(FlowError):
    """
    Raised when the graph is locked for execution.
    """


class NodeExecutionError(FlowError):
    """
    Raised when a node fails during execution.
    """


class InvalidConnectionError(FlowError):
    """
    Raised when two ports cannot be connected.
    """


class CycleError(FlowError):
    """
    Raised when the flow graph contains a cycle and cannot be ordered.
    """

    node_ids: list[UUID]

    def __init__(self, message: str, *, node_ids: list[UUID]):
        self.node_ids = node_ids

        super().__init__(message)


class InvalidNodeError(FlowError):
    """
    Raised when a node's ports fail validation.
    """

    errors: dict[UUID, list[str]]

    def __init__(self, message: str, *, validation_errors: dict[UUID, list[str]]):
        self.errors = validation_errors

        super().__init__(message)
