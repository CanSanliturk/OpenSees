from dataclasses import dataclass


@dataclass
class Point:
    x: float
    y: float
    z: float = 0.0

class Vector:
    def __init__(self, end: Point, start: Point = Point(0.0, 0.0, 0.0)):
        self.end: Point = end
        self.start: Point = start

    def length(self) -> float:
        return ((self.end.x - self.start.x) ** 2 + 
                (self.end.y - self.start.y) ** 2 + 
                (self.end.z - self.start.z) ** 2) ** 0.5

    def cross_product(self, other: 'Vector') -> 'Vector':
        cx = self.start.y * other.end.z - self.start.z * other.end.y
        cy = self.start.z * other.end.x - self.start.x * other.end.z
        cz = self.start.x * other.end.y - self.start.y * other.end.x
        return Vector(Point(cx, cy, cz))

    def dot_product(self, other: 'Vector') -> float:
        return (self.start.x * other.start.x + 
                self.start.y * other.start.y + 
                self.start.z * other.start.z)

    def normalize(self) -> 'Vector':
        length = self.length()
        if length == 0:
            raise ValueError("Cannot normalize a zero-length vector")
        return Vector(Point(self.start.x / length, 
                            self.start.y / length, 
                            self.start.z / length))

    def normal_vector(self) -> 'Vector':
        if self.length() == 0:
            raise ValueError("Cannot compute normal vector of a zero-length vector")
        if self.start.x == 0 and self.start.y == 0:
            return Vector(Point(1.0, 0.0, 0.0))
        return Vector(Point(-self.start.y, self.start.x, 0)).normalize()

    def sum(self, other: 'Vector') -> 'Vector':
        return Vector(Point(self.start.x + other.start.x,
                            self.start.y + other.start.y,
                            self.start.z + other.start.z))

    def difference(self, other: 'Vector') -> 'Vector':
        return Vector(Point(self.start.x - other.start.x,
                            self.start.y - other.start.y,
                            self.start.z - other.start.z))

    def scale(self, scalar: float) -> 'Vector':
        return Vector(Point(self.start.x * scalar,
                            self.start.y * scalar,
                            self.start.z * scalar))

class Shape:
    """
    A 2D shape defined by a list of points (vertices) and optional holes, 
    in counter-clockwise order, on the XY plane.
    """
    def __init__(self, points: list[Point], holes: list['Shape'] = []):
        self.points = points
        self.holes = holes

    def area(self) -> float:
        n = len(self.points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.points[i].x * self.points[j].y
            area -= self.points[j].x * self.points[i].y
        area = abs(area) / 2.0
        for hole in self.holes:
            area -= hole.area()
        return area

    def centroid(self) -> Point:
        n = len(self.points)
        cx = 0.0
        cy = 0.0
        area = self.area()
        factor = 0.0
        for i in range(n):
            j = (i + 1) % n
            factor = (self.points[i].x * self.points[j].y - self.points[j].x * self.points[i].y)
            cx += (self.points[i].x + self.points[j].x) * factor
            cy += (self.points[i].y + self.points[j].y) * factor
        cx /= (6.0 * area)
        cy /= (6.0 * area)
        return Point(cx, cy, 0.0)

    def isInside(self, point: Point) -> bool:
        # Check if point is on both outer boundary and any hole boundary
        # For structural analysis, we need these nodes, so we'll allow them
        # but we could flag them for special handling if needed
        is_on_outer_boundary = self._isOnOuterBoundary(point)
        is_on_hole_boundary = any(hole.isOnBoundary(point) for hole in self.holes)
        
        # Allow coincident boundary points for now (structural requirement)
        # if is_on_outer_boundary and is_on_hole_boundary:
        #     return False  # Would exclude coincident boundaries
            
        # Check if point is on outer boundary - these are considered inside
        if is_on_outer_boundary:
            return True
            
        n = len(self.points)
        inside = False
        p1x, p1y = self.points[0].x, self.points[0].y

        # Ray-casting algorithm: cast a ray from point to the right and count intersections
        for i in range(n):
            p2x, p2y = self.points[(i + 1) % n].x, self.points[(i + 1) % n].y
            
            # Check if ray intersects with this edge
            if ((p1y > point.y) != (p2y > point.y)) and \
               (point.x < (p2x - p1x) * (point.y - p1y) / (p2y - p1y) + p1x):
                inside = not inside
            p1x, p1y = p2x, p2y
        
        # If point is not inside the outer boundary, it's definitely outside
        if not inside:
            return False

        # Check if point is inside any hole - if so, it's outside (hole interior is empty)
        for hole in self.holes:
            if hole.isInside(point) and not hole.isOnBoundary(point):
                return False

        return True

    def _isOnOuterBoundary(self, point: Point, tol: float = 1e-9) -> bool:
        """Check if point is on the outer boundary of the shape (excluding holes)"""
        n = len(self.points)
        for i in range(n):
            j = (i + 1) % n
            if self._point_on_segment(point, self.points[i], self.points[j], tol):
                return True
        return False
    
    def isOnBoundary(self, point: Point, tol: float = 1e-9) -> bool:
        n = len(self.points)
        for i in range(n):
            j = (i + 1) % n
            if self._point_on_segment(point, self.points[i], self.points[j], tol):
                return True
        for hole in self.holes:
            if hole.isOnBoundary(point, tol):
                return True
        return False
    
    def _point_on_segment(self, p: Point, p1: Point, p2: Point, tol: float) -> bool:
        cross = (p2.y - p1.y) * (p.x - p1.x) - (p2.x - p1.x) * (p.y - p1.y)
        if abs(cross) > tol:
            return False
        dot = (p.x - p1.x) * (p2.x - p1.x) + (p.y - p1.y) * (p2.y - p1.y)
        if dot < 0:
            return False
        squared_length = (p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2
        if dot > squared_length:
            return False
        return True

    def bounding_box(self) -> tuple[float, float, float, float]:
        """
        Calculate the bounding box of the shape.
        
        Returns:
            tuple: (min_x, min_y, max_x, max_y) coordinates of the bounding box
        """
        if not self.points:
            raise ValueError("Cannot calculate bounding box for empty shape")
        
        min_x = min(p.x for p in self.points)
        max_x = max(p.x for p in self.points)
        min_y = min(p.y for p in self.points)
        max_y = max(p.y for p in self.points)
        
        return (min_x, min_y, max_x, max_y)
    
    def width(self) -> float:
        """
        Calculate the width of the shape's bounding box.
        
        Returns:
            float: Width of the bounding box (max_x - min_x)
        """
        min_x, _, max_x, _ = self.bounding_box()
        return max_x - min_x
    
    def height(self) -> float:
        """
        Calculate the height of the shape's bounding box.
        
        Returns:
            float: Height of the bounding box (max_y - min_y)
        """
        _, min_y, _, max_y = self.bounding_box()
        return max_y - min_y
