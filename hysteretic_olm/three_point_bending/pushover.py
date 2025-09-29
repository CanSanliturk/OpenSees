import opensees as ops
import numpy as np

#       Y
#       |
#       |
#       |____ X
#      /
#     /
#   Z

# Geometry parameters
dim_x: float = 5.0  # m, in X direction
dim_y: float = 0.5  # m in Y direction
dim_z: float = 0.5  # m in Z direction

# Material properties
E: float = 30e9 # Pa

# Concrete material
mat_tag: int = 1
rho: float = 2500         # kg/m^3
fc: float = -30e6         # compressive strength (negative) in Pa
e0: float = -0.002        # strain at peak compressive strength
n: float = 2.0            # compressive envelope shape factor
k: float = 0.67           # post-peak compressive shape factor
alpha1: float = 0.4       # parameter for compressive plastic strain evolution
fcr: float = 2.5e6        # tensile (cracking) strength in Pa
ecr: float = 0.00008      # tensile strain at cracking stress
b: float = 1.2            # exponent in tension stiffening softening
alpha2: float = 0.3       # parameter for tensile plastic strain evolution

# Tensile reinforcement
is_tensile_reinf: bool = True
tensile_rebar_count: int = 4
clear_cover: float = 0.1 # m
tensile_rebar_dia: float = 0.012 # m
tensile_rebar_area: float = np.pi * (tensile_rebar_dia / 2) ** 2 # m^2

# Tensile steel material
tensile_steel_mat_tag: int = 2            # unique material tag
fy: float = 420e6           # yield stress (Pa)
e0: float = 200e9           # initial elastic modulus (Pa)
b: float = 0.01             # strain-hardening ratio (Esh/E0)
R0: float = 18.0            # controls transition from elastic to plastic
cR1: float = 0.925          # controls transition from elastic to plastic
cR2: float = 0.15           # controls transition from elastic to plastic
params: list[float] = [R0, cR1, cR2]

# Misc
mesh_size: float = 0.1 # m
tolerance: float = 1e-6
horizon: float = mesh_size * np.sqrt(3) * 1.01 # m
lattice_area: float = 27.5625 * 1e-4 # m^2

# Create model
ops.wipe()
ops.model("basic", "-ndm", 3, "-ndf", 3)

ops.uniaxialMaterial('Concrete06', mat_tag, fc, e0, n, k, 
    alpha1, fcr, ecr, b, alpha2)

ops.uniaxialMaterial('Steel02', tensile_steel_mat_tag, 
    fy, e0, b, *params)

# Node calculations
n_node_x: int = int(dim_x / mesh_size) + 1
n_node_y: int = int(dim_y / mesh_size) + 1
n_node_z: int = int(dim_z / mesh_size) + 1
n_node_in_xy_plane: int = n_node_x * n_node_y

node_indexer: int = 0
node_to_coord: dict[int, tuple[float, float, float]] = {}
volume: float = dim_x * dim_y * dim_z
mass: float = volume * rho
n_nodes: int = n_node_x * n_node_y * n_node_z
mass_per_node: float = mass / n_nodes

def are_equal(a: float, b: float) -> bool:
    """
    Check if two floating point numbers are equal within a specified tolerance.
    """
    return abs(a - b) < tolerance

def make_coord_key(x: float, y: float, z: float, tolerance: float) -> str:
    """
    Quantize 3D coordinates to an integer grid and return a string key.

    Args:
        x (float): X coordinate.
        y (float): Y coordinate.
        z (float): Z coordinate.
        tolerance (float): Grid size (tolerance). Smaller = finer grid.

    Returns:
        str: String key like "123_-456_789".
    """
    qx: int = int(round(x / tolerance))
    qy: int = int(round(y / tolerance))
    qz: int = int(round(z / tolerance))
    return f"{qx}_{qy}_{qz}"

# Create nodes
coord_to_node: dict[str, int] = {}
for z in range(n_node_z):
    for y in range(n_node_y):
        for x in range(n_node_x):
            node_indexer += 1
            node_to_coord[node_indexer] = (x * mesh_size, y * mesh_size, z * mesh_size)
            dx, dy, dz = node_to_coord[node_indexer]
            ops.node(node_indexer, dx, dy, dz)
            ops.mass(node_indexer, mass_per_node, mass_per_node, mass_per_node)
            coord_key: str = make_coord_key(dx, dy, dz, tolerance)
            coord_to_node[coord_key] = node_indexer
            if are_equal(dx, 0):
                ops.fix(node_indexer, 1, 1, 1)
            elif are_equal(dx, dim_x):
                ops.fix(node_indexer, 0, 1, 1)

print(
    f"Created {node_indexer} nodes, in x direction: {n_node_x}, "
    f"y direction: {n_node_y}, z direction: {n_node_z}"
)

# Create concrete trusses
element_indexer: int = 0
connectivity: set[str] = set()
for node_1 in range(1, node_indexer):  # Fixed range to include last node
    for node_2 in range(node_1 + 1, node_indexer + 1):  # Only check nodes after current node to avoid duplicates
        conn_hash: str = f'{node_1}-{node_2}'
        node_1_x, node_1_y, node_1_z = node_to_coord[node_1]
        node_2_x, node_2_y, node_2_z = node_to_coord[node_2]
        dist: float = np.sqrt(
            (node_1_x - node_2_x) ** 2 + 
            (node_1_y - node_2_y) ** 2 + 
            (node_1_z - node_2_z) ** 2
            )
        if dist < horizon:
            element_indexer += 1
            connectivity.add(conn_hash)
            ops.element('Truss', element_indexer, node_1, node_2, lattice_area, mat_tag)
print(f"Created {element_indexer} concrete truss elements")

# Create tensile reinforcement trusses
tensile_steel_y_pos: float = clear_cover
tensile_steel_z_pos: list[float] = np.linspace(
    start=clear_cover,
    stop=dim_z - clear_cover,
    num=tensile_rebar_count
)

tensile_steel_x_pos: list[float] = np.arange(
    start=clear_cover,
    stop=dim_x - clear_cover - mesh_size, # only create beginning of an element
    step=mesh_size
)

concrete_element_count: int = element_indexer
for z_pos in tensile_steel_z_pos:
    for x_pos in tensile_steel_x_pos:
        node_1_key: str = make_coord_key(x_pos, tensile_steel_y_pos, z_pos, tolerance)
        node_2_key: str = make_coord_key(x_pos + mesh_size, tensile_steel_y_pos, z_pos, tolerance)
        if node_1_key in coord_to_node and node_2_key in coord_to_node:
            element_indexer += 1
            node_1: int = coord_to_node[node_1_key]
            node_2: int = coord_to_node[node_2_key]
            ops.element('Truss', element_indexer, node_1, node_2, tensile_rebar_area, tensile_steel_mat_tag)
        else:
            raise ValueError(f"Node keys {node_1_key} or {node_2_key} not found in coord_to_node mapping.")
print(f"Created {element_indexer - concrete_element_count} tensile reinforcement truss elements")

# Solve for eigenvalues
# n_modes: int = 10
# eigenvalues = ops.eigen(n_modes)

# ops.modalProperties("-print")
