import logging
from typing import Any, Callable
from uuid import UUID

import pytest

from flow_core.context import ExecutionContext
from flow_core.errors import (
    CycleError,
    GraphLockedError,
    InvalidNodeError,
    NodeExecutionError,
)
from flow_core.executor import Executor, ForwardExecutor, NodeData
from flow_core.graph import FlowGraph
from flow_core.node import Node
from flow_core.node_port import PortDirection, PortSpec, PrimitiveType


class FuncNode(Node):
    """
    Node with ports "in" (INPUT, default 0) and "out" (OUTPUT) whose behaviour
    is supplied by a callable. Records every context it was executed with.
    """

    def __init__(
        self,
        n: int,
        func: Callable[[ExecutionContext], None] | None = None,
        in_default: Any = 0,
    ):
        super().__init__(node_id=UUID(int=n), title=f"Func {n}")
        self.port_specs.append(
            PortSpec(
                name="in",
                default_label="In",
                port_type=PrimitiveType.ANY,
                direction=PortDirection.INPUT,
                default=in_default,
            )
        )
        self.port_specs.append(
            PortSpec(
                name="out",
                default_label="Out",
                port_type=PrimitiveType.ANY,
                direction=PortDirection.OUTPUT,
            )
        )
        self.func = func
        self.contexts: list[ExecutionContext] = []

    def execute(self, ctx: ExecutionContext):
        self.contexts.append(ctx)
        if self.func:
            self.func(ctx)


def passthrough_plus(amount: int) -> Callable[[ExecutionContext], None]:
    def func(ctx: ExecutionContext):
        ctx.outputs["out"] = ctx.inputs["in"] + amount

    return func


def make_chain(*nodes: Node) -> FlowGraph:
    graph = FlowGraph()
    for node in nodes:
        graph.add_node(node)
    for a, b in zip(nodes, nodes[1:], strict=False):
        graph.connect(a.portref("out"), b.portref("in"))
    return graph


@pytest.fixture
def executor() -> ForwardExecutor:
    return ForwardExecutor()


class TestBasics:
    def test_is_an_executor(self, executor: ForwardExecutor):
        assert isinstance(executor, Executor)

    def test_empty_graph(self, executor: ForwardExecutor):
        result = executor.execute(FlowGraph())

        assert result.nodes == []

    def test_every_node_executes_once(self, executor: ForwardExecutor):
        nodes = [FuncNode(i) for i in range(1, 4)]
        graph = FlowGraph()
        for n in nodes:
            graph.add_node(n)

        result = executor.execute(graph)

        assert all(len(n.contexts) == 1 for n in nodes)
        assert {r.node_id for r in result.nodes} == {n.node_id for n in nodes}

    def test_data_is_optional(self, executor: ForwardExecutor):
        node = FuncNode(1)
        graph = FlowGraph()
        graph.add_node(node)

        executor.execute(graph)
        executor.execute(graph, None)

        assert len(node.contexts) == 2


class TestOrdering:
    def test_chain_runs_in_dependency_order(self, executor: ForwardExecutor):
        a, b, c = FuncNode(1), FuncNode(2), FuncNode(3)
        # Insert in reverse so insertion order differs from execution order.
        graph = FlowGraph()
        for n in (c, b, a):
            graph.add_node(n)
        graph.connect(a.portref("out"), b.portref("in"))
        graph.connect(b.portref("out"), c.portref("in"))

        result = executor.execute(graph)

        assert [r.node_id for r in result.nodes] == [
            a.node_id,
            b.node_id,
            c.node_id,
        ]

    def test_exec_order_is_one_based_and_sequential(
        self, executor: ForwardExecutor
    ):
        graph = make_chain(FuncNode(1), FuncNode(2), FuncNode(3))

        result = executor.execute(graph)

        assert [r.exec_order for r in result.nodes] == [1, 2, 3]

    def test_diamond_runs_join_last(self, executor: ForwardExecutor):
        src, left, right, join = (FuncNode(i) for i in range(1, 5))
        graph = FlowGraph()
        for n in (join, left, right, src):
            graph.add_node(n)
        graph.connect(src.portref("out"), left.portref("in"))
        graph.connect(src.portref("out"), right.portref("in"))
        graph.connect(left.portref("out"), join.portref("in"))
        graph.connect(right.portref("out"), join.portref("in"))

        result = executor.execute(graph)
        order = [r.node_id for r in result.nodes]

        assert order[0] == src.node_id
        assert order[-1] == join.node_id

    def test_time_is_recorded(self, executor: ForwardExecutor):
        graph = make_chain(FuncNode(1))

        result = executor.execute(graph)

        assert result.nodes[0].time_ns >= 0


