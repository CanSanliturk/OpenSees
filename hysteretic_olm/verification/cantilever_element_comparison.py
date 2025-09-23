"""
Comparison of stdBrick vs BbarBrick elements with modal visualization
Tests both element types on the same cantilever and visualizes mode shapes
"""

import opensees as ops
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
from datetime import datetime

def create_cantilever_model(element_type='stdBrick'):
    """
    Create cantilever model with specified element type
    
    Parameters:
    - element_type: 'stdBrick' or 'bbarBrick'
    
    Returns:
    - success: Boolean indicating if model was created successfully
    - node_coords: Dictionary of node coordinates
    - total_elements: Number of elements created
    """
    
    # Clear existing model
    ops.wipe()
    
    # Create model with 3 DOF per node
    ops.model('basic', '-ndm', 3, '-ndf', 3)
    
    print(f"\n=== CANTILEVER WITH {element_type.upper()} ELEMENTS ===")
    
    # Column dimensions
    L = 3.0      # Length (height) - 3m
    W = 0.5      # Width - 50cm  
    D = 0.5      # Depth - 50cm
    
    # Material properties
    E_concrete = 30e9       # 30 GPa
    nu_concrete = 0.2       # Poisson's ratio
    rho_concrete = 2400     # kg/m³
    
    print(f"Column: {W}m × {D}m × {L}m")
    print(f"Concrete: E={E_concrete/1e9:.0f} GPa, ν={nu_concrete}, ρ={rho_concrete} kg/m³")
    
    # Define material with full density
    ops.nDMaterial('ElasticIsotropic', 1, E_concrete, nu_concrete, rho_concrete)
    
    # Create mesh with 0.1m cubic elements
    element_size = 0.1  # 10cm elements
    
    # Number of elements in each direction
    nx = int(W / element_size)  # 5 elements in X (width)
    ny = int(L / element_size)  # 30 elements in Y (height)
    nz = int(D / element_size)  # 5 elements in Z (depth)
    
    total_elements = nx * ny * nz
    total_nodes = (nx + 1) * (ny + 1) * (nz + 1)
    
    print(f"Mesh: {nx}×{ny}×{nz} = {total_elements} elements")
    print(f"Element size: {element_size}m cubic")
    print(f"Total nodes: {total_nodes}")
    
    # Create nodes
    node_tag = 1
    node_coords = {}
    
    for j in range(ny + 1):  # Y direction (height)
        y = j * element_size
        for k in range(nz + 1):  # Z direction (depth)
            z = k * element_size
            for i in range(nx + 1):  # X direction (width)
                x = i * element_size
                ops.node(node_tag, x, y, z)
                node_coords[node_tag] = (x, y, z)
                node_tag += 1
    
    # Create elements
    elem_tag = 1
    
    # Helper function to get node number
    def get_node(i, j, k):
        return j * (nx + 1) * (nz + 1) + k * (nx + 1) + i + 1
    
    for j in range(ny):  # Y direction (height)
        for k in range(nz):  # Z direction (depth)
            for i in range(nx):  # X direction (width)
                # 8-node brick element connectivity
                n1 = get_node(i, j, k)          # front-left
                n2 = get_node(i+1, j, k)        # front-right  
                n3 = get_node(i+1, j, k+1)      # back-right
                n4 = get_node(i, j, k+1)        # back-left
                n5 = get_node(i, j+1, k)        # front-left (top)
                n6 = get_node(i+1, j+1, k)      # front-right (top)
                n7 = get_node(i+1, j+1, k+1)    # back-right (top)
                n8 = get_node(i, j+1, k+1)      # back-left (top)
                
                # Create element based on type
                if element_type == 'stdBrick':
                    # stdBrick requires body forces
                    ops.element('stdBrick', elem_tag, n1, n2, n3, n4, n5, n6, n7, n8, 1, 0.0, 0.0, 0.0)
                elif element_type == 'bbarBrick':
                    # bbarBrick mixed formulation - no body forces needed
                    ops.element('bbarBrick', elem_tag, n1, n2, n3, n4, n5, n6, n7, n8, 1)
                else:
                    raise ValueError(f"Unknown element type: {element_type}")
                    
                elem_tag += 1
    
    # Fix bottom face (cantilever condition)
    fixed_nodes = 0
    for node, (x, y, z) in node_coords.items():
        if abs(y) < 1e-6:  # Bottom face
            ops.fix(node, 1, 1, 1)  # Fix all DOF
            fixed_nodes += 1
    
    print(f"Fixed {fixed_nodes} bottom nodes")
    
    # Find tip center node
    target_x, target_y, target_z = W/2, L, D/2
    tip_node = None
    min_dist = float('inf')
    
    for node, (x, y, z) in node_coords.items():
        if abs(y - L) < 1e-6:  # Top face
            dist = np.sqrt((x - target_x)**2 + (z - target_z)**2)
            if dist < min_dist:
                min_dist = dist
                tip_node = node
    
    return True, node_coords, total_elements, tip_node

