"""
example_usage_triangle.py

Demonstration of Mesh class usage with the Triangle backend for various domains:

1. Simple polygon (unit square)
2. Circular domain
3. Polygon with circular hole
4. Composite domain: square minus two circles
"""
import numpy as np
import matplotlib.pyplot as plt
from mesh import Mesh


def run_example_1():
    """1. Simple polygon (unit square)"""
    domain = {
        'outer': {'type': 'polygon', 'points': [(0, 0), (1, 0), (1, 1), (0, 1)]}
    }
    mesh = Mesh(domain)
    pts, tris = mesh.generate(max_area=0.01)
    print('Example 1: Unit square')
    print(f'  Vertices: {len(pts)}, Triangles: {len(tris)}')
    mesh.plot(color='blue')


def run_example_2():
    """2. Circular domain"""
    # Circle approximated by 128 segments
    domain = {
        'outer': {
            'type': 'circle',
            'center': (0, 0),
            'radius': 1.0,
            'segments': 128
        }
    }
    mesh = Mesh(domain)
    pts, tris = mesh.generate(max_area=0.005)
    print('Example 2: Circle')
    print(f'  Vertices: {len(pts)}, Triangles: {len(tris)}')
    mesh.plot(color='green')


def run_example_3():
    """3. Polygon with circular hole"""
    domain = {
        'outer': {'type': 'polygon', 'points': [(0, 0), (3, 0), (3, 2), (0, 2)]},
        'holes': [
            {'type': 'circle', 'center': (1.5, 1), 'radius': 0.5, 'segments': 64}
        ]
    }
    mesh = Mesh(domain)
    pts, tris = mesh.generate(max_area=0.02)
    print('Example 3: Rectangle with circular hole')
    print(f'  Vertices: {len(pts)}, Triangles: {len(tris)}')
    mesh.plot(color='red')


def run_example_4():
    """4. Square minus two circular holes"""
    domain = {
        'outer': {'type': 'polygon', 'points': [(-2, -2), (2, -2), (2, 2), (-2, 2)]},
        'holes': [
            {'type': 'circle', 'center': (-1, 0), 'radius': 0.7, 'segments': 64},
            {'type': 'circle', 'center': (1, 0), 'radius': 0.7, 'segments': 64}
        ]
    }
    mesh = Mesh(domain)
    pts, tris = mesh.generate(max_area=0.02)
    print('Example 4: Square with two holes')
    print(f'  Vertices: {len(pts)}, Triangles: {len(tris)}')
    mesh.plot(color='purple')


if __name__ == '__main__':
    run_example_1()
    run_example_2()
    run_example_3()
    run_example_4()  
    plt.show()

