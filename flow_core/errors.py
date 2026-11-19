"""
Flow core error types.
"""


class FlowError(Exception):
    """
    Base class for all flow core errors.
    """


class NodeExecutionError(FlowError):
    """
    Raised when a node fails during execution.
    """

class InvalidConnectionError(FlowError):
    """
    Raised when two ports cannot be connected.
    """


class InvalidKeyError(FlowError):
    """
    Raised when an invalid key is encountered.
    """
