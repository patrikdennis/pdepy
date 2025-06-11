import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QMenu,
    QToolButton, QWidget, QVBoxLayout
)
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtCore import Qt
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

    def on_generate_mesh(self):
        # Create matplotlib figure and axis if not already
        if self.canvas is None:
            fig, ax = plt.subplots()
            # Draw axes through origin
            ax.axhline(0, color='black', linewidth=2)
            ax.axvline(0, color='black', linewidth=2)
            # Grid
            ax.grid(True, which='both', linestyle='--', linewidth=0.5)
            # Set equal aspect
            ax.set_aspect('equal', 'box')

            # Embed canvas
            self.canvas = FigureCanvas(fig)
            self.toolbar = NavigationToolbar(self.canvas, self)
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
        print("Generated 2D coordinate system with matplotlib. Use toolbar to zoom/pan.")

    def on_refine_mesh(self):
        print("Refine Mesh selected")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

