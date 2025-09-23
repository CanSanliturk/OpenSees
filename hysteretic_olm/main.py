from geometry.geometry import *
from analytical_model.entities import *
from analytical_model.analytical_model import AnalyticalModel
from analytical_model.brick_model_generator import BrickModelGenerator
from analysis_runner.eigenvalue_analysis_runner import EigenValueAnalysisRunner

def create_column_model():
    """
    Create a 3m long column with 50cm x 50cm square cross-section
    Four rebars close to corners with meaningful areas
    Fixed at bottom
    """
    
    # Column dimensions (in meters)
    column_length = 3.0  # 3m height
    column_width = 0.5   # 50cm width
    column_depth = 0.5   # 50cm depth
    
    # Create rectangular cross-section shape (50cm x 50cm)
    # Using a 2D representation for membrane analysis
    
    # Create the rectangular cross-section shape for the column
    # Shape input: XY plane (width × height), extruded in Z direction (depth)
    # Y represents the actual height direction in the shape
    column_shape = Shape([
        Point(0.0, 0.0),                    # bottom-left corner
        Point(column_width, 0.0),           # bottom-right corner  
        Point(column_width, column_length), # top-right corner (using column_length for height)
        Point(0.0, column_length)           # top-left corner (using column_length for height)
    ])
    
    # Create concrete material using ElasticIsotropic for brick elements
    concrete_material = Material(
        tag=1,
        material_type="ElasticIsotropic",
        E=30e9,     # 30 GPa Young's modulus  
        v=0.2,      # Poisson's ratio
        rho=2400    # kg/m³ density
    )
    
    # Create rebar material (steel for truss elements)
    rebar_material = Material(
        tag=2, 
        material_type="Steel02",
        Fy=420e6,   # 420 MPa yield strength (in Pa for consistency)
        E=200e9,    # 200 GPa elastic modulus (in Pa)
        b=0.02      # strain hardening ratio
    )
    
    # Initialize brick model generator
    generator = BrickModelGenerator()
    
    # Set concrete properties - extrude shape in Z direction (depth)
    concrete_thickness = column_depth  # 50cm depth (Z-direction extrusion)
    generator.set_concrete(column_shape, concrete_material, concrete_thickness)
    
    # Add rebars with meaningful areas
    # Typical reinforced concrete column reinforcement:
    # - Corner rebars: #10 rebar (φ32mm ≈ 8.0 cm²) 
    # - Intermediate rebars: #8 rebar (φ25mm ≈ 5.0 cm²)
    rebar_area = 0.0005  # m² (5 cm²) - will be overridden below
    
    # Reinforcement ratio calculation:
    # Gross concrete area = 50cm × 50cm = 2500 cm²
    # Total steel area = 4×8cm² + 4×5cm² = 52 cm²  
    # Reinforcement ratio ρ = 52/2500 = 2.08% (typical range: 1-4%)
    
    # Rebar positions aligned with 25cm mesh grid
    # With 25cm mesh, grid points are at: 0.0, 0.25, 0.5
    rebar_x1 = 0.25  # Interior grid point (25cm from left)
    
    # Rebar positions - vertical rebars along column height (Y-direction)
    # For a 50cm x 50cm column, typical rebar arrangement includes:
    # - 4 corner rebars for confinement
    # - 2 additional rebars on each side for distributed reinforcement
    # Total: 8 longitudinal rebars
    
    # Rebar positions aligned with mesh grid (0.0, 0.25, 0.5)
    # Use front face (Z=0) for all rebars for simplicity with current mesh
    corner_positions = [
        # Corner rebars (4 rebars at corners)
        Vector(Point(0.0, 0.0, 0.0), Point(0.0, 3.0, 0.0)),      # bottom-left corner
        Vector(Point(0.5, 0.0, 0.0), Point(0.5, 3.0, 0.0)),      # bottom-right corner
        Vector(Point(0.0, 0.0, 0.5), Point(0.0, 3.0, 0.5)),      # top-left corner (back face)
        Vector(Point(0.5, 0.0, 0.5), Point(0.5, 3.0, 0.5)),      # top-right corner (back face)
        
        # Intermediate rebars for better distribution (4 rebars at mid-points)
        Vector(Point(0.25, 0.0, 0.0), Point(0.25, 3.0, 0.0)),    # center of front face
        Vector(Point(0.25, 0.0, 0.5), Point(0.25, 3.0, 0.5)),    # center of back face
        Vector(Point(0.0, 0.0, 0.25), Point(0.0, 3.0, 0.25)),    # center of left face
        Vector(Point(0.5, 0.0, 0.25), Point(0.5, 3.0, 0.25)),    # center of right face
    ]
    
    # Add rebars to the model with realistic sizing
    # Corner rebars: larger diameter (#10 rebar ≈ 8 cm²)
    # Intermediate rebars: smaller diameter (#8 rebar ≈ 5 cm²)
    
    corner_rebar_area = 0.0008  # m² (8 cm² for corner rebars)
    intermediate_rebar_area = 0.0005  # m² (5 cm² for intermediate rebars)
    
    for i, rebar_pos in enumerate(corner_positions):
        # First 4 rebars are corner rebars (larger)
        if i < 4:
            generator.add_rebar(rebar_pos, corner_rebar_area, rebar_material)
        else:
            # Remaining 4 rebars are intermediate rebars (smaller)
            generator.add_rebar(rebar_pos, intermediate_rebar_area, rebar_material)
    
    # Add fixed supports at ALL bottom face nodes (Y=0 plane)
    mesh_size = 0.25  # 25cm mesh for better numerical stability with brick elements
    
    # Fixed support constrains all DOFs for 3D brick analysis: [1,1,1] for (x,y,z)
    fixed_restraint = [1, 1, 1]  # Fixed all 3 translational DOF for brick elements
    
    # Calculate all nodes at the bottom face (Y=0) based on mesh size
    # For column: X from 0 to column_width, Z from 0 to column_depth, Y=0
    import numpy as np
    
    # Generate X coordinates based on mesh size
    n_x = int(np.round(column_width / mesh_size)) + 1
    x_coords = np.linspace(0.0, column_width, n_x)
    
    # Generate Z coordinates based on mesh size  
    n_z = int(np.round(column_depth / mesh_size)) + 1
    z_coords = np.linspace(0.0, column_depth, n_z)
    
    # Add support at every node on the bottom face (Y=0)
    for x in x_coords:
        for z in z_coords:
            # Check if the point is inside the column shape (should be for all points in rectangle)
            bottom_point = Point(float(x), 0.0, float(z))
            # For rectangular column, all grid points should be inside
            generator.add_support(bottom_point, fixed_restraint)
    
    # Generate the model with appropriate mesh size (25cm mesh)
    # Generate the model with visualization and custom save path
    custom_save_path = "outputs/column_brick_model_visualization.png"
    model = generator.generate(mesh_size, print_model=False, save_path=custom_save_path)

    return model