class TestDataFlow:
    def test_values_propagate_downstream(self, executor: ForwardExecutor):
        a = FuncNode(1, passthrough_plus(10), in_default=1)
        b = FuncNode(2, passthrough_plus(100))
        c = FuncNode(3)
        graph = make_chain(a, b, c)

        executor.execute(graph)

        assert a.contexts[0].inputs["in"] == 1
        assert b.contexts[0].inputs["in"] == 11
        assert c.contexts[0].inputs["in"] == 111

    def test_unconnected_input_uses_port_default(
        self, executor: ForwardExecutor
    ):
        node = FuncNode(1, in_default=7)
        graph = FlowGraph()
        graph.add_node(node)

        executor.execute(graph)

        assert node.contexts[0].inputs["in"] == 7

    def test_node_data_overrides_port_default(self, executor: ForwardExecutor):
        node = FuncNode(1, in_default=7)
        graph = FlowGraph()
        graph.add_node(node)
        data = NodeData()
        data.set(node.node_id, "in", 42)

        executor.execute(graph, data)

        assert node.contexts[0].inputs["in"] == 42

    def test_node_data_is_scoped_to_node(self, executor: ForwardExecutor):
        a, b = FuncNode(1, in_default=1), FuncNode(2, in_default=2)
        graph = FlowGraph()
        graph.add_node(a)
        graph.add_node(b)
        data = NodeData()
        data.set(a.node_id, "in", 99)

        executor.execute(graph, data)

        assert a.contexts[0].inputs["in"] == 99
        assert b.contexts[0].inputs["in"] == 2

    def test_node_data_can_preset_output(self, executor: ForwardExecutor):
        a, b = FuncNode(1), FuncNode(2)
        graph = make_chain(a, b)
        data = NodeData()
        data.set(a.node_id, "out", "preset")

        executor.execute(graph, data)

        assert b.contexts[0].inputs["in"] == "preset"

    def test_upstream_value_overrides_node_data(
        self, executor: ForwardExecutor
    ):
        a = FuncNode(1, passthrough_plus(1), in_default=1)
        b = FuncNode(2)
        graph = make_chain(a, b)
        data = NodeData()
        data.set(b.node_id, "in", "ignored")

        executor.execute(graph, data)

        assert b.contexts[0].inputs["in"] == 2

    def test_unset_output_propagates_port_default(
        self, executor: ForwardExecutor
    ):
        a, b = FuncNode(1), FuncNode(2)
        graph = make_chain(a, b)

        executor.execute(graph)

        assert b.contexts[0].inputs["in"] is None

    def test_one_output_fans_out_to_many(self, executor: ForwardExecutor):
        src = FuncNode(1, passthrough_plus(5))
        b, c = FuncNode(2), FuncNode(3)
        graph = FlowGraph()
        for n in (src, b, c):
            graph.add_node(n)
        graph.connect(src.portref("out"), b.portref("in"))
        graph.connect(src.portref("out"), c.portref("in"))

        executor.execute(graph)

        assert b.contexts[0].inputs["in"] == 5
        assert c.contexts[0].inputs["in"] == 5

    def test_inputs_are_read_only(self, executor: ForwardExecutor):
        def mutate(ctx: ExecutionContext):
            ctx.inputs["in"] = 1  # type: ignore

        node = FuncNode(1, mutate)
        graph = FlowGraph()
        graph.add_node(node)

        result = executor.execute(graph)

        assert isinstance(result.nodes[0].exc, NodeExecutionError)

    def test_inout_port_seeds_input_and_output(
        self, executor: ForwardExecutor
    ):
        class InOutNode(FuncNode):
            def __init__(self):
                super().__init__(1)
                self.port_specs.append(
                    PortSpec(
                        name="io",
                        default_label="IO",
                        port_type=PrimitiveType.ANY,
                        direction=PortDirection.INOUT,
                        default="d",
                    )
                )

        node = InOutNode()
        graph = FlowGraph()
        graph.add_node(node)

        executor.execute(graph)

        assert node.contexts[0].inputs["io"] == "d"
        assert node.contexts[0].outputs["io"] == "d"


class TestValidation:
    def test_duplicate_port_names_raise(self, executor: ForwardExecutor):
        node = FuncNode(1)
        node.port_specs.append(node.port_specs[0])
        graph = FlowGraph()
        graph.add_node(node)

        with pytest.raises(InvalidNodeError) as info:
            executor.execute(graph)

        assert node.node_id in info.value.errors
        assert node.contexts == []

    def test_errors_reported_for_every_invalid_node(
        self, executor: ForwardExecutor
    ):
        bad1, bad2, good = FuncNode(1), FuncNode(2), FuncNode(3)
        bad1.port_specs.append(bad1.port_specs[0])
        bad2.port_specs.append(bad2.port_specs[1])
        graph = FlowGraph()
        for n in (bad1, bad2, good):
            graph.add_node(n)

        with pytest.raises(InvalidNodeError) as info:
            executor.execute(graph)

        assert set(info.value.errors) == {bad1.node_id, bad2.node_id}
        assert good.contexts == []

    def test_invalid_node_runs_nothing(self, executor: ForwardExecutor):
        bad, good = FuncNode(1), FuncNode(2)
        bad.port_specs.append(bad.port_specs[0])
        graph = FlowGraph()
        graph.add_node(bad)
        graph.add_node(good)

        with pytest.raises(InvalidNodeError):
            executor.execute(graph)

        assert good.contexts == []


