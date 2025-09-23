from abc import ABC
from dataclasses import dataclass
from typing import Any

from geometry.geometry import Point, Vector

@dataclass
class Model:
    n_dimension: int

    def __post_init__(self):
        if self.n_dimension not in [1, 2, 3]:
            raise ValueError(f"n_dimension must be 1, 2, or 3, got {self.n_dimension}")

@dataclass
class TaggedEntityBase(ABC):
    tag: int
    args: dict[str, Any]

class Node(TaggedEntityBase):
    def __init__(self, tag: int, coord: Point):
        self.coord = coord
        super().__init__(tag, {"crds": [coord.x, coord.y, coord.z]})

@dataclass
class SinglePointConstraint:
    constrained_node_tag: int
    constraints: list[int]

@dataclass
class RigidDiaphragm:
    perpendicular_dir: Vector
    primary_node_tag: int
    secondary_nodes_tags: list[int]

class Element(TaggedEntityBase):
    def __init__(self, tag: int, element_type: str, nodes: list[Node], **kwargs):
        self.element_type: str = element_type
        self.nodes: list[Node] = nodes
        params = {
            "eleType": element_type,
            "nodes": [node.tag for node in nodes],
            **kwargs
        }
        super().__init__(tag, params)

class Material(TaggedEntityBase):
    def __init__(self, tag: int, material_type: str, **kwargs):
        self.material_type: str = material_type
        params = {
            "material_type": material_type,
            **kwargs
        }
        super().__init__(tag, params)