def create_frame_model():
    """
    Create a two-column one-beam frame model using a single shape with a hole
    Frame dimensions: 6m wide x 4m tall, with 0.5m thick columns and beam
    """
    
    generator = BrickModelGenerator()
    
    # Frame dimensions
    frame_width = 6.0    # 6m total width
    frame_height = 4.0   # 4m total height
    column_width = 0.5   # 50cm column width
    beam_height = 0.6    # 60cm beam height
    
    # Outer boundary points (counter-clockwise)
    outer_points = [
        Point(0.0, 0.0),                           # bottom-left
        Point(frame_width, 0.0),                   # bottom-right
        Point(frame_width, frame_height),          # top-right
        Point(0.0, frame_height)                   # top-left
    ]
    
    # Inner hole (the space between columns and under beam)
    # Hole starts after left column and ends before right column
    # Hole starts from ground and goes up to bottom of beam
    hole_left = column_width
    hole_right = frame_width - column_width
    hole_bottom = 0.0
    hole_top = frame_height - beam_height
    
    hole_points = [
        Point(hole_left, hole_bottom),    # bottom-left of hole
        Point(hole_right, hole_bottom),   # bottom-right of hole  
        Point(hole_right, hole_top),      # top-right of hole
        Point(hole_left, hole_top)        # top-left of hole
    ]
    
    # Create hole shape
    hole_shape = Shape(hole_points)
    
    # Create main frame shape with hole
    frame_shape = Shape(outer_points, holes=[hole_shape])
    
    # Create concrete material using ElasticIsotropic for brick elements
    concrete_material = Material(
        tag=1,
        material_type="ElasticIsotropic",
        E=30e9,     # 30 GPa Young's modulus
        v=0.2,      # Poisson's ratio
        rho=2400    # kg/m³ density
    )
    
    # Create rebar material (steel for truss elements)
    rebar_material = Material(
        tag=2,
        material_type="Steel02",
        Fy=420e6,   # 420 MPa yield strength (in Pa)
        E=200e9,    # 200 GPa elastic modulus (in Pa)  
        b=0.02      # strain hardening ratio
    )
    
    # Set concrete properties
    concrete_thickness = 0.3  # 30cm thick frame
    generator.set_concrete(frame_shape, concrete_material, concrete_thickness)
    
    # Add rebars - simplified realistic reinforcement for frame structure
    rebar_area = 0.0005  # m² (5 cm²)
    
    # Mesh size for positioning rebars
    mesh_size = 0.25  # 25cm mesh for stable element analysis
    
    # Simplified rebar arrangement using only mesh-aligned positions
    # Left column vertical rebars - use front face only for reliability
    left_col_rebars = [
        Vector(Point(0.25, 0.0, 0.0), Point(0.25, 3.75, 0.0)),  # center of left column, front face
    ]
    
    # Right column vertical rebars - use front face only
    right_col_rebars = [
        Vector(Point(5.75, 0.0, 0.0), Point(5.75, 3.75, 0.0)),  # center of right column, front face
    ]
    
    # Beam horizontal rebars - simplified to single rebar
    beam_rebars = [
        Vector(Point(0.75, 3.75, 0.0), Point(5.25, 3.75, 0.0)),  # beam reinforcement, front face
    ]
    
    # Add all rebars to the model
    all_rebars = left_col_rebars + right_col_rebars + beam_rebars
    
    for rebar_vector in all_rebars:
        generator.add_rebar(rebar_vector, rebar_area, rebar_material)
        
    # Add supports at ALL nodes on the bottom face (Y=0) of both columns
    fixed_restraint = [1, 1, 1]  # Fixed all 3 translational DOF for brick elements
    
    # Import numpy for coordinate calculations
    import numpy as np
    
    # Generate all X coordinates that will be nodes on the bottom face
    n_x = int(np.round(frame_width / mesh_size)) + 1
    x_coords = np.linspace(0.0, frame_width, n_x)
    
    # Generate all Z coordinates for the frame thickness
    n_z = int(np.round(concrete_thickness / mesh_size)) + 1  
    z_coords = np.linspace(0.0, concrete_thickness, n_z)
    
    # Fix all nodes at Y=0 that are inside the frame shape (i.e., in the column areas)
    for x in x_coords:
        for z in z_coords:
            bottom_point_2d = Point(float(x), 0.0)  # 2D point for shape checking
            
            # Check if this bottom point is inside the frame shape
            if frame_shape.isInside(bottom_point_2d):
                bottom_point_3d = Point(float(x), 0.0, float(z))
                generator.add_support(bottom_point_3d, fixed_restraint)
    
    # Generate the model with visualization and custom save path
    custom_save_path = "outputs/frame_brick_model_visualization.png"
    model = generator.generate(mesh_size, print_model=False, save_path=custom_save_path)

    return model