class TestCycles:
    def test_cycle_raises(self, executor: ForwardExecutor):
        a, b = FuncNode(1), FuncNode(2)
        graph = FlowGraph()
        graph.add_node(a)
        graph.add_node(b)
        graph.connect(a.portref("out"), b.portref("in"))
        graph.connect(b.portref("out"), a.portref("in"))

        with pytest.raises(CycleError) as info:
            executor.execute(graph)

        assert set(info.value.node_ids) == {a.node_id, b.node_id}
        assert a.contexts == [] and b.contexts == []

    def test_self_loop_raises(self, executor: ForwardExecutor):
        a = FuncNode(1)
        graph = FlowGraph()
        graph.add_node(a)
        graph.connect(a.portref("out"), a.portref("in"))

        with pytest.raises(CycleError):
            executor.execute(graph)

    def test_cycle_error_includes_downstream_nodes_only_if_blocked(
        self, executor: ForwardExecutor
    ):
        free = FuncNode(1)
        a, b = FuncNode(2), FuncNode(3)
        graph = FlowGraph()
        for n in (free, a, b):
            graph.add_node(n)
        graph.connect(a.portref("out"), b.portref("in"))
        graph.connect(b.portref("out"), a.portref("in"))

        with pytest.raises(CycleError) as info:
            executor.execute(graph)

        assert free.node_id not in info.value.node_ids


class TestErrorHandling:
    def test_failing_node_is_recorded(self, executor: ForwardExecutor):
        boom = ValueError("boom")

        def fail(ctx: ExecutionContext):
            raise boom

        node = FuncNode(1, fail)
        graph = FlowGraph()
        graph.add_node(node)

        result = executor.execute(graph)

        exc = result.nodes[0].exc
        assert isinstance(exc, NodeExecutionError)
        assert exc.__cause__ is boom

    def test_successful_node_has_no_exception(
        self, executor: ForwardExecutor
    ):
        graph = make_chain(FuncNode(1))

        result = executor.execute(graph)

        assert result.nodes[0].exc is None

    def test_execution_continues_after_failure(
        self, executor: ForwardExecutor
    ):
        def fail(ctx: ExecutionContext):
            raise RuntimeError

        a, b = FuncNode(1, fail), FuncNode(2)
        graph = make_chain(a, b)

        result = executor.execute(graph)

        assert len(b.contexts) == 1
        assert result.nodes[0].exc is not None
        assert result.nodes[1].exc is None

    def test_failed_node_partial_outputs_propagate(
        self, executor: ForwardExecutor
    ):
        def set_then_fail(ctx: ExecutionContext):
            ctx.outputs["out"] = "partial"
            raise RuntimeError

        a, b = FuncNode(1, set_then_fail), FuncNode(2)
        graph = make_chain(a, b)

        executor.execute(graph)

        assert b.contexts[0].inputs["in"] == "partial"

    def test_keyboard_interrupt_propagates(self, executor: ForwardExecutor):
        def interrupt(ctx: ExecutionContext):
            raise KeyboardInterrupt

        graph = FlowGraph()
        graph.add_node(FuncNode(1, interrupt))

        with pytest.raises(KeyboardInterrupt):
            executor.execute(graph)

    def test_system_exit_propagates(self, executor: ForwardExecutor):
        def exit_(ctx: ExecutionContext):
            raise SystemExit(3)

        graph = FlowGraph()
        graph.add_node(FuncNode(1, exit_))

        with pytest.raises(SystemExit):
            executor.execute(graph)


