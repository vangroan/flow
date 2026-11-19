import jsonschema
import yaml
from jsonschema import Draft202012Validator

TYPE_QUALIFIED_NAME_SCHEMA = {
    "type": "string",
    "description": "Fully qualified name of the Python class.",
}


PORT_DIRECTION_SCHEMA = {"type": "number", "enum": [0, 1, 2]}


PORT_SPEC_SCHEMA = {
    "type": "object",
    "rerquired": ["name", "direction"],
    "properties": {
        "name": {
            "type": "string",
        },
        "direction": PORT_DIRECTION_SCHEMA,
    },
}

NODE_SCHEMA = {
    "type": "object",
    "required": ["node_id", "pytype"],
    "properties": {
        "node_id": {
            "type": "string",
            "format": "uuid",
        },
        "title": {
            "type": "string",
        },
        "pytype": TYPE_QUALIFIED_NAME_SCHEMA,
        "port_specs": {
            "type": "array",
            "items": PORT_SPEC_SCHEMA,
        },
    },
}


FLOW_GRAPH_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://flow.vangroan.com",
    "title": "Flow Graph",
    "description": "Graph of executable nodes.",
    "type": "object",
    "additionalProperties": False,
    "required": ["nodes"],
    "properties": {
        "nodes": {
            "type": "array",
            "items": NODE_SCHEMA,
        },
        "connections": {},
    },
}


def validate(data: dict):
    jsonschema.validate(
        data,
        FLOW_GRAPH_SCHEMA,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


if __name__ == "__main__":
    with open("flow_serde/example.yaml", "r") as fp:
        data = yaml.safe_load(fp.read())
        validate(data)