def run_static_analysis(tip_node):
    """Run static analysis and return deflection results"""
    
    # Analysis setup
    ops.system('BandGeneral')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.test('NormUnbalance', 1.0e-6, 25, 0)
    ops.algorithm('Newton')
    ops.integrator('LoadControl', 1.0)
    ops.analysis('Static')
    
    # Apply lateral load
    load = 1000.0  # 1 kN
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.load(tip_node, load, 0.0, 0.0)  # Lateral load in X direction
    
    # Solve
    ok = ops.analyze(1)
    
    if ok == 0:
        # Get displacement
        disp_x = ops.nodeDisp(tip_node, 1) * 1000  # mm
        
        # Theoretical result
        L = 3.0      # Height
        W = 0.5      # Width  
        D = 0.5      # Depth
        E_concrete = 30e9
        
        P = load
        L_beam = L
        E = E_concrete
        I = (W * D**3) / 12  # Moment of inertia
        theory = (P * L_beam**3) / (3 * E * I) * 1000  # mm
        
        error = abs(abs(disp_x) - theory) / theory * 100
        
        return True, abs(disp_x), theory, error
    
    return False, 0, 0, 0

def run_eigenvalue_analysis(num_modes=7):
    """Run eigenvalue analysis and return results"""
    
    # Set up eigenvalue analysis
    ops.system('FullGeneral')
    
    # Compute eigenvalues
    lambda_values = ops.eigen(num_modes)
    
    if len(lambda_values) == 0:
        # Try alternative solver
        try:
            lambda_values = ops.eigen('-genBandArpack', num_modes)
        except:
            ops.system('BandGeneral')
            lambda_values = ops.eigen(num_modes)
    
    # Filter positive eigenvalues
    positive_eigenvalues = [lam for lam in lambda_values if lam > 0]
    positive_eigenvalues.sort()
    
    if len(positive_eigenvalues) == 0:
        return False, [], []
    
    # Calculate frequencies
    frequencies = []
    for lam in positive_eigenvalues:
        omega = np.sqrt(lam)
        freq = omega / (2 * np.pi)
        frequencies.append(freq)
    
    return True, positive_eigenvalues, frequencies

def extract_mode_shapes(node_coords, eigenvalues, num_modes=3):
    """Extract mode shapes for visualization"""
    
    mode_shapes = []
    
    for mode in range(min(num_modes, len(eigenvalues))):
        mode_data = {}
        
        for node in node_coords.keys():
            try:
                # Get displacement for all DOFs (1-indexed mode number)
                dx = ops.nodeEigenvector(node, mode+1, 1)  # X displacement
                dy = ops.nodeEigenvector(node, mode+1, 2)  # Y displacement  
                dz = ops.nodeEigenvector(node, mode+1, 3)  # Z displacement
                mode_data[node] = np.array([dx, dy, dz])
            except:
                mode_data[node] = np.array([0.0, 0.0, 0.0])
        
        mode_shapes.append(mode_data)
    
    return mode_shapes

