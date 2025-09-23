from analysis_runner.analysis_runner import AnalysisRunner, define_model
from analytical_model.analytical_model import AnalyticalModel
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

# Import OpenSees Python module
try:
    import opensees as ops
except ImportError:
    try:
        from openseespy.opensees import *
        import openseespy.opensees as ops
    except ImportError:
        ops = None


@dataclass
class EigenValueAnalysisResults:
    """
    Results from eigenvalue analysis.
    
    Attributes:
        eigenvalues: List of eigenvalues
        frequencies: List of natural frequencies (Hz)
        periods: List of natural periods (s)
        mode_shapes: Dictionary of mode shapes {mode_number: [displacements]}
        n_modes: Number of modes extracted
        n_dimension: Model dimension (2D or 3D)
        n_nodes: Number of nodes in the model
    """
    eigenvalues: List[float]
    frequencies: List[float]
    periods: List[float]
    mode_shapes: Dict[int, List[float]]
    n_modes: int
    n_dimension: int
    n_nodes: int
    
    def export_to_file(self, filename: str):
        """
        Export eigenvalue analysis results to a file.
        
        Args:
            filename: Output filename
        """
        import os
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write("Eigenvalue Analysis Results\n")
            f.write("=" * 50 + "\n")
            f.write(f"Model: {self.n_dimension}D with {self.n_nodes} nodes\n")
            f.write(f"Modes extracted: {self.n_modes}\n\n")
            
            f.write(f"{'Mode':<6} {'Eigenvalue':<15} {'Frequency (Hz)':<15} {'Period (s)':<15}\n")
            f.write("-" * 60 + "\n")
            
            for i, (eigenval, freq, period) in enumerate(zip(self.eigenvalues, self.frequencies, self.periods)):
                period_str = f"{period:.6f}" if period != float('inf') else "inf"
                f.write(f"{i+1:<6} {eigenval:<15.6e} {freq:<15.6f} {period_str:<15}\n")
            
            if self.mode_shapes:
                f.write(f"\nMode Shapes:\n")
                f.write("-" * 20 + "\n")
                for mode, shape in self.mode_shapes.items():
                    f.write(f"Mode {mode}: {len(shape)} DOF values\n")

class EigenValueAnalysisRunner(AnalysisRunner):
    """
    Eigenvalue analysis runner for OpenSees models.
    Performs modal analysis to extract natural frequencies and mode shapes.
    """
    
    def __init__(self, model: AnalyticalModel, n_modes: int):
        """
        Initialize eigenvalue analysis runner.
        
        Args:
            model: AnalyticalModel to analyze
            n_modes: Number of modes to extract
        """
        self.model = model
        self.n_modes = n_modes
        self.frequencies: Optional[List[float]] = None
        self.periods: Optional[List[float]] = None
        self.eigenvalues: Optional[List[float]] = None
        self.mode_shapes: Optional[Dict[int, List[float]]] = None
    
    def run(self) -> EigenValueAnalysisResults:
        """
        Run eigenvalue analysis and return results.
        
        Returns:
            EigenValueAnalysisResults object containing analysis results
        """
        if ops is None:
            raise ImportError("OpenSees Python module is required for eigenvalue analysis")
        
        # Define the OpenSees model
        define_model(self.model)
        
        # TEMPORARY: Export model for debugging
        from analysis_runner.analysis_runner import export_opensees_script
        export_opensees_script(self.model, "outputs/column_model_debug.py")
        
        # FIXED: Use more robust eigenvalue solver
        # Try different solvers for better numerical stability
        try:
            # First try BandArpack solver (more robust)
            ops.system("BandSPD")
            eigenvalues = ops.eigen(self.n_modes)
        except:
            try:
                # Fallback to ProfileSPD with different solver
                ops.system("ProfileSPD")  
                eigenvalues = ops.eigen(self.n_modes)
            except:
                # Last resort - use basic solver
                eigenvalues = ops.eigen(self.n_modes)
        
        if not eigenvalues or len(eigenvalues) == 0:
            raise RuntimeError("Eigenvalue analysis failed - no eigenvalues extracted")
        
        # Calculate frequencies and periods
        frequencies = []
        periods = []
        
        for eigenval in eigenvalues:
            if eigenval > 0:
                freq = np.sqrt(eigenval) / (2 * np.pi)  # Natural frequency in Hz
                period = 1.0 / freq if freq > 0 else float('inf')  # Period in seconds
            else:
                freq = 0.0
                period = float('inf')
            frequencies.append(freq)
            periods.append(period)
        
        # Extract mode shapes
        mode_shapes = {}
        node_tags = list(self.model.nodes.keys())
        
        for mode in range(1, len(eigenvalues) + 1):
            # Get mode shape for this mode
            mode_shape = []
            for node_tag in node_tags:
                # Extract all DOFs based on model.n_dof
                for dof in range(1, self.model.n_dof + 1):
                    dof_value = ops.nodeEigenvector(node_tag, mode, dof)
                    mode_shape.append(dof_value)
            
            mode_shapes[mode] = mode_shape
        
        # Store results
        self.eigenvalues = eigenvalues
        self.frequencies = frequencies
        self.periods = periods
        self.mode_shapes = mode_shapes
        
        # Create results object
        results = EigenValueAnalysisResults(
            eigenvalues=eigenvalues,
            frequencies=frequencies,
            periods=periods,
            mode_shapes=mode_shapes,
            n_modes=len(eigenvalues),
            n_dimension=self.model.n_dimension,
            n_nodes=len(self.model.nodes)
        )
        
        return results
    
    def get_mode_shape_matrix(self, mode: int) -> Optional[np.ndarray]:
        """
        Get mode shape as a matrix for visualization.
        
        Args:
            mode: Mode number (1-based)
            
        Returns:
            numpy array with shape (n_nodes, n_dof) or None if mode not found
        """
        if self.mode_shapes is None or mode not in self.mode_shapes:
            return None
        
        mode_data = self.mode_shapes[mode]
        n_nodes = len(self.model.nodes)
        dof_per_node = self.model.n_dof
        
        # Reshape mode shape data into matrix
        mode_matrix = np.array(mode_data).reshape(n_nodes, dof_per_node)
        return mode_matrix
    
    def export_results(self, filename: str) -> None:
        """
        Export eigenvalue analysis results to a file.
        
        Args:
            filename: Output filename
        """
        if self.eigenvalues is None:
            raise ValueError("No results to export. Run analysis first.")
        
        import os
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write("Eigenvalue Analysis Results\n")
            f.write("=" * 50 + "\n")
            f.write(f"Model: {self.model.n_dimension}D\n")
            f.write(f"Nodes: {len(self.model.nodes)}\n")
            f.write(f"Elements: {len(self.model.elements)}\n")
            f.write(f"Modes extracted: {len(self.eigenvalues)}\n\n")
            
            f.write(f"{'Mode':<6} {'Eigenvalue':<15} {'Frequency (Hz)':<15} {'Period (s)':<15}\n")
            f.write("-" * 60 + "\n")
            
            for i, (eigenval, freq, period) in enumerate(zip(self.eigenvalues, self.frequencies, self.periods)):
                period_str = f"{period:.6f}" if period != float('inf') else "inf"
                f.write(f"{i+1:<6} {eigenval:<15.6e} {freq:<15.6f} {period_str:<15}\n")
            
            if self.mode_shapes:
                f.write(f"\nMode Shapes:\n")
                f.write("-" * 20 + "\n")
                for mode, shape in self.mode_shapes.items():
                    f.write(f"Mode {mode}: {len(shape)} DOF values\n")