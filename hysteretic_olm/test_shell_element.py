#!/usr/bin/env python3
"""
Test ShellMITC4 element for column modeling with fine mesh
"""
import opensees as ops
import numpy as np

def test_shell_column():
    """Test column using ShellMITC4 elements"""
    print("=== SHELL ELEMENT COLUMN TEST ===")
    ops.wipe()
    
    # 3D model with 6 DOF per node
    ops.model('basic', '-ndm', 3, '-ndf', 6)
    
    # Material properties from your Concrete01
    E = 30e9  # Pa (from Concrete01 derived)
    nu = 0.2
    thickness = 0.5  # 50cm column depth
    rho = 2400  # kg/m³
    
    # Create elastic membrane-plate section
    ops.section('ElasticMembranePlateSection', 1, E, nu, thickness, rho)
    
    # Column geometry
    width = 0.5   # 50cm width
    height = 3.0  # 3m height
    
    # Coarser mesh than your current 10cm - use 25cm elements
    mesh_size = 0.10  # 10cm mesh - same as quad elements
    n_x = int(width / mesh_size)    # Elements in width
    n_y = int(height / mesh_size)   # Elements in height
    
    print(f"Creating {width}m x {height}m column with {n_x}x{n_y} shell elements")
    print(f"Mesh size: {mesh_size*100}cm - same as quad element test")
    
    # Create nodes
    node_tag = 1
    for j in range(n_y + 1):
        for i in range(n_x + 1):
            x = i * mesh_size
            y = j * mesh_size
            z = 0.0  # Column in XY plane
            ops.node(node_tag, x, y, z)
            node_tag += 1
    
    # Create shell elements
    elem_tag = 1
    for j in range(n_y):
        for i in range(n_x):
            # Node connectivity for shell element
            n1 = j * (n_x + 1) + i + 1
            n2 = n1 + 1
            n3 = n2 + (n_x + 1)  
            n4 = n1 + (n_x + 1)
            
            ops.element('ShellMITC4', elem_tag, n1, n2, n3, n4, 1)
            elem_tag += 1
    
    # Boundary conditions - fix bottom edge (cantilever)
    # Fix all 6 DOF for bottom nodes
    for i in range(n_x + 1):
        bottom_node = i + 1
        ops.fix(bottom_node, 1, 1, 1, 1, 1, 1)  # Fix all DOF
    
    # Eigenvalue analysis
    try:
        eigenvals = ops.eigen(3)
        print(f"Shell element results:")
        for i, eigenval in enumerate(eigenvals):
            freq = np.sqrt(eigenval) / (2 * np.pi)
            print(f"  Mode {i+1}: {freq:.2f} Hz")
            
        # Compare with beam theory
        I = width * thickness**3 / 12  # Moment of inertia
        mu = rho * width * thickness   # Mass per unit length  
        f_beam = (1.875**2 / (2 * np.pi)) * np.sqrt(E * I / (mu * height**4))
        print(f"  Beam theory: {f_beam:.2f} Hz")
        
        total_mass = rho * width * height * thickness
        print(f"  Total mass: {total_mass:.0f} kg")
        
    except Exception as e:
        print(f"  Shell test failed: {e}")

if __name__ == "__main__":
    test_shell_column()
