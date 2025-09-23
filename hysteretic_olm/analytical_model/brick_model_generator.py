from typing import Optional
from geometry.geometry import *
from analytical_model.entities import *
from analytical_model.analytical_model import AnalyticalModel
from geometry.plotter import GeometryPlotter
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

class BrickModelGenerator:
    def __init__(self):
        self.concrete_shape: Optional[Shape] = None
        self.concrete_material: Optional[Material] = None
        self.concrete_thickness: float = 0.0

        # rebars -> tuple of start-end vector, area, and material for a rebar
        self.rebars: list[tuple[Vector, float, Material]] = []

        self.supports: list[tuple[Point, list[int]]] = []

        self.materials: dict[int, Material] = {}

    def set_concrete(self, shape: Shape, material: Material, thickness: float):
        """Set concrete properties for the brick model."""
        self.concrete_shape = shape
        self.concrete_material = material
        self.concrete_thickness = thickness
        
        # Store thickness in material args for shell element sections
        self.concrete_material.args['thick'] = thickness
        
        # Add thickness to material args for shell section creation
        material.args['thickness'] = thickness
        self.materials[material.tag] = material

    def add_rebar(self, position: Vector, area: float, material: Material):
        self.rebars.append((position, area, material))

        if material.tag in self.materials and self.materials[material.tag] != material:
            raise ValueError(f"Material with tag {material.tag} is already defined with different properties.")
        self.materials[material.tag] = material

    def add_support(self, point: Point, restraint: list[int]):
        """Add support constraint at point."""
        # Support 6 DOF for shell elements (x, y, z, rx, ry, rz)
        if len(restraint) not in [2, 3, 6]:
            raise ValueError(f"Restraint must have 2, 3, or 6 values for DOFs, got {len(restraint)}")
        
        self.supports.append((point, restraint))

    def reset(self):
        self.concrete_shape = None
        self.concrete_material = None
        self.concrete_thickness = 0.0
        self.rebars = []
        self.supports = []
        self.materials = {}

    def generate(self, mesh_size: float, print_model: bool = False, save_path: Optional[str] = None) -> AnalyticalModel:
        if mesh_size <= 0:
            raise ValueError("mesh_size must be positive.")

        if not self.concrete_shape or not self.concrete_material:
            raise ValueError("Concrete properties must be set before generating the model.")
        
        nodes: dict[int, Node] = self._generate_nodes(mesh_size)
        n_nodes = len(nodes)

        restraints: list[SinglePointConstraint] = []
        for support_point, support_restraint in self.supports:
            support_node = self._get_node_at(nodes, support_point)
            # Support validation moved to add_support method
            restraints.append(SinglePointConstraint(constrained_node_tag=support_node.tag, constraints=support_restraint))

        concrete_bricks: dict[int, Element] = self._generate_concrete_members(nodes, mesh_size)
        rebar_trusses: dict[int, Element] = self._generate_rebars(nodes, len(concrete_bricks) + 1)

        # Use 3D model with 3 DOF for brick elements (translational DOFs only)
        model = AnalyticalModel(n_dimension=3, n_dof=3, nodes=nodes, sp_constraints=restraints,
                                rigid_diaphragm=None, materials=self.materials,
                                elements={**concrete_bricks, **rebar_trusses})
        
        # Visualize the model if requested or if save_path is provided
        if print_model or save_path:
            self._visualize_model(nodes, concrete_bricks, rebar_trusses, restraints, mesh_size, save_path)
        return model

    def _get_node_at(self, nodes: dict[int, Node], point: Point) -> Optional[Node]:
        for node in nodes.values():
            if (abs(node.coord.x - point.x) < 1e-6 and
                abs(node.coord.y - point.y) < 1e-6 and
                abs(node.coord.z - point.z) < 1e-6):
                return node
        return None

    def _generate_nodes(self, mesh_size: float) -> dict[int, Node]:
        nodes: dict[int, Node] = {}

        # Get bounding box coordinates
        min_x, min_y, max_x, max_y = self.concrete_shape.bounding_box()

        # Calculate number of points needed in X and Y directions
        n_x = int(np.round((max_x - min_x) / mesh_size)) + 1
        n_y = int(np.round((max_y - min_y) / mesh_size)) + 1
        
        # Calculate number of layers in Z direction based on mesh size
        n_z = int(np.round(self.concrete_thickness / mesh_size)) + 1
        
        n_nodes_on_one_face = n_x * n_y

        # Use linspace for more accurate spacing
        x_coords = np.linspace(min_x, max_x, n_x)
        y_coords = np.linspace(min_y, max_y, n_y)
        z_coords = np.linspace(0.0, self.concrete_thickness, n_z)

        node_id = 1
        for z in z_coords:
            for x in x_coords:
                for y in y_coords:
                    # Create 3D point for each layer in Z direction
                    point_3d = Point(float(x), float(y), float(z))
                    if self.concrete_shape.isInside(Point(float(x), float(y))):  # Use 2D check for inside test
                        nodes[node_id] = Node(node_id, point_3d)
                        node_id += 1
        return nodes

    def _generate_concrete_members(self, nodes: dict[int, Node], mesh_size: float) -> dict[int, Element]:
        elements: dict[int, Element] = {}
        
        # Get bounding box and calculate grid dimensions
        min_x, min_y, max_x, max_y = self.concrete_shape.bounding_box()
        n_x = int(np.round((max_x - min_x) / mesh_size)) + 1
        n_y = int(np.round((max_y - min_y) / mesh_size)) + 1
        n_z = int(np.round(self.concrete_thickness / mesh_size)) + 1
        
        # Use linspace for consistent coordinate calculation
        x_coords = np.linspace(min_x, max_x, n_x)
        y_coords = np.linspace(min_y, max_y, n_y)
        z_coords = np.linspace(0.0, self.concrete_thickness, n_z)
        
        # Create a mapping from (i,j,k) indices to node IDs
        coord_to_node_id = {}
        for node_id, node in nodes.items():
            # Find the indices for this node
            for i, x in enumerate(x_coords):
                if abs(node.coord.x - x) < 1e-6:
                    for j, y in enumerate(y_coords):
                        if abs(node.coord.y - y) < 1e-6:
                            for k, z in enumerate(z_coords):
                                if abs(node.coord.z - z) < 1e-6:
                                    coord_to_node_id[(i, j, k)] = node_id
                                    break
                            break
                    break
        
        elm_id = 1
        
        # Generate brick elements between each layer
        for k in range(n_z - 1):  # Go through z layers
            for i in range(n_x - 1):  # Go through x grid indices
                for j in range(n_y - 1):  # Go through y grid indices
                    
                    # Check if element center is inside the concrete shape
                    mid_x = x_coords[i] + (x_coords[i+1] - x_coords[i]) / 2
                    mid_y = y_coords[j] + (y_coords[j+1] - y_coords[j]) / 2
                    
                    if self.concrete_shape.isInside(Point(mid_x, mid_y)):
                        # Check if all 8 corner nodes exist for this brick element
                        corner_indices = [
                            (i, j, k),         # bottom-left-front
                            (i+1, j, k),       # bottom-right-front
                            (i+1, j+1, k),     # top-right-front
                            (i, j+1, k),       # top-left-front
                            (i, j, k+1),       # bottom-left-back
                            (i+1, j, k+1),     # bottom-right-back
                            (i+1, j+1, k+1),   # top-right-back
                            (i, j+1, k+1),     # top-left-back
                        ]
                        
                        # Get node IDs for all 8 corners
                        brick_nodes = []
                        all_corners_exist = True
                        
                        for corner_idx in corner_indices:
                            if corner_idx in coord_to_node_id:
                                node_id = coord_to_node_id[corner_idx]
                                brick_nodes.append(nodes[node_id])
                            else:
                                all_corners_exist = False
                                break
                        
                        # Create brick element if all 8 nodes exist
                        if all_corners_exist and len(brick_nodes) == 8:
                            elements[elm_id] = Element(
                                tag=elm_id, 
                                element_type="stdBrick",  # Use brick elements
                                nodes=brick_nodes,  # 8 nodes in proper order
                                matTag=self.concrete_material.tag  # Material tag for brick element
                            )
                            elm_id += 1
        
        return elements

    def _generate_rebars(self, nodes: dict[int, Node], rebar_index: int) -> dict[int, Element]:
        rebars: dict[int, Element] = {}

        for pos_vec, area, material in self.rebars:
            start_pos: Point = pos_vec.start
            end_pos: Point = pos_vec.end

            start_node = self._get_node_at(nodes, start_pos)
            end_node = self._get_node_at(nodes, end_pos)

            if not start_node or not end_node:
                raise ValueError(f"Rebar {rebar_index} start or end point does not match any node.")

            rebars[rebar_index] = Element(tag=rebar_index, element_type="Truss",
                                          nodes=[start_node, end_node],
                                          A=area,
                                          matTag=material.tag
                                          )
            rebar_index += 1

        return rebars

    def _visualize_model(self, nodes: dict[int, Node], concrete_elements: dict[int, Element], 
                        rebar_elements: dict[int, Element], constraints: list[SinglePointConstraint], 
                        mesh_size: float, save_path: Optional[str] = None):
        """Visualize the analytical model showing concrete bricks, rebars, holes, and supports"""
        # Set up matplotlib for non-interactive backend
        matplotlib.use('Agg')
        
        # Create figure with subplots for different views
        fig = plt.figure(figsize=(16, 12))
        
        # Create 3 subplots: XY view, XZ view, and 3D projection
        ax_xy = fig.add_subplot(2, 2, 1)  # XY view (top view)
        ax_xz = fig.add_subplot(2, 2, 2)  # XZ view (side view)
        ax_3d = fig.add_subplot(2, 2, (3, 4), projection='3d')  # 3D view
        
        # Separate nodes by layer for better visualization
        front_nodes = []  # z = 0 (front layer)
        back_nodes = []   # z = thickness (back layer) 
        middle_nodes = [] # intermediate layers
        
        for node in nodes.values():
            if abs(node.coord.z - 0.0) < 1e-6:  # Front layer (z=0)
                front_nodes.append(node)
            elif abs(node.coord.z - self.concrete_thickness) < 1e-6:  # Back layer (z=thickness)
                back_nodes.append(node)
            else:  # Intermediate layers
                middle_nodes.append(node)
        
        # === XY VIEW (SHAPE INPUT VIEW) ===
        ax_xy.set_title('XY View (Shape Input) - Y as Height Direction')
        
        # Plot concrete shape outline
        if self.concrete_shape:
            points = self.concrete_shape.points
            if points:
                x_coords = [p.x for p in points] + [points[0].x]
                y_coords = [p.y for p in points] + [points[0].y]
                ax_xy.plot(x_coords, y_coords, 'k-', linewidth=2, label='Concrete Boundary')
                ax_xy.fill(x_coords, y_coords, color='lightgray', alpha=0.3, label='Concrete Area')
            
            # Plot holes
            if self.concrete_shape.holes:
                for i, hole in enumerate(self.concrete_shape.holes):
                    hole_points = hole.points
                    if hole_points:
                        hole_x = [p.x for p in hole_points] + [hole_points[0].x]
                        hole_y = [p.y for p in hole_points] + [hole_points[0].y]
                        ax_xy.plot(hole_x, hole_y, 'r-', linewidth=2, 
                                 label='Hole Boundary' if i == 0 else "")
                        ax_xy.fill(hole_x, hole_y, color='white', alpha=1.0, zorder=2)
        
        # Plot front face nodes
        if front_nodes:
            front_x = [node.coord.x for node in front_nodes]
            front_y = [node.coord.y for node in front_nodes]
            ax_xy.scatter(front_x, front_y, c='blue', s=20, alpha=0.6, label=f'Front Nodes ({len(front_nodes)})')
        
        # Plot brick elements (front faces only for XY view)
        brick_plotted = False
        for element in concrete_elements.values():
            if len(element.nodes) == 8:  # Brick elements
                element_nodes = element.nodes
                # Get front face nodes (first 4 nodes)
                front_face_nodes = element_nodes[:4]
                
                # Plot front face as quadrilateral
                elem_x = [node.coord.x for node in front_face_nodes] + [front_face_nodes[0].coord.x]
                elem_y = [node.coord.y for node in front_face_nodes] + [front_face_nodes[0].coord.y]
                ax_xy.plot(elem_x, elem_y, 'g-', linewidth=1.0, alpha=0.8, 
                          label='Brick Elements' if not brick_plotted else "")
                brick_plotted = True
        
        # Plot rebars in XY view
        rebar_plotted_xy = False
        for element in rebar_elements.values():
            if len(element.nodes) == 2:
                element_nodes = element.nodes
                elem_x = [element_nodes[0].coord.x, element_nodes[1].coord.x]
                elem_y = [element_nodes[0].coord.y, element_nodes[1].coord.y]
                ax_xy.plot(elem_x, elem_y, 'r-', linewidth=3, 
                          label='Rebar' if not rebar_plotted_xy else "")
                rebar_plotted_xy = True
        
        # Plot supports in XY view
        support_nodes_xy = []
        for constraint in constraints:
            for node in nodes.values():
                if node.tag == constraint.constrained_node_tag:
                    support_nodes_xy.append(node)
                    break
        
        if support_nodes_xy:
            support_x = [node.coord.x for node in support_nodes_xy]
            support_y = [node.coord.y for node in support_nodes_xy]
            ax_xy.scatter(support_x, support_y, c='red', s=100, marker='^', 
                         label=f'Supports ({len(support_nodes_xy)})', zorder=5)
        
        ax_xy.set_xlabel('X (m)')
        ax_xy.set_ylabel('Y (m)')
        ax_xy.grid(True, alpha=0.3)
        ax_xy.legend()
        ax_xy.set_aspect('equal')
        
        # === XZ VIEW (SIDE VIEW) ===
        ax_xz.set_title('XZ View (Side View)')
        
        # Plot all nodes in XZ view  
        all_x = [node.coord.x for node in nodes.values()]
        all_z = [node.coord.z for node in nodes.values()]
        ax_xz.scatter(all_x, all_z, c='blue', s=20, alpha=0.6, label=f'All Nodes ({len(nodes)})')
        
        # Draw lines connecting front and back faces for each brick
        brick_plotted_xz = False
        for element in concrete_elements.values():
            if len(element.nodes) == 8:  # Brick elements
                element_nodes = element.nodes
                # Connect corresponding front and back nodes
                for i in range(4):  # 4 node pairs
                    front_node = element_nodes[i]
                    back_node = element_nodes[i + 4]
                    
                    line_x = [front_node.coord.x, back_node.coord.x]
                    line_z = [front_node.coord.z, back_node.coord.z]
                    ax_xz.plot(line_x, line_z, 'g-', linewidth=1.0, alpha=0.7,
                              label='Brick Depth' if not brick_plotted_xz else "")
                    brick_plotted_xz = True
        
        # Plot rebars in XZ view
        rebar_plotted_xz = False
        for element in rebar_elements.values():
            if len(element.nodes) == 2:
                element_nodes = element.nodes
                elem_x = [element_nodes[0].coord.x, element_nodes[1].coord.x]
                elem_z = [element_nodes[0].coord.z, element_nodes[1].coord.z]
                ax_xz.plot(elem_x, elem_z, 'r-', linewidth=3,
                          label='Rebar' if not rebar_plotted_xz else "")
                rebar_plotted_xz = True
        
        # Plot supports in XZ view
        if support_nodes_xy:
            support_x = [node.coord.x for node in support_nodes_xy]
            support_z = [node.coord.z for node in support_nodes_xy]
            ax_xz.scatter(support_x, support_z, c='red', s=100, marker='^', 
                         label=f'Supports', zorder=5)
        
        ax_xz.set_xlabel('X (m)')
        ax_xz.set_ylabel('Z (m)')
        ax_xz.grid(True, alpha=0.3)
        ax_xz.legend()
        ax_xz.set_aspect('equal')
        
        # === 3D VIEW ===
        ax_3d.set_title('3D View - Brick Elements')
        
        # Plot all nodes in 3D
        all_x = [node.coord.x for node in nodes.values()]
        all_y = [node.coord.y for node in nodes.values()]
        all_z = [node.coord.z for node in nodes.values()]
        ax_3d.scatter(all_x, all_y, all_z, c='blue', s=10, alpha=0.4, label=f'Nodes ({len(nodes)})')
        
        # Plot each brick element as a wireframe
        for element in concrete_elements.values():
            if len(element.nodes) == 8:  # Brick elements
                element_nodes = element.nodes
                
                # Extract coordinates for all 8 nodes
                brick_x = [node.coord.x for node in element_nodes]
                brick_y = [node.coord.y for node in element_nodes]
                brick_z = [node.coord.z for node in element_nodes]
                
                # Draw front face (nodes 0,1,2,3)
                front_face_x = [brick_x[i] for i in [0,1,2,3,0]]  # Close the loop
                front_face_y = [brick_y[i] for i in [0,1,2,3,0]]
                front_face_z = [brick_z[i] for i in [0,1,2,3,0]]
                ax_3d.plot(front_face_x, front_face_y, front_face_z, 'g-', linewidth=1.0, alpha=0.8)
                
                # Draw back face (nodes 4,5,6,7)
                back_face_x = [brick_x[i] for i in [4,5,6,7,4]]  # Close the loop
                back_face_y = [brick_y[i] for i in [4,5,6,7,4]]
                back_face_z = [brick_z[i] for i in [4,5,6,7,4]]
                ax_3d.plot(back_face_x, back_face_y, back_face_z, 'g-', linewidth=1.0, alpha=0.8)
                
                # Draw connecting edges between front and back faces
                for i in range(4):
                    edge_x = [brick_x[i], brick_x[i+4]]
                    edge_y = [brick_y[i], brick_y[i+4]]
                    edge_z = [brick_z[i], brick_z[i+4]]
                    ax_3d.plot(edge_x, edge_y, edge_z, 'g-', linewidth=1.0, alpha=0.6)
        
        # Plot rebars in 3D
        for element in rebar_elements.values():
            if len(element.nodes) == 2:
                element_nodes = element.nodes
                elem_x = [element_nodes[0].coord.x, element_nodes[1].coord.x]
                elem_y = [element_nodes[0].coord.y, element_nodes[1].coord.y]
                elem_z = [element_nodes[0].coord.z, element_nodes[1].coord.z]
                ax_3d.plot(elem_x, elem_y, elem_z, 'r-', linewidth=4)
        
        # Plot supports in 3D
        if support_nodes_xy:
            support_x = [node.coord.x for node in support_nodes_xy]
            support_y = [node.coord.y for node in support_nodes_xy]
            support_z = [node.coord.z for node in support_nodes_xy]
            ax_3d.scatter(support_x, support_y, support_z, c='red', s=100, marker='^', 
                         label=f'Supports', zorder=5)
        
        ax_3d.set_xlabel('X (m)')
        ax_3d.set_ylabel('Y (m)')
        ax_3d.set_zlabel('Z (m)')
        ax_3d.legend()
        
        # Set viewing angle for 3D isometric view:
        # Y-axis pointing upward (vertical), X-axis to the right, Z-axis toward viewer (depth)
        # elev=30 gives a good upward viewing angle to see the 3D structure
        # azim=-45 rotates the view for optimal isometric perspective
        ax_3d.view_init(elev=30, azim=-45)
        
        # Alternative angles for fine-tuning:
        # ax_3d.view_init(elev=25, azim=-60)  # Different angle
        # ax_3d.view_init(elev=35, azim=-30)  # Steeper viewing angle
        # ax_3d.view_init(elev=20, azim=-45)  # Lower viewing angle
        
        # Set equal aspect ratio for 3D plot
        if len(all_x) > 0 and len(all_y) > 0:
            max_x, min_x = max(all_x), min(all_x)
            max_y, min_y = max(all_y), min(all_y)
            max_range = max(max_x - min_x, max_y - min_y, self.concrete_thickness) / 2.0
            mid_x = (max_x + min_x) / 2.0
            mid_y = (max_y + min_y) / 2.0
        else:
            max_range = self.concrete_thickness / 2.0
            mid_x, mid_y = 0, 0
        
        mid_z = self.concrete_thickness / 2.0
        
        ax_3d.set_xlim(mid_x - max_range, mid_x + max_range)
        ax_3d.set_ylim(mid_y - max_range, mid_y + max_range)
        ax_3d.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Overall figure formatting
        total_elements = len(concrete_elements) + len(rebar_elements)
        fig.suptitle(f'Brick Model Visualization\n'
                    f'Nodes: {len(nodes)}, Brick Elements: {len(concrete_elements)}, '
                    f'Rebar Elements: {len(rebar_elements)}, Supports: {len(constraints)}, Mesh: {mesh_size}m',
                    fontsize=14)
        
        plt.tight_layout()
        
        # Save the plot
        import os
        
        if save_path:
            filename = save_path
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        else:
            output_dir = "outputs"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            filename = f"{output_dir}/brick_model_visualization.png"
        
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Brick model visualization saved to: {filename}")
        print(f"   - Total nodes: {len(nodes)} (Front: {len(front_nodes)}, Back: {len(back_nodes)}, Middle: {len(middle_nodes)})")
        print(f"   - Brick elements: {len(concrete_elements)}")
        print(f"   - Rebar elements: {len(rebar_elements)}")
        print(f"   - Support nodes: {len(constraints)}")
        print(f"   - Concrete thickness: {self.concrete_thickness}m")