def main():
    print("Structural Model Generator")
    print("Choose a model to generate:")
    print("1. Single Column Model (50cm x 50cm x 3m)")
    print("2. Two-Column Frame Model (6m x 4m)")
    print()
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\nCreating 3m Column Model...")
        model = create_column_model()
        
        if model:
            # Run eigenvalue analysis
            print("\nRunning eigenvalue analysis...")
            runner = EigenValueAnalysisRunner(model, n_modes=5)
            try:
                results = runner.run()
                
                # Log analysis results
                print("\nEigenvalue Analysis Results:")
                print(f"Model: {results.n_dimension}D with {results.n_nodes} nodes")
                print(f"Modes extracted: {results.n_modes}")
                
                for i, (eigenval, freq, period) in enumerate(zip(results.eigenvalues, results.frequencies, results.periods)):
                    period_str = f"{period:.4f}" if period != float('inf') else "∞"
                    print(f"Mode {i+1}: λ={eigenval:.6e}, f={freq:.4f} Hz, T={period_str} s")
                
                # Export results
                results.export_to_file("outputs/column_eigenvalue_results.txt")
                print("\nResults exported to outputs/column_eigenvalue_results.txt")
                
            except Exception as e:
                print(f"Analysis failed: {e}")
        else:
            print("Failed to create column model")
    
    elif choice == "2":
        print("\nCreating Two-Column Frame Model...")
        model = create_frame_model()
        
        if model:
            # Run eigenvalue analysis
            print("\nRunning eigenvalue analysis...")
            runner = EigenValueAnalysisRunner(model, n_modes=5)
            try:
                results = runner.run()
                
                # Log analysis results
                print("\nEigenvalue Analysis Results:")
                print(f"Model: {results.n_dimension}D with {results.n_nodes} nodes")
                print(f"Modes extracted: {results.n_modes}")
                
                for i, (eigenval, freq, period) in enumerate(zip(results.eigenvalues, results.frequencies, results.periods)):
                    period_str = f"{period:.4f}" if period != float('inf') else "∞"
                    print(f"Mode {i+1}: λ={eigenval:.6e}, f={freq:.4f} Hz, T={period_str} s")
                
                # Export results
                results.export_to_file("outputs/frame_eigenvalue_results.txt")
                print("\nResults exported to outputs/frame_eigenvalue_results.txt")
                
            except Exception as e:
                print(f"Analysis failed: {e}")
        else:
            print("Failed to create frame model")
    
    else:
        print("Invalid choice. Please run again and select 1 or 2.")

if __name__ == "__main__":
    main()
