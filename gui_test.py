import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QToolBar, QMenu, QToolButton
from PyQt6.QtGui import QAction, QFont

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Empty Window with Navigation Bar")
        # Make window larger
        self.resize(800, 600)

        # Define a larger font
        font = QFont()
        font.setPointSize(14)

        # Create a navigation toolbar
        nav_bar = QToolBar("Navigation")
        nav_bar.setFont(font)
        # Optionally increase toolbar icon height
        nav_bar.setIconSize(nav_bar.iconSize().expandedTo(nav_bar.iconSize()))
        self.addToolBar(nav_bar)

        # Create a 'Mesh' tool button with suboptions
        mesh_button = QToolButton(self)
        mesh_button.setText("Mesh")
        mesh_button.setFont(font)
        mesh_menu = QMenu(self)
        mesh_menu.setFont(font)

        # Suboptions
        generate_action = QAction("Generate Mesh", self)
        refine_action = QAction("Refine Mesh", self)
        mesh_menu.addAction(generate_action)
        mesh_menu.addAction(refine_action)

        # Connect actions
        generate_action.triggered.connect(self.on_generate_mesh)
        refine_action.triggered.connect(self.on_refine_mesh)

        mesh_button.setMenu(mesh_menu)
        # Use InstantPopup mode so clicking the button shows the menu immediately
        mesh_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        nav_bar.addWidget(mesh_button)

    def on_generate_mesh(self):
        # Placeholder for Generate Mesh
        print("Generate Mesh selected")

    def on_refine_mesh(self):
        # Placeholder for Refine Mesh
        print("Refine Mesh selected")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

