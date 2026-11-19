import yaml
from pathlib import Path

from flow_core.graph import FlowGraph
from flow_core.node import Node

from flow_serde.schema import validate
from flow_serde.reflection import find_type

type PathLike = str | Path


def deserialise(data: dict) -> FlowGraph:
    validate(data)

    graph = FlowGraph()
    
    for node_data in data["nodes"]:
        qualname = node_data["pytype"]
        node_class = find_type(qualname)
        # FIXME: Figure out how to call the constructor.
        node = node_class()


def load_file(path: PathLike) -> FlowGraph:
    if isinstance(path, str):
        path = Path(path)

    with path.open("r") as fp:
        data = yaml.safe_load(fp)
        return deserialise(data)
