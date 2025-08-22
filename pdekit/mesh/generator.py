# pdekit/mesh/generator.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LinearRing
from shapely.ops import unary_union

try:
    import triangle  # pip install triangle
except Exception as e:
    raise ImportError(
        "The 'triangle' package is required. Install with `pip install triangle`."
    ) from e


@dataclass
class TriMesh:
    """Simple triangle mesh container."""
    vertices: np.ndarray     # (N, 2) float64
    triangles: np.ndarray    # (M, 3) int32 (indices into vertices)
    segments: np.ndarray | None = None  # (K, 2) int32 (boundary edges)

    # alias for Canvas.show_mesh() that expects elements
    @property
    def elements(self) -> List[List[Tuple[float, float]]]:
        tris = []
        V = self.vertices
        for i, j, k in self.triangles:
            tris.append([(float(V[i,0]), float(V[i,1])),
                         (float(V[j,0]), float(V[j,1])),
                         (float(V[k,0]), float(V[k,1])),
                         (float(V[i,0]), float(V[i,1]))])
        return tris
    
    @property
    def points(self):
        return self.vertices


def _ring_to_vertices_and_segments(ring: LinearRing,
                                   verts: List[Tuple[float, float]],
                                   segs: List[Tuple[int, int]]) -> None:
    # Shapely rings repeat the first vertex at the end — drop it
    coords = list(ring.coords)
    if len(coords) > 1 and coords[0] == coords[-1]:
        coords = coords[:-1]
    start = len(verts)
    verts.extend(coords)
    n = len(coords)
    for i in range(n):
        segs.append((start + i, start + ((i + 1) % n)))


def _polygon_to_pslg(poly: Polygon,
                     verts: List[Tuple[float, float]],
                     segs: List[Tuple[int, int]],
                     holes: List[Tuple[float, float]]) -> None:
    # Exterior boundary
    _ring_to_vertices_and_segments(poly.exterior, verts, segs)
    # Holes: add their rings as segments and supply one interior point each
    for interior in poly.interiors:
        _ring_to_vertices_and_segments(interior, verts, segs)
        hole_poly = Polygon(interior)
        p = hole_poly.representative_point()
        holes.append((float(p.x), float(p.y)))


def _geom_to_pslg(geom: Polygon | MultiPolygon) -> dict:
    """Build the Triangle PSLG dict from a shapely (Multi)Polygon."""
    if isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    elif isinstance(geom, Polygon):
        polys = [geom]
    else:
        raise TypeError("generate_mesh expects a shapely Polygon or MultiPolygon.")

    # Fix minor validity issues (self-touching boundaries, etc.)
    polys = [p.buffer(0) if not p.is_valid else p for p in polys]

    verts: List[Tuple[float, float]] = []
    segs: List[Tuple[int, int]] = []
    holes: List[Tuple[float, float]] = []

    for p in polys:
        if p.is_empty:
            continue
        _polygon_to_pslg(p, verts, segs, holes)

    if not verts or not segs:
        raise ValueError("Empty PSLG – the geometry has no boundary to mesh.")

    A = {
        "vertices": np.asarray(verts, dtype=np.float64),
        "segments": np.asarray(segs, dtype=np.int32),
    }
    if holes:
        A["holes"] = np.asarray(holes, dtype=np.float64)
    return A


def generate_mesh(geom,
                  max_area: float | None = None,
                  quiet: bool = True,
                  min_angle: float = 25.0,
                  quality: bool = True,
                  conforming_delaunay: bool = True,
                  max_steiner: int | None = None,
                  smooth_iters: int = 0) -> TriMesh:

    A = _geom_to_pslg(geom)

    opts = "p"                   # PSLG
    if quality:
        # include numeric min angle, Triangle uses 'qXX'
        opts += f"q{float(min_angle):.6g}"
    if max_area is not None:
        opts += f"a{float(max_area):.6g}"
    if conforming_delaunay:
        opts += "D"
    if quiet:
        opts += "Q"
    # NOTE: Triangle doesn’t have a “max steiner” count directly; you can ignore or
    #       use it to clamp smoothing, or just keep it for future logic.

    result = triangle.triangulate(A, opts)

    V = result.get("vertices")
    T = result.get("triangles")

    if V is None or T is None:
        raise RuntimeError("Triangle failed to return vertices/triangles.")

    mesh = TriMesh(
        vertices=np.asarray(V, dtype=np.float64),
        triangles=np.asarray(T, dtype=np.int32),
    )

    if smooth_iters and len(mesh.vertices) and len(mesh.triangles):
        mesh = _laplacian_smooth(mesh, iters=int(smooth_iters))

    return mesh


# -------- optional helper (only smoothing) --------
def _laplacian_smooth(mesh: TriMesh, iters: int = 1) -> TriMesh:
    V = mesh.vertices.copy()
    T = mesh.triangles

    # build adjacency and detect boundary vertices
    from collections import Counter
    edges = []
    for a, b, c in T:
        edges.extend([(a, b), (b, c), (c, a)])
    edges = [tuple(sorted(e)) for e in edges]
    counts = Counter(edges)
    boundary = set([i for e, c in counts.items() if c == 1 for i in e])

    nbrs = [[] for _ in range(len(V))]
    for a, b, c in T:
        nbrs[a] += [b, c]
        nbrs[b] += [a, c]
        nbrs[c] += [a, b]
    nbrs = [list(set(ns)) for ns in nbrs]

    for _ in range(iters):
        newV = V.copy()
        for i, ns in enumerate(nbrs):
            if i in boundary or not ns:
                continue
            newV[i] = V[ns].mean(axis=0)
        V = newV
    return TriMesh(vertices=V, triangles=T)



__all__ = ["TriMesh", "generate_mesh"]