class TestLocking:
    def test_graph_locked_during_execution(self, executor: ForwardExecutor):
        def try_mutate(ctx: ExecutionContext):
            graph.add_node(FuncNode(99))

        node = FuncNode(1, try_mutate)
        graph = FlowGraph()
        graph.add_node(node)

        result = executor.execute(graph)

        exc = result.nodes[0].exc
        assert isinstance(exc, NodeExecutionError)
        assert isinstance(exc.__cause__, GraphLockedError)
        assert not graph.contains_node_id(UUID(int=99))

    def test_graph_unlocked_after_execution(self, executor: ForwardExecutor):
        graph = make_chain(FuncNode(1))

        executor.execute(graph)

        graph.add_node(FuncNode(2))
        assert graph.contains_node_id(UUID(int=2))

    def test_graph_unlocked_after_node_failure(
        self, executor: ForwardExecutor
    ):
        def fail(ctx: ExecutionContext):
            raise RuntimeError

        graph = make_chain(FuncNode(1, fail))

        executor.execute(graph)

        graph.add_node(FuncNode(2))

    def test_graph_unlocked_after_validation_error(
        self, executor: ForwardExecutor
    ):
        bad = FuncNode(1)
        bad.port_specs.append(bad.port_specs[0])
        graph = FlowGraph()
        graph.add_node(bad)

        with pytest.raises(InvalidNodeError):
            executor.execute(graph)

        graph.add_node(FuncNode(2))

    def test_graph_unlocked_after_cycle_error(self, executor: ForwardExecutor):
        a = FuncNode(1)
        graph = FlowGraph()
        graph.add_node(a)
        graph.connect(a.portref("out"), a.portref("in"))

        with pytest.raises(CycleError):
            executor.execute(graph)

        graph.add_node(FuncNode(2))

    def test_graph_unlocked_after_keyboard_interrupt(
        self, executor: ForwardExecutor
    ):
        def interrupt(ctx: ExecutionContext):
            raise KeyboardInterrupt

        graph = make_chain(FuncNode(1, interrupt))

        with pytest.raises(KeyboardInterrupt):
            executor.execute(graph)

        graph.add_node(FuncNode(2))


class TestLogCapture:
    def test_logs_attributed_to_emitting_node(
        self, executor: ForwardExecutor
    ):
        def log(msg: str):
            def func(ctx: ExecutionContext):
                logging.getLogger("test").warning(msg)

            return func

        a, b = FuncNode(1, log("from a")), FuncNode(2, log("from b"))
        graph = make_chain(a, b)

        result = executor.execute(graph)

        assert [r.getMessage() for r in result.nodes[0].logs] == ["from a"]
        assert [r.getMessage() for r in result.nodes[1].logs] == ["from b"]

    def test_node_without_logs_has_empty_list(
        self, executor: ForwardExecutor
    ):
        graph = make_chain(FuncNode(1))

        result = executor.execute(graph)

        assert result.nodes[0].logs == []

    def test_multiple_records_are_kept_in_order(
        self, executor: ForwardExecutor
    ):
        def func(ctx: ExecutionContext):
            log = logging.getLogger("test")
            log.warning("one")
            log.error("two")

        graph = make_chain(FuncNode(1, func))

        result = executor.execute(graph)

        assert [r.getMessage() for r in result.nodes[0].logs] == ["one", "two"]
        assert [r.levelno for r in result.nodes[0].logs] == [
            logging.WARNING,
            logging.ERROR,
        ]

    def test_logs_before_failure_are_kept(self, executor: ForwardExecutor):
        def func(ctx: ExecutionContext):
            logging.getLogger("test").warning("before")
            raise RuntimeError

        graph = make_chain(FuncNode(1, func))

        result = executor.execute(graph)

        assert [r.getMessage() for r in result.nodes[0].logs] == ["before"]

    def test_handler_removed_after_execution(self, executor: ForwardExecutor):
        root = logging.getLogger()
        before = list(root.handlers)
        graph = make_chain(FuncNode(1))

        executor.execute(graph)

        assert root.handlers == before

    def test_logs_not_carried_between_runs(self, executor: ForwardExecutor):
        def func(ctx: ExecutionContext):
            logging.getLogger("test").warning("hello")

        graph = make_chain(FuncNode(1, func))

        first = executor.execute(graph)
        second = executor.execute(graph)

        assert len(first.nodes[0].logs) == 1
        assert len(second.nodes[0].logs) == 1


class TestReuse:
    def test_executor_is_reusable(self, executor: ForwardExecutor):
        node = FuncNode(1, passthrough_plus(1), in_default=1)
        graph = make_chain(node, FuncNode(2))

        r1 = executor.execute(graph)
        r2 = executor.execute(graph)

        assert [r.exec_order for r in r1.nodes] == [1, 2]
        assert [r.exec_order for r in r2.nodes] == [1, 2]

    def test_node_data_not_mutated(self, executor: ForwardExecutor):
        node = FuncNode(1, passthrough_plus(1))
        graph = FlowGraph()
        graph.add_node(node)
        data = NodeData()
        data.set(node.node_id, "in", 5)

        executor.execute(graph, data)
        executor.execute(graph, data)

        assert [c.inputs["in"] for c in node.contexts] == [5, 5]
        assert data._values == {(node.node_id, "in"): 5}
