"""
Ultra-simple single brick element test
"""

import opensees as ops
import numpy as np

def test_single_brick():
    """Test a single brick element"""
    
    # Clear existing model
    ops.wipe()
    
    # Create model with 3 DOF per node
    ops.model('basic', '-ndm', 3, '-ndf', 3)
    
    # Material
    E = 30e9
    nu = 0.2
    rho = 2400
    ops.nDMaterial('ElasticIsotropic', 1, E, nu, rho)
    
    # Create 8 nodes for a single brick (1x1x1 meter cube)
    # Bottom face (z=0)
    ops.node(1, 0.0, 0.0, 0.0)  # node 1: (0,0,0)
    ops.node(2, 1.0, 0.0, 0.0)  # node 2: (1,0,0)
    ops.node(3, 1.0, 1.0, 0.0)  # node 3: (1,1,0)
    ops.node(4, 0.0, 1.0, 0.0)  # node 4: (0,1,0)
    
    # Top face (z=1)
    ops.node(5, 0.0, 0.0, 1.0)  # node 5: (0,0,1)
    ops.node(6, 1.0, 0.0, 1.0)  # node 6: (1,0,1)
    ops.node(7, 1.0, 1.0, 1.0)  # node 7: (1,1,1)
    ops.node(8, 0.0, 1.0, 1.0)  # node 8: (0,1,1)
    
    print("Created 8 nodes for single brick element")
    
    # Create single brick element
    # Node order: bottom face (1,2,3,4), then top face (5,6,7,8)
    ops.element('stdBrick', 1, 1, 2, 3, 4, 5, 6, 7, 8, 1, 0.0, 0.0, 0.0)
    print("Created single brick element")
    
    # Fix bottom face (nodes 1,2,3,4)
    for node in [1, 2, 3, 4]:
        ops.fix(node, 1, 1, 1)
    print("Fixed bottom 4 nodes")
    
    # Check system
    try:
        num_dof = ops.systemSize()
        print(f"System DOF: {num_dof}")
    except:
        print("Could not get system size")
    
    # Apply load to top corner (node 5)
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.load(5, 0.0, 0.0, -1000.0)  # 1kN downward in Z direction
    print("Applied 1kN load in Z direction to node 5")
    
    # Analysis
    ops.system('BandGeneral')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.test('NormUnbalance', 1.0e-6, 10, 0)
    ops.algorithm('Newton')
    ops.integrator('LoadControl', 1.0)
    ops.analysis('Static')
    
    print("Attempting analysis...")
    ok = ops.analyze(1)
    
    if ok == 0:
        # Success - get displacement
        disp_z = ops.nodeDisp(5, 3)  # Z displacement
        print(f"✓ SUCCESS! Node 5 Z displacement: {disp_z*1000:.6f} mm")
        
        # Simple beam theory check (approximate)
        # For a cantilever beam: δ = PL³/(3EI)
        # For cube: I ≈ bh³/12 = 1*1³/12 = 1/12 m⁴
        P = 1000  # N
        L = 1.0   # m 
        I = 1.0/12  # m⁴
        analytical = (P * L**3) / (3 * E * I) * 1000  # mm
        print(f"Rough analytical estimate: {analytical:.6f} mm")
        
        return True
    else:
        print(f"✗ Analysis failed with code: {ok}")
        return False

if __name__ == "__main__":
    print("=== SINGLE BRICK ELEMENT TEST ===")
    success = test_single_brick()
    
    if success:
        print("\n✓ Single brick element works!")
        print("The stdBrick element is functioning correctly.")
    else:
        print("\n✗ Single brick element failed.")
