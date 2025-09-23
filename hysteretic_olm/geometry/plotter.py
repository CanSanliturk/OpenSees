"""
Geometry visualization and plotting utilities.

This module provides classes for visualizing geometric shapes and saving plots to files.
"""

import matplotlib.pyplot as plt
import matplotlib
import os
from typing import Optional, Tuple
from geometry.geometry import Shape

class GeometryPlotter:
    """
    A class for plotting and saving geometric shapes.
    """
    
    def __init__(self, backend: str = 'Agg'):
        """
        Initialize the GeometryPlotter.
        
        Args:
            backend: matplotlib backend to use ('Agg' for non-interactive, 
                    'TkAgg' for interactive, etc.)
        """
        matplotlib.use(backend)
        self.backend = backend
    
    def plot_shape(self, shape: Shape, ax: Optional[plt.Axes] = None, 
                   color: str = 'blue', hole_color: str = 'white', 
                   alpha: float = 0.5, show: bool = True) -> Tuple[Optional[plt.Figure], plt.Axes]:
        """
        Plot a Shape object on matplotlib axes.
        
        Args:
            shape: Shape object to plot
            ax: matplotlib axes object. If None, creates new figure
            color: color for the outer shape
            hole_color: color for holes
            alpha: transparency level
            show: whether to call plt.show() (only when ax is None)
        
        Returns:
            tuple: (fig, ax) if new figure was created, otherwise (None, ax)
        """
        created_fig = False
        fig = None
        if ax is None:
            fig, ax = plt.subplots()
            created_fig = True
        
        # Draw outer shape
        xs = [p.x for p in shape.points] + [shape.points[0].x]
        ys = [p.y for p in shape.points] + [shape.points[0].y]
        ax.fill(xs, ys, color=color, alpha=alpha, edgecolor='black')
        
        # Draw holes
        for hole in shape.holes:
            hx = [p.x for p in hole.points] + [hole.points[0].x]
            hy = [p.y for p in hole.points] + [hole.points[0].y]
            ax.fill(hx, hy, color=hole_color, alpha=1.0, edgecolor='black')
        
        ax.set_aspect('equal')
        
        # Only show if we created the figure and show=True
        if created_fig and show:
            plt.show()
        
        return (fig, ax)
    
    def save_shape_plot(self, shape: Shape, filepath: str, dpi: int = 150, 
                        color: str = 'blue', hole_color: str = 'white', 
                        alpha: float = 0.5, bbox_inches: str = 'tight', 
                        figsize: Optional[Tuple[float, float]] = None) -> str:
        """
        Plot a Shape object and save it to a file.
        
        Args:
            shape: Shape object to plot
            filepath: path/name of the file to save
            dpi: dots per inch for the saved image
            color: color for the outer shape
            hole_color: color for holes
            alpha: transparency level
            bbox_inches: bbox_inches parameter for plt.savefig
            figsize: tuple for figure size (width, height)
        
        Returns:
            str: the filepath that was saved
        """
        # Create directory if it doesn't exist
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        
        # Create figure
        if figsize:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig, ax = plt.subplots()

        # Plot the shape
        self.plot_shape(shape, ax=ax, color=color, hole_color=hole_color, 
                       alpha=alpha, show=False)

        # Save the figure
        plt.savefig(filepath, dpi=dpi, bbox_inches=bbox_inches)
        plt.close(fig)  # Close to free memory

        print(f"Plot saved as '{filepath}'")
        return filepath
