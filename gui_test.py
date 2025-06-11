import sys
from math import hypot
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QMenu,
    QToolButton, QWidget, QVBoxLayout, QSizePolicy
)
from PyQt6.QtGui import QAction, QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

class MainWindow(QMainWindow):
    CLOSE_THRESHOLD = 0.5  # distance threshold in data coords to close polygon

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Empty Window with Navigation Bar")
        self.resize(800, 600)

        # Define larger font
        font = QFont()
        font.setPointSize(14)

        # Navigation toolbar
        nav_bar = QToolBar("Navigation")
        nav_bar.setFont(font)
        self.addToolBar(nav_bar)

        # Mesh button with submenu
        mesh_button = QToolButton(self)
        mesh_button.setText("Mesh")
        mesh_button.setFont(font)
        mesh_menu = QMenu(self)
        mesh_menu.setFont(font)

        # Mesh submenu actions
        generate_action = QAction("Generate Mesh", self)
        refine_action = QAction("Refine Mesh", self)
        mesh_menu.addAction(generate_action)
        mesh_menu.addAction(refine_action)

        # Draw submenu
        draw_menu = mesh_menu.addMenu("Draw")
        draw_menu.setFont(font)
        polygon_action = QAction("Polygon", self)
        draw_menu.addAction(polygon_action)

        # Connect actions
        generate_action.triggered.connect(self.on_generate_mesh)
        refine_action.triggered.connect(self.on_refine_mesh)
        polygon_action.triggered.connect(self.on_draw_polygon)

        mesh_button.setMenu(mesh_menu)
        mesh_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        nav_bar.addWidget(mesh_button)

        # Central container
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.layout = QVBoxLayout(self.container)

        # State
        self.canvas = None
        self.toolbar = None
        self.poly_points = []
        self.poly_artists = []
        self.drawing = False  # whether polygon drawing is active

    def zoom_callback(self, event):
        ax = event.inaxes
        if ax is None:
            return
        base_scale = 1.1
        scale_factor = base_scale if event.button == 'up' else 1/base_scale
        xdata, ydata = event.xdata, event.ydata
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        new_width = (xlim[1] - xlim[0]) * scale_factor
        new_height = (ylim[1] - ylim[0]) * scale_factor
        relx = (xdata - xlim[0]) / (xlim[1] - xlim[0])
        rely = (ydata - ylim[0]) / (ylim[1] - ylim[0])
        ax.set_xlim([xdata - new_width * relx, xdata + new_width * (1-relx)])
        ax.set_ylim([ydata - new_height * rely, ydata + new_height * (1-rely)])
        self.canvas.draw_idle()

    def on_generate_mesh(self):
        # Create axes if needed
        if self.canvas is None:
            fig, ax = plt.subplots()
            ax.axhline(0, color='black', linewidth=2)
            ax.axvline(0, color='black', linewidth=2)
            ax.set_aspect('equal', 'box')
            ax.set_xlim(-10, 10)
            ax.set_ylim(-10, 10)

            # Embed canvas and toolbar
            self.canvas = FigureCanvas(fig)
            self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.canvas.updateGeometry()
            fig.canvas.mpl_connect('scroll_event', self.zoom_callback)
            fig.canvas.mpl_connect('button_press_event', self.on_click)

            self.toolbar = NavigationToolbar(self.canvas, self)
            self.toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.layout.addWidget(self.toolbar)
            self.layout.addWidget(self.canvas)
        else:
            # Reset axes
            ax = self.canvas.figure.axes[0]
            ax.cla()
            ax.axhline(0, color='black', linewidth=2)
            ax.axvline(0, color='black', linewidth=2)
            ax.set_aspect('equal', 'box')
            ax.set_xlim(-10, 10)
            ax.set_ylim(-10, 10)
            # Clear drawing state
            self.poly_points.clear()
            for artist in self.poly_artists:
                artist.remove()
            self.poly_artists.clear()
            self.canvas.draw()
        self.drawing = True
        print("Generated coordinate axes. Scroll to zoom, drag to pan. Ready to draw or refine.")

    def on_draw_polygon(self):
        # Start polygon drawing mode
        if self.canvas is None:
            self.on_generate_mesh()
        else:
            # Clear any previous polygon
            ax = self.canvas.figure.axes[0]
            for artist in self.poly_artists:
                artist.remove()
            self.poly_artists.clear()
            self.poly_points.clear()
            self.canvas.draw()
        self.drawing = True
        print("Polygon draw mode activated. Click to add points. Click near start to close.")

    def on_click(self, event):
        if not self.drawing:
            return
        ax = event.inaxes
        if ax is None or event.button != 1:
            return
        x, y = event.xdata, event.ydata
        # Close polygon if near start and enough points
        if len(self.poly_points) >= 3:
            x0, y0 = self.poly_points[0]
            if hypot(x - x0, y - y0) <= self.CLOSE_THRESHOLD:
                self.poly_points.append((x0, y0))
                self._draw_polygon(ax)
                self.drawing = False
                print("Polygon closed. Returning to view mode.")
                return
        # Add vertex
        self.poly_points.append((x, y))
        self._draw_polygon(ax)

    def _draw_polygon(self, ax):
        # Remove old artists
        for artist in self.poly_artists:
            artist.remove()
        self.poly_artists.clear()
        xs, ys = zip(*self.poly_points)
        scatter = ax.scatter(xs, ys, c='blue')
        line, = ax.plot(xs, ys, linestyle='-', marker='o', color='blue')
        self.poly_artists.extend([scatter, line])
        self.canvas.draw()

    def on_refine_mesh(self):
        print("Refine Mesh selected")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

