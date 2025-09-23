"""
Working 2-element column based on the successful single brick
"""

import opensees as ops

def create_two_element_column():
    """Create a working 2-element column"""
    
    ops.wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 3)
    
    # Material
    E = 30e9
    nu = 0.2 
    rho = 2400
    ops.nDMaterial('ElasticIsotropic', 1, E, nu, rho)
    
    # Create nodes for 2-element column (0.5x0.5x3.0 m total)
    # Each element is 0.5x0.5x1.5 m
    
    # Bottom layer (y=0)
    ops.node(1, 0.0, 0.0, 0.0)  # Bottom-left-front
    ops.node(2, 0.5, 0.0, 0.0)  # Bottom-right-front  
    ops.node(3, 0.5, 0.0, 0.5)  # Bottom-right-back
    ops.node(4, 0.0, 0.0, 0.5)  # Bottom-left-back
    
    # Middle layer (y=1.5)
    ops.node(5, 0.0, 1.5, 0.0)  # Middle-left-front
    ops.node(6, 0.5, 1.5, 0.0)  # Middle-right-front
    ops.node(7, 0.5, 1.5, 0.5)  # Middle-right-back  
    ops.node(8, 0.0, 1.5, 0.5)  # Middle-left-back
    
    # Top layer (y=3.0)
    ops.node(9,  0.0, 3.0, 0.0)  # Top-left-front
    ops.node(10, 0.5, 3.0, 0.0)  # Top-right-front
    ops.node(11, 0.5, 3.0, 0.5)  # Top-right-back
    ops.node(12, 0.0, 3.0, 0.5)  # Top-left-back
    
    print("Created 12 nodes for 2-element column")
    
    # Create 2 brick elements
    # Element 1: bottom half (nodes 1-8)
    ops.element('stdBrick', 1, 1, 2, 3, 4, 5, 6, 7, 8, 1, 0.0, 0.0, 0.0)
    
    # Element 2: top half (nodes 5-12) 
    ops.element('stdBrick', 2, 5, 6, 7, 8, 9, 10, 11, 12, 1, 0.0, 0.0, 0.0)
    
    print("Created 2 brick elements")
    
    # Fix bottom nodes (1,2,3,4)
    for node in [1, 2, 3, 4]:
        ops.fix(node, 1, 1, 1)
    print("Fixed bottom 4 nodes")
    
    # Check system
    try:
        num_dof = ops.systemSize()
        print(f"System DOF: {num_dof}")
    except:
        print("Could not get system size")
    
    return {
        'total_nodes': 12,
        'total_elements': 2,
        'fixed_nodes': 4
    }

def test_two_element_column():
    """Test the 2-element column"""
    
    model_info = create_two_element_column()
    
    print(f"\n=== 2-ELEMENT COLUMN TEST ===")
    
    # Apply load to top corner (node 9)
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.load(9, 0.0, -1000.0, 0.0)  # 1kN downward in Y direction
    print("Applied 1kN downward load to top node 9")
    
    # Analysis setup
    ops.system('BandGeneral')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.test('NormUnbalance', 1.0e-6, 25, 0)
    ops.algorithm('Newton')
    ops.integrator('LoadControl', 1.0)
    ops.analysis('Static')
    
    print("Attempting analysis...")
    ok = ops.analyze(1)
    
    if ok == 0:
        # Success - get displacement
        disp_y = ops.nodeDisp(9, 2)  # Y displacement
        computed_disp = abs(disp_y * 1000)  # mm
        
        print(f"✓ SUCCESS! Node 9 Y displacement: {disp_y:.6e} m = {computed_disp:.6f} mm")
        
        # Analytical cantilever beam check
        P = 1000  # N
        L = 3.0   # m
        E = 30e9  # Pa
        I = (0.5 * 0.5**3) / 12  # m⁴ (bh³/12)
        analytical_disp = (P * L**3) / (3 * E * I) * 1000  # mm
        
        print(f"Analytical cantilever: {analytical_disp:.6f} mm")
        error = abs(computed_disp - analytical_disp) / analytical_disp * 100
        print(f"Error: {error:.2f}%")
        
        return True
    else:
        print(f"✗ Analysis failed with code: {ok}")
        return False

if __name__ == "__main__":
    print("=== 2-ELEMENT COLUMN TEST ===")
    success = test_two_element_column()
    
    if success:
        print("\n✓ 2-element column works!")
        print("Now we can build up to the full model.")
    else:
        print("\n✗ 2-element column failed.")
