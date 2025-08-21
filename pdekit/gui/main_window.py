import sys
from math import hypot, atan2, cos, sin
from PyQt6.QtWidgets import QMainWindow, QToolBar, QMenu, QToolButton, QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtGui import QAction, QFont
from shapely.geometry import Polygon as ShapelyPoly, Point as ShapelyPoint
from matplotlib.patches import Polygon as MplPolygon, Ellipse as MplEllipse, Rectangle as MplRectangle

from pdekit.canvas.canvas import Canvas
from pdekit.shapes.dialogs import EllipseDialog, RectangleDialog

from PyQt6.QtWidgets import QMessageBox


class MainWindow(QMainWindow):
    #CLOSE_THRESHOLD = 0.5  # tolerance for vertex/edge selection

    def __init__(self):
        super().__init__()
        container = QWidget()
        self.setCentralWidget(container)
        self.layout = QVBoxLayout(container)
        self.setWindowTitle('PDEKit')
        self.resize(800, 600)

        # Toolbar and menus
        toolbar = QToolBar("Navigation")
        font = QFont()
        font.setPointSize(14)
        toolbar.setFont(font)
        self.addToolBar(toolbar)

        # mesh button 
        mesh_btn = QToolButton(self)
        mesh_btn.setText("Mesh")
        mesh_btn.setFont(font)
        mesh_menu = QMenu(self)
        mesh_menu.setFont(font)
        
        # start canvas, generate mesh, refine mesh: mesh (parent) --> child
        canvas_act = QAction("Start Canvas", self)
        gen_act    = QAction("Generate Mesh", self)
        ref_act    = QAction("Refine Mesh", self)
        delete_act = QAction("Delete", self)
        domain_act = QAction("Domain", self)
        mesh_menu.addAction(canvas_act)
        mesh_menu.addAction(gen_act)
        mesh_menu.addAction(ref_act)
        
        # Draw menu: mesh (parent) --> draw (child)
        draw_menu = mesh_menu.addMenu("Draw")
        poly_act = draw_menu.addAction("Polygon")
        circle_act = draw_menu.addAction("Circle")
        rect_act = draw_menu.addAction("Rectangle")
        draw_menu.addAction(poly_act)
        draw_menu.addAction(circle_act)
        draw_menu.addAction(rect_act)
        
        mesh_btn.setMenu(mesh_menu)
        mesh_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup) if hasattr(QToolButton, 'ToolButtonPopupMode') else mesh_btn.setPopupMode(QToolButton.ToolButtonPopup)
        toolbar.addWidget(mesh_btn)

        canvas_act.triggered.connect(self.on_generate_canvas)
        gen_act.triggered.connect(self.on_generate_mesh)
        ref_act.triggered.connect(self.on_refine_mesh)
        poly_act.triggered.connect(self.on_draw_polygon)
        circle_act.triggered.connect(self.on_draw_circle)
        rect_act.triggered.connect(self.on_draw_rectangle)
        delete_act.triggered.connect(self.on_delete)
        domain_act.triggered.connect(self.on_domain)
    
        toolbar.addAction(delete_act)
        toolbar.addAction(domain_act)
        
        self.canvas = None
        
        # Central layout
        container = QWidget()
        self.setCentralWidget(container)
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def on_generate_canvas(self):
        if self.canvas is None:
            self.canvas = Canvas(self)
            self.layout.addWidget(self.canvas)
        self.canvas.initialize()

    def on_draw_polygon(self):
        if not self.canvas:
            self.on_generate_canvas()
        self.canvas.start_polygon_mode()

    def on_draw_circle(self):
        if not self.canvas:
            self.on_generate_canvas()
        self.canvas.start_circle_mode()

    def on_draw_rectangle(self):
        if not self.canvas:
            self.on_generate_canvas()
        self.canvas.start_rectangle_mode()
        
    def on_delete(self):
        if self.canvas:
            self.canvas.delete_selected()
    
    def on_domain(self):
        if self.canvas:
            self.canvas.domain_calculator()

    def on_generate_mesh(self):
        """
        Generate a mesh for the current domain and show it on the canvas.
        Uses Canvas.generate_and_show_mesh(), which keeps the mesh layer pinned
        (semi-transparent) so it stays visible while editing geometry.
        """
        # Read settings (fallbacks if you haven't set them on the window)
        max_area = getattr(self, "mesh_max_area", None)   # e.g. 0.01 for finer mesh
        quality  = getattr(self, "mesh_quality", True)    # Triangle quality switch

        try:
            mesh = self.canvas.generate_and_show_mesh(max_area=max_area, quality=quality)
            # Optionally keep a reference to the latest mesh
            self._last_mesh = mesh
            # Optional: tell the user some stats (uncomment if you like)
            # QMessageBox.information(self, "Mesh generated",
            #     f"Nodes: {len(mesh.points)}\nTriangles: {len(mesh.triangles)}")
        except ModuleNotFoundError as e:
            # Typically if the 'triangle' package isn't installed
            QMessageBox.critical(
                self, "Generate Mesh",
                "The meshing backend is missing.\n\n"
                "Install the Triangle Python wrapper:\n"
                "    pip install triangle\n\n"
                f"Details: {e}"
            )
        except ValueError as e:
            # Likely no valid domain on the canvas or geometry is empty
            QMessageBox.warning(self, "Generate Mesh", str(e))
        except Exception as e:
            # Catch-all to avoid crashing the app
            QMessageBox.critical(self, "Generate Mesh", f"Failed to generate mesh:\n{e}")


    def on_refine_mesh(self):
        refine_mesh()
