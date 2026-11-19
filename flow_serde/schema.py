import jsonschema
import yaml
from jsonschema import Draft202012Validator


NODE_ID_SCHEMA = {
    "type": "string",
    "format": "uuid",
}

PORT_REF = {
    "type": "object",
    "required": ["node_id", "port_name"],
    "properties": {
        "node_id": NODE_ID_SCHEMA,
        "port_name": {"type": "string"},
    },
}

TYPE_QUALIFIED_NAME_SCHEMA = {
    "type": "string",
    "description": "Fully qualified name of the Python class.",
}

PORT_DIRECTION_SCHEMA = {"type": "number", "enum": [0, 1, 2]}

PORT_SPEC_SCHEMA = {
    "type": "object",
    "required": ["name", "direction"],
    "properties": {

    },
}

NODE_SCHEMA = {
    "type": "object",
    "required": ["node_id", "pytype"],
    "properties": {
        "node_id": NODE_ID_SCHEMA,
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

CONNECTION_SCHEMA = {
    "type": "object",
    "required": ["from_port", "to_port"],
    "properties": {
        "from_port": PORT_REF,
        "to_port": PORT_REF,
    },
}


FLOW_GRAPH_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://flow.vangroan.com",
    "title": "Flow Graph",
    "description": "Graph of executable nodes.",
    "type": "object",
    "additionalProperties": False,
    "required": ["nodes", "connections"],
    "properties": {
        "nodes": {
            "type": "array",
            "items": NODE_SCHEMA,
        },
        "connections": {
            "type": "array",
            "items": CONNECTION_SCHEMA,
        },
    },
}


def validate(data: dict):
    jsonschema.validate(
        data,
        FLOW_GRAPH_SCHEMA,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
