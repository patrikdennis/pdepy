"""mesh.py

2-D unstructured mesh generator using the 'triangle' package for PSLGs,
supporting polygons, circles, holes, and boolean subtraction.

* **Domain** – an 'outer' polygon or circle, plus optional 'holes' (polygons or circles).
  Circles are approximated by many segments.
* **Dependencies** – ``numpy``, ``matplotlib``, and ``triangle`` (a Python
  wrapper around Jonathan Shewchuk's Triangle).

Usage example
-------------
>>> from mesh import Mesh
>>> # Outer square minus a circular hole
>>> domain = {
...     'outer': {'type': 'polygon', 'points': [(0,0),(2,0),(2,2),(0,2)]},
...     'holes': [
...         {'type': 'circle', 'center': (1,1), 'radius': 0.5, 'segments': 64}
...     ]
... }
>>> mesh = Mesh(domain)
>>> pts, tris = mesh.generate(max_area=0.005)
>>> mesh.plot()

"""
from typing import Tuple, Union, List, Dict
import numpy as np
import matplotlib.pyplot as plt
import triangle as tr

DomainPrimitive = Dict[str, Union[str, List[Tuple[float,float]], Tuple[float,float], float, int]]

class Mesh:
    """Mesh generator for planar straight-line graphs via Triangle.
Support 'outer' as polygon or circle, plus optional 'holes'."""

    def __init__(self, spec: Dict):
        """
        Parameters
        ----------
        spec : dict with keys:
            'outer': DomainPrimitive for outer boundary (polygon or circle)
            'holes': optional list of DomainPrimitive for holes (polygon or circle)
        """
        if 'outer' not in spec:
            raise ValueError("spec must contain an 'outer' domain")
        otype = spec['outer'].get('type')
        if otype not in ('polygon', 'circle'):
            raise ValueError("spec['outer']['type'] must be 'polygon' or 'circle'")
        self.outer = spec['outer']
        self.holes = spec.get('holes', [])

        # Internal storage
        self.points: np.ndarray = np.empty((0,2))
        self.triangles: np.ndarray = np.empty((0,3), dtype=int)

    def _discretize_circle(self, center: Tuple[float,float], r: float, segments: int) -> np.ndarray:
        theta = np.linspace(0, 2*np.pi, segments, endpoint=False)
        pts = np.vstack([center[0] + r*np.cos(theta), center[1] + r*np.sin(theta)]).T
        return pts

    def generate(self, max_area: float = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build the mesh.

        Parameters
        ----------
        max_area : float, optional
            Maximum triangle area. If None, no area constraint.

        Returns
        -------
        points : (M,2) float array of node coordinates
        triangles : (K,3) int array of indices into points
        """
        # --- Assemble PSLG
        vertices: List[Tuple[float,float]] = []
        segments: List[List[int]] = []
        holes_pts: List[Tuple[float,float]] = []

        def add_loop(pts_arr: np.ndarray) -> None:
            start = len(vertices)
            for p in pts_arr:
                vertices.append((float(p[0]), float(p[1])))
            n = len(pts_arr)
            for i in range(n):
                segments.append([start + i, start + (i + 1) % n])

        # --- Outer boundary ---
        o = self.outer
        if o['type'] == 'polygon':
            pts = np.asarray(o['points'], float)
            if pts.shape[0] < 3:
                raise ValueError("Polygon outer boundary needs at least 3 points")
            if not np.allclose(pts[0], pts[-1]):
                pts = np.vstack([pts, pts[0]])
            add_loop(pts[:-1])
        else:  # circle
            center = tuple(o['center'])
            r = float(o['radius'])
            segs = int(o.get('segments', 64))
            pts = self._discretize_circle(center, r, segs)
            add_loop(pts)

        # --- Holes ---
        for hole in self.holes:
            htype = hole.get('type')
            if htype == 'polygon':
                pts_h = np.asarray(hole['points'], float)
                if pts_h.shape[0] < 3:
                    raise ValueError("Polygon hole needs at least 3 points")
                if not np.allclose(pts_h[0], pts_h[-1]):
                    pts_h = np.vstack([pts_h, pts_h[0]])
                c = pts_h[:-1].mean(axis=0)
                holes_pts.append((float(c[0]), float(c[1])))
                add_loop(pts_h[:-1])
            elif htype == 'circle':
                center = tuple(hole['center'])
                r = float(hole['radius'])
                segs = int(hole.get('segments', 64))
                pts_h = self._discretize_circle(center, r, segs)
                holes_pts.append((float(center[0]), float(center[1])))
                add_loop(pts_h)
            else:
                raise ValueError(f"Unknown hole type {htype}")

        mesh_dict: Dict[str, np.ndarray] = {
            'vertices': np.array(vertices),
            'segments': np.array(segments, dtype=int)
        }
        if holes_pts:
            mesh_dict['holes'] = np.array(holes_pts, dtype=float)

        # --- Triangle options ---
        opts = 'p'
        if max_area is not None:
            opts += f'a{max_area}'
        opts += 'q'

        tri = tr.triangulate(mesh_dict, opts)
        self.points = tri['vertices']
        self.triangles = tri['triangles']
        return self.points, self.triangles

    def plot(self, ax: plt.Axes = None, show: bool = True, **kwargs) -> None:
        """Visualize the mesh with matplotlib triplot."""
        if self.points.size == 0 or self.triangles.size == 0:
            raise RuntimeError("Generate mesh first: call `.generate()`")
        own_fig = False
        if ax is None:
            fig, ax = plt.subplots()
            own_fig = True
        ax.triplot(self.points[:,0], self.points[:,1], self.triangles, **kwargs)
        ax.set_aspect('equal')
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title('Triangle-generated mesh')
        if show and own_fig:
            plt.show()

    plot_mesh = plot

