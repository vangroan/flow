"""
Ports that connect nodes. They serve as the edges of the directional graph.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from enum import Enum

from flow_core.errors import InvalidKeyError

_PORT_KEY_PATTERN = re.compile(r"[a-zA-Z0-9_\.]+")


@enum.unique
class PrimitiveType(Enum):
    NONE = 0
    INT = 1
    FLOAT = 2
    STRING = 3
    BOOL = 4


@dataclass(frozen=True, slots=True)
class ListType:
    item: PrimitiveType


@dataclass(frozen=True, slots=True)
class ObjectType:
    ty: type


type PortType = PrimitiveType | ListType | ObjectType


class PortDirection(Enum):
    """
    Direction of the port.
    """
    INPUT = 0
    OUTPUT = 1
    INOUT = 2


@dataclass(frozen=True, slots=True)
class PortSpec:
    """
    Specification of a port.
    
    A specification defines the type and options shared between all instances
    referencing this port.
    """
    # This is the flyweight pattern for node ports. It ensures that common port
    # specifications are shared across instances.
    
    port_key: str
    """
    The unique key identifying this port specification.
    """

    default_label: str
    port_type: PortType
    direction: PortDirection

    def __post_init__(self) -> None:
        self.validate_key(self.port_key)

    @staticmethod
    def validate_key(key: str) -> None:
        if not _PORT_KEY_PATTERN.fullmatch(key):
            raise InvalidKeyError(f"Invalid port key: {key}")



@dataclass(frozen=True, slots=True)
class PortRef:
    """
    Reference to a port.
    
    A reference points to a specific instance of a port defined by a PortSpec.
    """

    spec: PortSpec
    """
    The specification this reference points to.
    """

    label: str | None = None
    """
    The label of the port instance. If None, the default label from the spec is used.
    """


@dataclass(frozen=True, slots=True)
class Connection:
    """
    Represents a connection between two ports.
    """

    from_port: PortRef
    to_port: PortRef