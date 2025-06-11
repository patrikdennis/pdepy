import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QMenu,
    QToolButton, QWidget, QVBoxLayout, QSizePolicy
)
from PyQt6.QtGui import QAction, QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

class MainWindow(QMainWindow):
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
        generate_action = QAction("Generate Mesh", self)
        refine_action = QAction("Refine Mesh", self)
        mesh_menu.addAction(generate_action)
        mesh_menu.addAction(refine_action)
        generate_action.triggered.connect(self.on_generate_mesh)
        refine_action.triggered.connect(self.on_refine_mesh)
        mesh_button.setMenu(mesh_menu)
        mesh_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        nav_bar.addWidget(mesh_button)

        # Central container
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.layout = QVBoxLayout(self.container)
        self.canvas = None
        self.toolbar = None

    def zoom_callback(self, event):
        # Zoom on scroll event
        ax = event.inaxes
        if ax is None:
            return
        base_scale = 1.1
        # determine scale factor
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
        # Create matplotlib figure and axis if not already
        if self.canvas is None:
            fig, ax = plt.subplots()
            # Draw axes through origin
            ax.axhline(0, color='black', linewidth=2)
            ax.axvline(0, color='black', linewidth=2)
            # Grid
            ax.grid(True, which='both', linestyle='--', linewidth=0.5)
            # Equal aspect
            ax.set_aspect('equal', 'box')

            # Embed canvas
            self.canvas = FigureCanvas(fig)
            self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.canvas.updateGeometry()
            # Connect scroll event for zoom
            fig.canvas.mpl_connect('scroll_event', self.zoom_callback)

            # Navigation toolbar
            self.toolbar = NavigationToolbar(self.canvas, self)
            self.toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            # Add to layout
            self.layout.addWidget(self.toolbar)
            self.layout.addWidget(self.canvas)
        else:
            # Clear and redraw
            ax = self.canvas.figure.axes[0]
            ax.cla()
            ax.axhline(0, color='black', linewidth=2)
            ax.axvline(0, color='black', linewidth=2)
            ax.grid(True, which='both', linestyle='--', linewidth=0.5)
            ax.set_aspect('equal', 'box')
            self.canvas.draw()
        print("Generated 2D coordinate system with matplotlib. Scroll to zoom, drag to pan.")

    def on_refine_mesh(self):
        print("Refine Mesh selected")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

