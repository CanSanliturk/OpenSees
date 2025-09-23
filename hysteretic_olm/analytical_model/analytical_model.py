from typing import Optional
from .entities import *

@dataclass
class AnalyticalModel:
    n_dimension: int
    n_dof: int
    nodes: dict[int, Node]
    sp_constraints: list[SinglePointConstraint]
    rigid_diaphragm: Optional[RigidDiaphragm]
    materials: dict[int, Material]
    elements: dict[int, Element]
