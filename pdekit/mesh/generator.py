# from __future__ import annotations

# import numpy as np
# from dataclasses import dataclass
# from shapely.geometry import Polygon as ShapelyPoly
# from shapely.geometry.polygon import orient

# # Optional: repair borderline polys
# try:
#     from shapely.validation import make_valid
# except Exception:
#     def make_valid(g):  # no-op fallback
#         return g

# # Triangle wrapper
# try:
#     import triangle as tr
# except Exception:
#     tr = None


# @dataclass
# class SimpleMesh:
#     # Each element is a closed triangle polyline: [(x,y), (x,y), (x,y), (x,y)]
#     elements: list[list[tuple[float, float]]]


# class MeshGenerator:
#     """
#     Triangulates polygons (with holes) using Jonathan Shewchuk's Triangle via the
#     'triangle' Python wrapper.
#     """

#     def __init__(self, min_angle: float = 25.0, max_area: float | None = None, quiet: bool = True):
#         self.min_angle = float(min_angle) if min_angle else None
#         self.max_area = float(max_area) if max_area else None
#         self.quiet = quiet

#     # ---------- Shapely -> Triangle PSLG ----------
#     def _poly_to_pslg(self, poly: ShapelyPoly, round_ndigits: int = 12) -> dict:
#         """Build a PSLG dict {'vertices','segments','holes'} for a single polygon."""
#         poly = orient(poly, sign=1.0)  # CCW exterior

#         verts: list[list[float]] = []
#         segs: list[tuple[int, int]] = []
#         holes: list[list[float]] = []
#         index: dict[tuple[float, float], int] = {}

#         def keyxy(x, y):
#             return (round(float(x), round_ndigits), round(float(y), round_ndigits))

#         def add_v(x, y):
#             k = keyxy(x, y)
#             i = index.get(k)
#             if i is None:
#                 i = len(verts)
#                 index[k] = i
#                 verts.append([float(x), float(y)])
#             return i

#         def add_ring(coords):
#             pts = list(coords)
#             if len(pts) > 1 and pts[0] == pts[-1]:
#                 pts = pts[:-1]
#             ids = [add_v(x, y) for x, y in pts]
#             n = len(ids)
#             segs.extend((ids[i], ids[(i + 1) % n]) for i in range(n))

#         # exterior
#         add_ring(poly.exterior.coords)
#         # holes
#         for interior in poly.interiors:
#             add_ring(interior.coords)
#             hp = ShapelyPoly(interior).representative_point()
#             holes.append([float(hp.x), float(hp.y)])

#         out = {
#             "vertices": np.asarray(verts, dtype=float),
#             "segments": np.asarray(segs, dtype=int),
#         }
#         if holes:
#             out["holes"] = np.asarray(holes, dtype=float)
#         return out

#     # ---------- Triangle call ----------
#     def _triangulate_pslg(self, pslg: dict) -> list[list[tuple[float, float]]]:
#         if tr is None:
#             raise RuntimeError("The 'triangle' package is not installed. Install with: pip install triangle")

#         opts = "p" + ("Q" if self.quiet else "")
#         if self.min_angle:
#             opts += f"q{self.min_angle}"
#         if self.max_area:
#             opts += f"a{self.max_area}"

#         T = tr.triangulate(pslg, opts)
#         if "triangles" not in T or len(T["triangles"]) == 0:
#             return []

#         V = np.asarray(T["vertices"], dtype=float)
#         tris = []
#         for a, b, c in np.asarray(T["triangles"], dtype=int):
#             pa, pb, pc = tuple(V[a]), tuple(V[b]), tuple(V[c])
#             tris.append([pa, pb, pc, pa])  # closed polyline
#         return tris

#     # ---------- Public API ----------
#     def from_geometries(self, geoms) -> SimpleMesh:
#         """
#         Accepts an iterable of Shapely geometries (Polygons or collections).
#         Returns a SimpleMesh that your Canvas.show_mesh can draw.
#         """
#         polys: list[ShapelyPoly] = []
#         for g in geoms:
#             if g is None or g.is_empty:
#                 continue
#             try:
#                 g = make_valid(g)
#             except Exception:
#                 pass

#             if isinstance(g, ShapelyPoly):
#                 polys.append(g)
#             elif hasattr(g, "geoms"):
#                 for gg in g.geoms:
#                     if isinstance(gg, ShapelyPoly):
#                         polys.append(gg)

#         all_tris: list[list[tuple[float, float]]] = []
#         for poly in polys:
#             pslg = self._poly_to_pslg(poly)
#             all_tris.extend(self._triangulate_pslg(pslg))

#         return SimpleMesh(elements=all_tris)


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


def generate_mesh(geom: Polygon | MultiPolygon,
                  max_area: float | None = None,
                  quality: bool = True,
                  quiet: bool = True) -> TriMesh:
    """
    Triangulate a shapely (Multi)Polygon using Shewchuk's Triangle.

    Parameters
    ----------
    geom : Polygon | MultiPolygon
        Domain to mesh (holes supported).
    max_area : float | None
        If given, Triangle switch 'a' is used to limit triangle area.
    quality : bool
        If True, apply Triangle 'q' quality refinement.
    quiet : bool
        If True, pass 'Q' to silence Triangle.

    Returns
    -------
    TriMesh
        vertices (N,2) and triangles (M,3).
    """
    A = _geom_to_pslg(geom)

    opts = "p"          # use PSLG (segments respected)
    if quality:
        opts += "q"
    if max_area is not None:
        opts += f"a{max_area}"
    if quiet:
        opts += "Q"

    result = triangle.triangulate(A, opts)

    V = result.get("vertices", None)
    T = result.get("triangles", None)
    S = result.get("segments", None)

    if V is None or T is None:
        raise RuntimeError("Triangle failed to return vertices/triangles.")

    return TriMesh(
        vertices=np.asarray(V, dtype=np.float64),
        triangles=np.asarray(T, dtype=np.int32),
        #segments=None if S is None else np.asarray(S, dtype=np.int32),
    )


__all__ = ["TriMesh", "generate_mesh"]