def visualize_mode_shapes(node_coords, mode_shapes, frequencies, element_type, save_plots=True):
    """Create 3D visualization of mode shapes"""
    
    num_modes = len(mode_shapes)
    
    # Create subplot grid
    fig = plt.figure(figsize=(16, 6*num_modes))
    
    for mode in range(num_modes):
        # Create 3D subplot
        ax = fig.add_subplot(num_modes, 2, 2*mode+1, projection='3d')
        
        # Original structure (blue points)
        nodes = np.array(list(node_coords.values()))
        ax.scatter(nodes[:, 0], nodes[:, 1], nodes[:, 2], 
                  c='blue', s=20, alpha=0.4, label='Original')
        
        # Get mode shape data
        mode_data = mode_shapes[mode]
        
        # Calculate scaling factor for visibility
        max_displacement = 0
        for node_id, disp in mode_data.items():
            max_displacement = max(max_displacement, np.linalg.norm(disp))
        
        if max_displacement > 1e-12:
            scale_factor = 0.2 / max_displacement  # Scale to 20cm max displacement for visualization
        else:
            scale_factor = 1.0
        
        # Deformed shape (red points)
        deformed_nodes = []
        for node_id, coord in node_coords.items():
            if node_id in mode_data:
                disp = mode_data[node_id] * scale_factor
                deformed_coord = np.array(coord) + disp
                deformed_nodes.append(deformed_coord)
        
        if deformed_nodes:
            deformed_nodes = np.array(deformed_nodes)
            ax.scatter(deformed_nodes[:, 0], deformed_nodes[:, 1], deformed_nodes[:, 2], 
                      c='red', s=20, alpha=0.8, label=f'Mode {mode+1}')
            
            # Draw displacement vectors for selected nodes (every 10th node for clarity)
            node_list = list(node_coords.keys())
            for i in range(0, len(node_list), 10):
                node_id = node_list[i]
                coord = np.array(node_coords[node_id])
                disp = mode_data[node_id] * scale_factor
                
                if np.linalg.norm(disp) > 1e-6:
                    ax.quiver(coord[0], coord[1], coord[2],
                             disp[0], disp[1], disp[2],
                             color='red', alpha=0.6, length=1.0, normalize=False)
        
        # Set labels and title
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)') 
        ax.set_zlabel('Z (m)')
        ax.set_title(f'{element_type} - Mode {mode+1}\nf = {frequencies[mode]:.3f} Hz')
        ax.legend()
        
        # Set equal aspect ratio
        max_range = 0.5 * np.array([
            nodes[:, 0].max() - nodes[:, 0].min(),
            nodes[:, 1].max() - nodes[:, 1].min(),
            nodes[:, 2].max() - nodes[:, 2].min()
        ]).max()
        mid_x = (nodes[:, 0].max() + nodes[:, 0].min()) * 0.5
        mid_y = (nodes[:, 1].max() + nodes[:, 1].min()) * 0.5
        mid_z = (nodes[:, 2].max() + nodes[:, 2].min()) * 0.5
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Add 2D side view
        ax2 = fig.add_subplot(num_modes, 2, 2*mode+2)
        
        # Side view (X-Y plane)
        ax2.scatter(nodes[:, 0], nodes[:, 1], c='blue', s=20, alpha=0.4, label='Original')
        if deformed_nodes.size > 0:
            ax2.scatter(deformed_nodes[:, 0], deformed_nodes[:, 1], 
                       c='red', s=20, alpha=0.8, label=f'Mode {mode+1}')
        
        ax2.set_xlabel('X (m)')
        ax2.set_ylabel('Y (m)')
        ax2.set_title(f'Side View - Mode {mode+1}')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_aspect('equal')
    
    plt.tight_layout()
    
    if save_plots:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'outputs/mode_shapes_{element_type}_{timestamp}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"Mode shapes saved to {filename}")
    
    plt.show()

def create_animated_mode_shape(node_coords, mode_data, frequency, element_type, mode_num):
    """Create animated visualization of a single mode shape"""
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Original structure
    nodes = np.array(list(node_coords.values()))
    
    # Calculate scaling factor
    max_displacement = 0
    for node_id, disp in mode_data.items():
        max_displacement = max(max_displacement, np.linalg.norm(disp))
    
    if max_displacement > 1e-12:
        scale_factor = 0.3 / max_displacement
    else:
        scale_factor = 1.0
    
    def animate(frame):
        ax.clear()
        
        # Time-varying amplitude (sinusoidal)
        amplitude = np.sin(frame * 0.2) * scale_factor
        
        # Original structure (blue)
        ax.scatter(nodes[:, 0], nodes[:, 1], nodes[:, 2], 
                  c='blue', s=30, alpha=0.6, label='Original')
        
        # Animated deformed shape (red)
        deformed_nodes = []
        for node_id, coord in node_coords.items():
            if node_id in mode_data:
                disp = mode_data[node_id] * amplitude
                deformed_coord = np.array(coord) + disp
                deformed_nodes.append(deformed_coord)
        
        if deformed_nodes:
            deformed_nodes = np.array(deformed_nodes)
            ax.scatter(deformed_nodes[:, 0], deformed_nodes[:, 1], deformed_nodes[:, 2], 
                      c='red', s=30, alpha=0.8, label=f'Vibrating Mode {mode_num}')
        
        # Set consistent view
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Z (m)')
        ax.set_title(f'{element_type} - Animated Mode {mode_num}\nFrequency = {frequency:.3f} Hz')
        ax.legend()
        
        # Fix axis limits
        max_range = 0.4
        ax.set_xlim(-0.1, 0.6)
        ax.set_ylim(-0.1, 3.1)
        ax.set_zlim(-0.1, 0.6)
    
    # Create animation
    anim = animation.FuncAnimation(fig, animate, frames=100, interval=100, repeat=True)
    
    # Save animation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'outputs/animated_mode_{mode_num}_{element_type}_{timestamp}.gif'
    try:
        anim.save(filename, writer='pillow', fps=10)
        print(f"Animation saved to {filename}")
    except:
        print(f"Could not save animation (pillow writer not available)")
    
    plt.show()
    return anim

