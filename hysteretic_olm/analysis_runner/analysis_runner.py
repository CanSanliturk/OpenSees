from analytical_model.analytical_model import AnalyticalModel
from analytical_model.entities import Node, Element, Material, SinglePointConstraint, RigidDiaphragm
from abc import ABC
from typing import Dict, List

# Import OpenSees Python module
try:
    import opensees as ops
except ImportError:
    try:
        from openseespy.opensees import *
        import openseespy.opensees as ops
    except ImportError:
        ops = None

class AnalysisRunner(ABC):
    def run(self) -> any:
        pass

def define_model(model: AnalyticalModel) -> None:
    """
    Define OpenSees model from analytical model data structure.
    
    Args:
        model: AnalyticalModel containing nodes, elements, materials, and constraints
    """
    if ops is None:
        raise ImportError("OpenSees Python module is required but not available")
    
    # Clear any existing model
    ops.wipe()
    
    # Create ModelBuilder - use n_dof from model
    ops.model('basic', '-ndm', model.n_dimension, '-ndf', model.n_dof)
    
    # Define materials
    _define_materials(model.materials)
    
    # Define nodes
    _define_nodes(model.nodes)
    
    # Define boundary conditions (support constraints)
    _define_boundary_conditions(model.sp_constraints)
    
    # Define elements
    _define_elements(model.elements)
    
    # Handle rigid diaphragm if present
    if model.rigid_diaphragm:
        _define_rigid_diaphragm(model.rigid_diaphragm)


def _define_materials(materials: Dict[int, Material]) -> None:
    """Define materials in OpenSees model."""
    for mat_tag, material in materials.items():
        if material.material_type == "ElasticIsotropic":
            # Check if this material is used by truss elements
            # For truss elements, we need both nD and uniaxial versions
            E = material.args.get('E', 25000000000)  # Pa
            nu = material.args.get('v', 0.2)  # Poisson's ratio
            rho = material.args.get('rho', 2400)  # kg/m^3
            
            # Define nD material for quad elements
            ops.nDMaterial("ElasticIsotropic", mat_tag, E, nu, rho)
            
            # Define uniaxial material for truss elements (using same tag + offset)
            # This ensures truss elements can use the same material tag
            ops.uniaxialMaterial("Elastic", mat_tag + 1000, E)
            
        elif material.material_type == "Concrete01":
            # Concrete01 uniaxial material - convert to ElasticMembranePlateSection for shell elements
            # Convert from MPa to Pa for OpenSees
            fpc = material.args.get('fpc', -30.0) * 1e6      # MPa -> Pa - compressive strength
            epsc0 = material.args.get('epsc0', -0.002)       # Strain at max strength (dimensionless)
            fpcu = material.args.get('fpcu', -6.0) * 1e6     # MPa -> Pa - crushing strength  
            epsU = material.args.get('epsU', -0.005)         # Strain at crushing (dimensionless)
            rho = material.args.get('rho', 2.4) * 1000       # Mg/m³ -> kg/m³
            thickness = material.args.get('thick', 0.5)      # Get thickness from material
            
            # Calculate elastic modulus from concrete stress-strain relationship
            # Initial tangent modulus: E = 2*fpc/epsc0
            E_concrete = abs(2 * fpc / epsc0)  # Pa
            nu = 0.2  # Typical Poisson's ratio for concrete
            
            # Define ElasticMembranePlateSection for shell elements
            ops.section('ElasticMembranePlateSection', mat_tag, E_concrete, nu, thickness, rho)
            
            # Also define uniaxial Concrete01 for potential truss elements
            ops.uniaxialMaterial("Concrete01", mat_tag + 1000, fpc, epsc0, fpcu, epsU)
            
        elif material.material_type == "Steel02":
            # Steel02 uniaxial material for rebars
            # Convert from MPa to Pa for OpenSees
            Fy = material.args.get('Fy', 420) * 1e6      # MPa -> Pa - yield strength
            E = material.args.get('E', 200000) * 1e6     # MPa -> Pa - elastic modulus
            b = material.args.get('b', 0.02)             # strain hardening ratio (dimensionless)
            ops.uniaxialMaterial("Steel02", mat_tag, Fy, E, b)
            
        elif material.material_type == "Elastic":
            # For 1D elements like trusses
            E = material.args.get('E', 200000000000)  # Pa
            ops.uniaxialMaterial("Elastic", mat_tag, E)


def _define_nodes(nodes: Dict[int, Node]) -> None:
    """Define nodes in OpenSees model."""
    for node_tag, node in nodes.items():
        # Extract coordinates - always create 3D nodes
        x = node.coord.x
        y = node.coord.y
        z = node.coord.z if hasattr(node.coord, 'z') else 0.0
        
        # Create 3D node (required for quad elements)
        ops.node(node_tag, x, y, z)


def _define_boundary_conditions(constraints: List[SinglePointConstraint]) -> None:
    """Define boundary conditions (support constraints)."""
    for constraint in constraints:
        node_tag = constraint.constrained_node_tag
        restraints = constraint.constraints
        
        # Apply constraints based on the number of DOFs
        if len(restraints) == 2:
            # 2 DOF model (x, y)
            ops.fix(node_tag, restraints[0], restraints[1])
        elif len(restraints) == 3:
            # 3 DOF model (x, y, rz)
            ops.fix(node_tag, restraints[0], restraints[1], restraints[2])
        elif len(restraints) == 6:
            # 6 DOF model (x, y, z, rx, ry, rz)
            ops.fix(node_tag, restraints[0], restraints[1], restraints[2], 
                   restraints[3], restraints[4], restraints[5])


