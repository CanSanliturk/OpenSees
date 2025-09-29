import opensees as ops
import numpy as np

#       Z
#       |
#       |
#       |____ Y
#      /
#     /
#   X

# Geometry parameters
height: float = 3.0 # m, in Z direction
width: float = 0.5 # m in Y direction
depth: float = 0.5 # m in X direction

# Material properties
E: float = 30e9 # Pa
rho: float = 2500 # kg/m^3

# Misc
mesh_size: float = 0.1 # m
tolerance: float = 1e-6
horizon: float = mesh_size * np.sqrt(3) * 1.01 # m
lattice_area: float = 30 * 1e-4 # m^2

# Create model
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 3)

# Create material
mat_tag: int = 1
ops.uniaxialMaterial('Elastic', mat_tag, E)

# Node calculations
n_node_x: int = int(depth / mesh_size) + 1
n_node_y: int = int(width / mesh_size) + 1
n_node_z: int = int(height / mesh_size) + 1
n_node_in_xy_plane: int = n_node_x * n_node_y

# Calculate mass to distribute to each node
volume: float = height * width * depth
mass: float = volume * rho
n_nodes: int = n_node_x * n_node_y * n_node_z - n_node_in_xy_plane # Exclude base nodes
mass_per_node: float = mass / n_nodes

node_indexer: int = 0
node_to_coord: dict[int, tuple[float, float, float]] = {}
# Create nodes
for z in range(n_node_z):
    for y in range(n_node_y):
        for x in range(n_node_x):
            node_indexer += 1
            node_to_coord[node_indexer] = (x * mesh_size, y * mesh_size, z * mesh_size)
            ops.node(node_indexer, x * mesh_size, y * mesh_size, z * mesh_size)
            if z > 0: # Exclude base nodes
                ops.mass(node_indexer, mass_per_node, mass_per_node, mass_per_node)

print(f'Created {node_indexer} nodes, in x direction: {n_node_x}, y direction: {n_node_y}, z direction: {n_node_z}')

# Fix base nodes
def are_equal(a: float, b: float) -> bool:
    return abs(a - b) < tolerance

for node, coords in node_to_coord.items():
    x, y, z = coords
    if are_equal(z, 0.0):
        ops.fix(node, 1, 1, 1)

# Create lattice elements
connectivity: set[str] = set()

element_indexer: int = 0
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

print(f'Created {element_indexer} elements')

# Solve for eigenvalues
n_modes: int = 10
eigenvalues: list[float] = ops.eigen(n_modes)
ops.modalProperties("-print")
