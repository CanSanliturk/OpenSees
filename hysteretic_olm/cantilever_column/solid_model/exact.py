
import numpy as np

# Parameters from your OpenSees model
height = 3.0    # m (L - cantilever length)
width = 0.5     # m (in Y direction)
depth = 0.5     # m (in X direction)
E = 30e9        # Pa (Young's modulus)
rho = 2500      # kg/m³ (density)
nu = 0.3        # Poisson's ratio

# Derived material properties
G = E / (2 * (1 + nu))  # Shear modulus

# Cross-sectional properties
A = width * depth                           # Cross-sectional area
Ix = (width * depth**3) / 12               # Moment of inertia about X-axis  
Iy = (depth * width**3) / 12               # Moment of inertia about Y-axis
J = Ix + Iy                                # Polar moment of inertia (for rectangular section)

print("=== GEOMETRY AND MATERIAL PROPERTIES ===")
print(f"Length (height): {height} m")
print(f"Cross-section: {width} × {depth} m")
print(f"Cross-sectional area: {A} m²")
print(f"Moment of inertia Ix: {Ix:.8f} m⁴")
print(f"Moment of inertia Iy: {Iy:.8f} m⁴") 
print(f"Polar moment J: {J:.8f} m⁴")
print(f"Young's modulus: {E/1e9:.1f} GPa")
print(f"Shear modulus: {G/1e9:.1f} GPa")
print(f"Density: {rho} kg/m³")
print()

# Cantilever beam eigenvalue coefficients (λ values) for bending modes
lambda_bending = [1.875104, 4.694091, 7.854757, 10.995541, 14.137165, 17.278760]

print("=== BENDING MODES ===")
print("Theory: ω = (λ²/L²) × √(EI/ρA)")
print("Since Ix = Iy, bending modes in X and Y directions are identical")
print()

bending_periods = []
for i, lam in enumerate(lambda_bending):
    omega = (lam**2 / height**2) * np.sqrt((E * Ix) / (rho * A))
    period = 2 * np.pi / omega
    frequency = 1 / period
    bending_periods.append(period)
    
    print(f"Mode {i+1}: λ = {lam:.6f}")
    print(f"  ω = {omega:.3f} rad/s, f = {frequency:.3f} Hz, T = {period:.6f} s")
    print()

print("=== TORSIONAL MODE ===")
print("Theory: ω = (π/2L) × √(GJ/ρJ)")
print()

# Torsional frequency (first mode)
omega_torsion = (np.pi / (2 * height)) * np.sqrt((G * J) / (rho * J))
period_torsion = 2 * np.pi / omega_torsion  
frequency_torsion = 1 / period_torsion

print(f"Torsional mode:")
print(f"  ω = {omega_torsion:.3f} rad/s, f = {frequency_torsion:.3f} Hz, T = {period_torsion:.6f} s")
print()

print("=== AXIAL MODE ===")  
print("Theory: ω = (π/2L) × √(E/ρ)")
print()

# Axial frequency (first mode)
omega_axial = (np.pi / (2 * height)) * np.sqrt(E / rho)
period_axial = 2 * np.pi / omega_axial
frequency_axial = 1 / period_axial

print(f"Axial mode:")
print(f"  ω = {omega_axial:.3f} rad/s, f = {frequency_axial:.3f} Hz, T = {period_axial:.6f} s")
print()

print("=== SUMMARY OF EXPECTED PERIODS ===")
print("First 6 modes (likely what OpenSees will compute):")
print()

# Combine all modes and sort by period (descending)
all_modes = []
for i, period in enumerate(bending_periods):
    all_modes.append((f"Bending X (Mode {i+1})", period))
    all_modes.append((f"Bending Y (Mode {i+1})", period))

all_modes.append(("Torsional", period_torsion))
all_modes.append(("Axial", period_axial))

# Sort by period (longest first, which corresponds to lowest frequency)
all_modes.sort(key=lambda x: x[1], reverse=True)

print("Expected periods (sorted by magnitude):")
for i, (mode_type, period) in enumerate(all_modes[:10]):
    print(f"{i+1:2d}. {mode_type:20s}: T = {period:.6f} s")
    
print()
print("Note: Since your column has a square cross-section (0.5×0.5 m),")
print("bending modes in X and Y directions will be identical (degenerate).")
print("The first few modes from OpenSees should match the bending periods above.")
