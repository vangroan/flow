"""
Flow graph execution engine.
"""

from __future__ import annotations

import abc

from flow_core.graph import FlowGraph


class Executor(abc.ABC):
    """Abstract base class for flow graph executors."""

    @abc.abstractmethod
    def execute(self, graph: FlowGraph):
        """Execute the given flow graph."""
        raise NotImplementedError


class PullExecutor(Executor):
    """
    Executes a flow graph by pulling data from sending nodes to receiving nodes.

    Cycles are currently not supported.

    Nodes with no outgoing edges, and no side-effects, will not be executed.
    """

    # TODO: Implement the pull-based execution logic for the flow graph.

    def execute(self, graph: FlowGraph):
        """Execute the flow graph using pull-based strategy."""
        # Implementation will go here.
        raise NotImplementedError
