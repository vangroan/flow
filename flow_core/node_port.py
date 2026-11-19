"""
Ports that connect nodes. They serve as the edges of the directional graph.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@enum.unique
class PrimitiveType(enum.Enum):
    ANY = 0
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


@enum.unique
class PortDirection(enum.Enum):
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
    name: str
    default_label: str
    port_type: PortType
    direction: PortDirection
    default: Any = None
    """Default value assigned to the execution context."""


@dataclass(frozen=True, slots=True, eq=True)
class PortRef:
    """
    Reference to a port.
    
    A reference points to a specific instance of a port defined by a PortSpec.
    """

    node_id: UUID

    spec: PortSpec
    """
    The specification this reference points to.
    """


@dataclass(frozen=True, slots=True, eq=True)
class Connection:
    """
    Represents a connection between two ports.
    """

    from_port: PortRef
    to_port: PortRef