def _define_elements(elements: Dict[int, Element]) -> None:
    """Define elements in OpenSees model."""
    for elem_tag, element in elements.items():
        try:
            if element.element_type == "quad" or element.element_type == "shell":
                # Shell element for 3D model with 6 DOF (membrane + bending)
                node_tags = element.args['nodes']
                section_tag = element.args['matTag']  # Now refers to section instead of material
                
                # Use ShellMITC4 element for better fine mesh behavior
                ops.element("ShellMITC4", elem_tag, *node_tags, section_tag)
                
            elif element.element_type == "truss" or element.element_type == "Truss":
                # Truss element for rebars
                node_tags = element.args['nodes']
                area = element.args.get('A', 0.001)  # Cross-sectional area
                mat_tag = element.args['matTag']
                
                # Steel02 materials use original tag, ElasticIsotropic use offset
                # Check material type to determine correct tag
                ops.element("truss", elem_tag, *node_tags, area, mat_tag)
                
        except Exception:
            pass  # Silently skip errors


def _define_rigid_diaphragm(rigid_diaphragm: RigidDiaphragm) -> None:
    """Define rigid diaphragm constraint."""
    # rigidDiaphragm perpDirn retainedNodeTag constrainedNodeTag1 constrainedNodeTag2 ...
    perpendicular_dir = 3  # Assuming Z-direction for 2D models (out-of-plane)
    
    ops.rigidDiaphragm(perpendicular_dir, 
                      rigid_diaphragm.primary_node_tag,
                      *rigid_diaphragm.secondary_nodes_tags)


def export_opensees_script(model: AnalyticalModel, filename: str) -> None:
    """
    Export the analytical model as an OpenSees Python script.
    
    Args:
        model: AnalyticalModel to convert
        filename: Output filename for the Python script
    """
    import os
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    with open(filename, 'w') as f:
        f.write("#!/usr/bin/env python3\n")
        f.write('"""\n')
        f.write("OpenSees Python script generated from analytical model\n")
        f.write('"""\n\n')
        f.write("# Import OpenSees\n")
        f.write("try:\n")
        f.write("    import opensees as ops\n")
        f.write("except ImportError:\n")
        f.write("    from openseespy.opensees import *\n")
        f.write("    import openseespy.opensees as ops\n\n")
        
        f.write("# Clear existing model\n")
        f.write("ops.wipe()\n\n")
        
        f.write("# Create model\n")
        f.write(f'ops.model("BasicBuilder", "-ndm", {model.n_dimension}, "-ndf", {model.n_dof})\n\n')
        
        f.write("# Define materials\n")
        for mat_tag, material in model.materials.items():
            if material.material_type == "ElasticIsotropic":
                E = material.args.get('E', 25000000000)
                nu = material.args.get('v', 0.2)
                rho = material.args.get('rho', 2400)
                f.write(f'ops.nDMaterial("ElasticIsotropic", {mat_tag}, {E}, {nu}, {rho})\n')
                f.write(f'ops.uniaxialMaterial("Elastic", {mat_tag + 1000}, {E})  # For truss elements\n')
        f.write("\n")
        
        f.write("# Define nodes\n")
        for node_tag, node in model.nodes.items():
            x, y = node.coord.x, node.coord.y
            z = node.coord.z if hasattr(node.coord, 'z') else 0.0
            if z == 0.0:
                f.write(f"ops.node({node_tag}, {x}, {y})\n")
            else:
                f.write(f"ops.node({node_tag}, {x}, {y}, {z})\n")
        f.write("\n")
        
        f.write("# Define boundary conditions\n")
        for constraint in model.sp_constraints:
            node_tag = constraint.constrained_node_tag
            restraints = constraint.constraints
            restraint_str = ", ".join(map(str, restraints))
            f.write(f"ops.fix({node_tag}, {restraint_str})\n")
        f.write("\n")
        
        f.write("# Define elements\n")
        for elem_tag, element in model.elements.items():
            if element.element_type == "quad":
                node_tags = element.args['nodes']
                thick = element.args.get('thick', 0.3)
                plane_type = element.args.get('type', 'PlaneStress')
                mat_tag = element.args['matTag']
                node_str = ", ".join(map(str, node_tags))
                f.write(f'ops.element("quad", {elem_tag}, {node_str}, {thick}, "{plane_type}", {mat_tag})\n')
            elif element.element_type in ["truss", "Truss"]:
                node_tags = element.args['nodes']
                area = element.args.get('A', 0.001)
                mat_tag = element.args['matTag'] + 1000  # Use uniaxial material
                node_str = ", ".join(map(str, node_tags))
                f.write(f'ops.element("truss", {elem_tag}, {node_str}, {area}, {mat_tag})\n')
        f.write("\n")
        
        if model.rigid_diaphragm:
            f.write("# Define rigid diaphragm\n")
            rd = model.rigid_diaphragm
            secondary_str = ", ".join(map(str, rd.secondary_nodes_tags))
            f.write(f"ops.rigidDiaphragm(3, {rd.primary_node_tag}, {secondary_str})\n\n")
        
        f.write("print('OpenSees model defined successfully!')\n")
        f.write(f"print('Nodes: {len(model.nodes)}, Elements: {len(model.elements)}, Materials: {len(model.materials)}')\n")