def compare_element_types():
    """Main comparison function"""
    
    results = {}
    
    # Test both element types
    element_types = ['stdBrick', 'bbarBrick']
    
    for elem_type in element_types:
        print(f"\n{'='*60}")
        print(f"TESTING {elem_type.upper()} ELEMENTS")
        print('='*60)
        
        # Create model
        success, node_coords, total_elements, tip_node = create_cantilever_model(elem_type)
        
        if not success:
            print(f"❌ Failed to create {elem_type} model")
            continue
            
        # Run static analysis
        success, fea_disp, theory_disp, error = run_static_analysis(tip_node)
        
        if success:
            print(f"✅ Static Analysis Success:")
            print(f"   FEA displacement: {fea_disp:.6f} mm")
            print(f"   Theory: {theory_disp:.6f} mm") 
            print(f"   Error: {error:.2f}%")
        else:
            print(f"❌ Static analysis failed for {elem_type}")
            continue
        
        # Run eigenvalue analysis
        success, eigenvalues, frequencies = run_eigenvalue_analysis()
        
        if success:
            print(f"✅ Eigenvalue Analysis Success:")
            print(f"   Found {len(frequencies)} modes")
            for i, freq in enumerate(frequencies[:5]):
                print(f"   Mode {i+1}: {freq:.3f} Hz")
        else:
            print(f"❌ Eigenvalue analysis failed for {elem_type}")
            continue
        
        # Extract mode shapes
        mode_shapes = extract_mode_shapes(node_coords, eigenvalues, 3)
        
        # Store results
        results[elem_type] = {
            'node_coords': node_coords,
            'static_error': error,
            'frequencies': frequencies,
            'eigenvalues': eigenvalues,
            'mode_shapes': mode_shapes,
            'tip_node': tip_node
        }
        
        # Visualize mode shapes
        print(f"Creating mode shape visualizations...")
        visualize_mode_shapes(node_coords, mode_shapes, frequencies, elem_type)
        
        # Create animation for first mode
        if len(mode_shapes) > 0:
            print(f"Creating animated mode shape...")
            anim = create_animated_mode_shape(
                node_coords, mode_shapes[0], frequencies[0], elem_type, 1)
    
    # Compare results
    print(f"\n{'='*60}")
    print("ELEMENT TYPE COMPARISON")
    print('='*60)
    
    if len(results) == 2:
        std_results = results['stdBrick']
        bbar_results = results['bbarBrick']
        
        print(f"Static Analysis Comparison:")
        print(f"  stdBrick error:  {std_results['static_error']:.2f}%")
        print(f"  bbarBrick error: {bbar_results['static_error']:.2f}%")
        
        if bbar_results['static_error'] < std_results['static_error']:
            print(f"bbarBrick shows better static accuracy!")
        else:
            print(f"stdBrick shows better static accuracy!")
        
        print(f"\nDynamic Analysis Comparison (first 3 modes):")
        print(f"{'Mode':<6} {'stdBrick (Hz)':<15} {'bbarBrick (Hz)':<15} {'Difference':<12}")
        print("-" * 55)
        
        for i in range(min(3, len(std_results['frequencies']), len(bbar_results['frequencies']))):
            std_freq = std_results['frequencies'][i]
            bbar_freq = bbar_results['frequencies'][i]
            diff_percent = abs(std_freq - bbar_freq) / std_freq * 100
            
            print(f"{i+1:<6} {std_freq:<15.3f} {bbar_freq:<15.3f} {diff_percent:<12.2f}%")
        
        avg_std_error = std_results['static_error']
        avg_bbar_error = bbar_results['static_error']
        
        if abs(avg_bbar_error - avg_std_error) < 1.0:
            print("Both element types perform similarly well")
        elif avg_bbar_error < avg_std_error:
            print("bbarBrick RECOMMENDED: Better accuracy, reduced volumetric locking")
        else:
            print("stdBrick RECOMMENDED: Better overall performance")
        
    print(f"\nAnalysis complete - check outputs directory for visualizations")
    
    return results

if __name__ == "__main__":
    results = compare_element_types()
