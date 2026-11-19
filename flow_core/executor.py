"""
Flow graph execution engine.
"""

from __future__ import annotations

import abc
import logging
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from queue import Queue
from types import MappingProxyType
from typing import Any, Generator, Mapping
from uuid import UUID

from flow_core import logging_ext
from flow_core.context import ExecutionContext
from flow_core.errors import CycleError, InvalidNodeError, NodeExecutionError
from flow_core.graph import FlowGraph
from flow_core.node import Node
from flow_core.node_port import Connection, PortDirection
from flow_core.result import ExecutionResult

type _DataKey = tuple[UUID, str]
"""Node data mapping key (node_id, port_spec.name)"""


@dataclass(frozen=True)
class NodeData:
    """
    Data used to populate node ports on an execution run.
    """

    _values: dict[_DataKey, Any] = field(default_factory=dict)

    def set(self, node_id: UUID, port_name: str, value: Any):
        self._values[(node_id, port_name)] = value


_EMPTY_NODE_DATA = NodeData()


class Executor(abc.ABC):
    """Abstract base class for flow graph executors."""

    @abc.abstractmethod
    def execute(self, graph: FlowGraph):
        """Execute the given flow graph."""
        raise NotImplementedError


class ForwardExecutor(Executor):
    """
    Executes a flow graph by pushing data forward through node connections. All
    nodes are executed, even if they don't have any side effects.

    Cycles are currently not supported.
    """

    def _validate_nodes(self, graph: FlowGraph):
        graph_errors: dict[UUID, list[str]] = {}

        for node_id, node in graph.nodes.items():
            validation_result = node.validate()
            if not validation_result.is_valid:
                if node_id not in graph_errors:
                    graph_errors[node_id] = [*validation_result.errors]
                else:
                    graph_errors[node_id].extend(validation_result.errors)

        if graph_errors:
            raise InvalidNodeError("Nodes are invalid", validation_errors=graph_errors)

    def _sort_nodes(self, graph: FlowGraph) -> list[UUID]:
        """
        Sort node IDs in the order they must be executed (topological order),
        so that every node runs after all nodes that feed into it.

        Raises:
            - CycleError: When the graph contains a cycle.
        """
        successors: dict[UUID, set[UUID]] = {node_id: set() for node_id in graph.nodes}
        in_degree: dict[UUID, int] = {node_id: 0 for node_id in graph.nodes}

        for conn in graph.connections:
            src, dst = conn.from_port.node_id, conn.to_port.node_id
            if dst not in successors[src]:
                successors[src].add(dst)
                in_degree[dst] += 1

        ready = deque(node_id for node_id, deg in in_degree.items() if deg == 0)
        order: list[UUID] = []

        while ready:
            node_id = ready.popleft()
            order.append(node_id)

            for succ in successors[node_id]:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    ready.append(succ)

        if len(order) != len(graph.nodes):
            cyclic = [node_id for node_id, deg in in_degree.items() if deg > 0]
            raise CycleError("Flow graph contains a cycle", node_ids=cyclic)

        return order

    @staticmethod
    def _create_execution_context(
        node: Node,
        node_data: NodeData,
        upstream: Mapping[str, Any] | None = None,
    ) -> ExecutionContext:
        inputs: dict[str, Any] = {}
        outputs: dict[str, Any] = {}
        upstream = upstream or {}

        def get_data(name: str, default: Any) -> Any:
            return node_data._values.get((node.node_id, name), default)

        # Default port values for node invocation.
        for port_spec in node.port_specs:
            match port_spec.direction:
                case PortDirection.INPUT:
                    inputs[port_spec.name] = get_data(port_spec.name, port_spec.default)
                case PortDirection.OUTPUT:
                    outputs[port_spec.name] = get_data(
                        port_spec.name, port_spec.default
                    )
                case PortDirection.INOUT:
                    inputs[port_spec.name] = get_data(port_spec.name, port_spec.default)
                    outputs[port_spec.name] = get_data(
                        port_spec.name, port_spec.default
                    )

        # Values pushed from connected upstream nodes take precedence.
        inputs.update(upstream)

        return ExecutionContext(MappingProxyType(inputs), outputs)

    def execute(
        self, graph: FlowGraph, data: NodeData | None = None
    ) -> ExecutionResult:
        """
        Execute the flow graph using pull-based strategy.

        Args:
            graph: The graph describing the logic flow to execute.
            data: The values assigned to node ports by a user via a frontend.

        Raises:
            InvalidNodeError: When a node in the graph has invalid ports configured.
            CycleError: When the graph contains a cycle.
        """
        log_records: dict[UUID, list[logging.LogRecord]] = {}
        log_queue: Queue[logging.LogRecord] = Queue()

        with _flow_mutation_guard(graph):
            self._validate_nodes(graph)

            execution_order = self._sort_nodes(graph)
            nodes = graph.nodes
            node_data = data or _EMPTY_NODE_DATA

            # Mapping of nodes to their incoming connections.
            incoming: dict[UUID, list[Connection]] = {node_id: [] for node_id in nodes}
            for conn in graph.connections:
                incoming[conn.to_port.node_id].append(conn)

            # Mapping of nodes to their execution outputs.
            results: dict[UUID, dict[str, Any]] = {}

            for node_id in execution_order:
                node = nodes[node_id]

                upstream = {
                    conn.to_port.spec.name: results[conn.from_port.node_id][
                        conn.from_port.spec.name
                    ]
                    for conn in incoming[node_id]
                }
                ctx = self._create_execution_context(node, node_data, upstream)

                try:
                    with logging_ext.capture_logs(log_queue):
                        node.execute(ctx)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as exc:
                    raise NodeExecutionError("Error in node execution.") from exc
                finally:
                    log_records[node_id] = _drain_queue(log_queue)

                results[node_id] = ctx.outputs

        return ExecutionResult(logs=log_records)


@contextmanager
def _flow_mutation_guard(graph: FlowGraph) -> Generator[None]:
    graph._locked = True
    try:
        yield
    finally:
        graph._locked = False


def _drain_queue[T](queue: Queue[T]) -> list[T]:
    result: list[T] = []

    while not queue.empty():
        result.append(queue.get_nowait())

    return result
