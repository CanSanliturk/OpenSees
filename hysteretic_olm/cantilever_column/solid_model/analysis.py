import opensees as ops

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
nu: float = 0.3 # Poisson's ratio
is_lumped_mass: bool = False

# Misc
mesh_size: float = 0.1 # m
tolerance: float = 1e-6

# Create model
ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 3)

# Create material
mat_tag: int = 1
ops.nDMaterial('ElasticIsotropic', mat_tag, E, nu, 0 if is_lumped_mass else rho)

# Node calculations
n_node_x: int = int(depth / mesh_size) + 1
n_node_y: int = int(width / mesh_size) + 1
n_node_z: int = int(height / mesh_size) + 1

n_elem_x: int = n_node_x - 1
n_elem_y: int = n_node_y - 1
n_elem_z: int = n_node_z - 1

n_node_in_xy_plane: int = n_node_x * n_node_y

node_indexer: int = 0
node_to_coord: dict[int, tuple[float, float, float]] = {}
# Create nodes
for z in range(n_node_z):
    for y in range(n_node_y):
        for x in range(n_node_x):
            node_indexer += 1
            node_to_coord[node_indexer] = (x * mesh_size, y * mesh_size, z * mesh_size)
            ops.node(node_indexer, x * mesh_size, y * mesh_size, z * mesh_size)
print(f'Created {node_indexer} nodes, in x direction: {n_node_x}, y direction: {n_node_y}, z direction: {n_node_z}')

# Fix base nodes
def are_equal(a: float, b: float) -> bool:
    return abs(a - b) < tolerance

for node, coords in node_to_coord.items():
    x, y, z = coords
    if are_equal(z, 0.0):
        ops.fix(node, 1, 1, 1)

# Create std brick elements
elem_indexer: int = 0

def validate_node_2(node_1: int, node_2: int) -> bool:
    '''
    node2 should have the same y and z coordinates as node1, but x coordinate should be 1 mesh_size away
    '''
    if node_2 not in node_to_coord:
        return False
    node_1_x, node_1_y, node_1_z = node_to_coord[node_1]
    node_2_x, node_2_y, node_2_z = node_to_coord[node_2]
    return are_equal(node_1_y, node_2_y) and are_equal(node_1_z, node_2_z) and are_equal(node_1_x + mesh_size, node_2_x)

def validate_node_3(node_2: int, node_3: int) -> bool:
    '''
    node3 should have the same x and z coordinates as node2, but y coordinate should be 1 mesh_size away
    '''
    if node_3 not in node_to_coord:
        return False
    node_2_x, node_2_y, node_2_z = node_to_coord[node_2]
    node_3_x, node_3_y, node_3_z = node_to_coord[node_3]
    return are_equal(node_2_x, node_3_x) and are_equal(node_2_z, node_3_z) and are_equal(node_2_y + mesh_size, node_3_y)

def validate_node_4(node_3: int, node_4: int) -> bool:
    '''
    node4 should have the same y and z coordinates as node3, but x coordinate should be 1 mesh_size smaller
    '''
    if node_4 not in node_to_coord:
        return False
    node_3_x, node_3_y, node_3_z = node_to_coord[node_3]
    node_4_x, node_4_y, node_4_z = node_to_coord[node_4]
    return are_equal(node_3_y, node_4_y) and are_equal(node_3_z, node_4_z) and are_equal(node_3_x - mesh_size, node_4_x)

elem_to_nodes: dict[int, tuple[int, int, int, int, int, int, int, int]] = {}
for node in range(1, node_indexer):
    bottom_node_1: int = node
    bottom_node_2: int = bottom_node_1 + 1
    bottom_node_3: int = bottom_node_2 + n_node_x
    bottom_node_4: int = bottom_node_3 - 1
    if validate_node_2(bottom_node_1, bottom_node_2) and validate_node_3(bottom_node_2, bottom_node_3) and validate_node_4(bottom_node_3, bottom_node_4):
        top_node_1: int = bottom_node_1 + n_node_in_xy_plane
        top_node_2: int = bottom_node_2 + n_node_in_xy_plane
        top_node_3: int = bottom_node_3 + n_node_in_xy_plane
        top_node_4: int = bottom_node_4 + n_node_in_xy_plane
        if validate_node_2(top_node_1, top_node_2) and validate_node_3(top_node_2, top_node_3) and validate_node_4(top_node_3, top_node_4):
            elem_indexer += 1
            elem_to_nodes[elem_indexer] = (bottom_node_1, bottom_node_2, bottom_node_3, bottom_node_4,
                                           top_node_1, top_node_2, top_node_3, top_node_4)
            ops.element('stdBrick', elem_indexer, bottom_node_1, bottom_node_2, bottom_node_3, bottom_node_4,
                        top_node_1, top_node_2, top_node_3, top_node_4, mat_tag)
print(f'Created {elem_indexer} elements, in x direction: {n_elem_x}, y direction: {n_elem_y}, z direction: {n_elem_z}')

# Solve for eigenvalues
n_modes: int = 10
eigenvalues: list[float] = ops.eigen(n_modes)
ops.modalProperties("-print")
