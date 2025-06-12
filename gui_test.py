import sys
from math import hypot
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QMenu,
    QToolButton, QWidget, QVBoxLayout, QSizePolicy
)
from PyQt6.QtGui import QAction, QFont, QCursor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

class MainWindow(QMainWindow):
    CLOSE_THRESHOLD = 0.5  # threshold to detect proximity

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Empty Window with Navigation Bar")
        self.resize(800, 600)

        # Toolbar setup
        font = QFont()
        font.setPointSize(14)
        toolbar = QToolBar("Navigation")
        toolbar.setFont(font)
        self.addToolBar(toolbar)

        # Mesh menu
        mesh_btn = QToolButton(self)
        mesh_btn.setText("Mesh")
        mesh_btn.setFont(font)
        mesh_menu = QMenu(self)
        mesh_menu.setFont(font)

        # Mesh actions
        gen_act = QAction("Generate Mesh", self)
        ref_act = QAction("Refine Mesh", self)
        mesh_menu.addAction(gen_act)
        mesh_menu.addAction(ref_act)

        # Draw submenu
        draw_menu = mesh_menu.addMenu("Draw")
        draw_menu.setFont(font)
        poly_act = QAction("Polygon", self)
        draw_menu.addAction(poly_act)

        mesh_btn.setMenu(mesh_menu)
        mesh_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(mesh_btn)

        # Connect actions
        gen_act.triggered.connect(self.on_generate_mesh)
        ref_act.triggered.connect(self.on_refine_mesh)
        poly_act.triggered.connect(self.on_draw_polygon)

        # Central widget
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.layout = QVBoxLayout(self.container)

        # State variables
        self.canvas = None
        self.drawing = False
        self.current_points = []
        self.current_artists = []
        self.polygons = []  # list of dicts with 'points' and 'artists'
        self.selected_idx = None
        self.mode = None  # 'move' or 'modify'
        self.dragging = False
        self.last_mouse = None
        self.modify_vidx = None
        self.context_event = None

    def on_generate_mesh(self):
        if not self.canvas:
            fig, ax = plt.subplots()
            ax.axhline(0, color='black', linewidth=2)
            ax.axvline(0, color='black', linewidth=2)
            ax.set_aspect('equal', 'box')
            ax.set_xlim(-10, 10)
            ax.set_ylim(-10, 10)

            self.canvas = FigureCanvas(fig)
            self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            fig.canvas.mpl_connect('button_press_event', self.on_click)
            fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
            fig.canvas.mpl_connect('button_release_event', self.on_release)

            nav = NavigationToolbar(self.canvas, self)
            self.layout.addWidget(nav)
            self.layout.addWidget(self.canvas)

        ax = self.canvas.figure.axes[0]
        ax.cla()
        ax.axhline(0, color='black', linewidth=2)
        ax.axvline(0, color='black', linewidth=2)
        ax.set_aspect('equal', 'box')
        ax.set_xlim(-10, 10)
        ax.set_ylim(-10, 10)

        # Clear existing polygons
        for poly in self.polygons:
            for art in poly['artists']:
                try:
                    art.remove()
                except:
                    pass
        self.polygons.clear()
        self.clear_current()
        self.selected_idx = None
        self.mode = None
        self.canvas.draw()
        print("Mesh generated.")

    def on_draw_polygon(self):
        if not self.canvas:
            self.on_generate_mesh()
        self.drawing = True
        self.clear_current()
        self.selected_idx = None
        self.redraw_polygons()
        print("Polygon draw mode activated.")

    def on_refine_mesh(self):
        print("Refine Mesh selected")

    def on_click(self, event):
        ax = event.inaxes
        if not ax:
            return
        # Drawing mode: left-click
        if self.drawing and event.button == 1:
            x, y = event.xdata, event.ydata
            if len(self.current_points) >= 3 and hypot(x - self.current_points[0][0], y - self.current_points[0][1]) <= self.CLOSE_THRESHOLD:
                # Close polygon
                self.current_points.append(self.current_points[0])
                self.draw_current()
                self.polygons.append({
                    'points': list(self.current_points),
                    'artists': list(self.current_artists)
                })
                self.clear_current()
                self.drawing = False
                print("Polygon closed.")
            else:
                self.current_points.append((x, y))
                self.draw_current()
            return
        # Context menu: right-click
        if not self.drawing and event.button == 3:
            for idx, poly in enumerate(self.polygons):
                for px, py in poly['points']:
                    if hypot(event.xdata - px, event.ydata - py) <= self.CLOSE_THRESHOLD:
                        self.selected_idx = idx
                        self.context_event = event
                        self.highlight(idx)
                        self.show_context_menu()
                        return

    def show_context_menu(self):
        menu = QMenu(self)
        move_act = QAction("Move", self)
        mod_act = QAction("Modify", self)
        del_act = QAction("Delete", self)
        menu.addAction(move_act)
        menu.addAction(mod_act)
        menu.addAction(del_act)
        move_act.triggered.connect(self.start_move)
        mod_act.triggered.connect(self.start_modify)
        del_act.triggered.connect(self.start_delete)
        menu.exec(QCursor.pos())

    def start_move(self):
        self.mode = 'move'
        self.dragging = True
        x0, y0 = self.context_event.xdata, self.context_event.ydata
        self.last_mouse = (x0, y0)
        print("Move mode activated.")

    def start_modify(self):
        if self.context_event and self.selected_idx is not None:
            x0, y0 = self.context_event.xdata, self.context_event.ydata
            points = self.polygons[self.selected_idx]['points']
            dists = [hypot(px - x0, py - y0) for px, py in points]
            self.modify_vidx = dists.index(min(dists))
            self.mode = 'modify'
            self.dragging = True
            self.last_mouse = (x0, y0)
            print(f"Modify mode activated on vertex {self.modify_vidx}.")
        else:
            print("Modify mode could not activate.")

    def start_delete(self):
        idx = self.selected_idx
        if idx is not None:
            for art in self.polygons[idx]['artists']:
                try:
                    art.remove()
                except:
                    pass
            self.polygons.pop(idx)
            self.selected_idx = None
            self.redraw_polygons()

    def draw_current(self):
        self.clear_current_artists()
        ax = self.canvas.figure.axes[0]
        xs, ys = zip(*self.current_points)
        sc = ax.scatter(xs, ys, c='blue')
        ln, = ax.plot(xs, ys, marker='o', c='blue')
        self.current_artists = [sc, ln]
        self.canvas.draw()

    def clear_current(self):
        self.current_points.clear()
        self.clear_current_artists()

    def clear_current_artists(self):
        for art in self.current_artists:
            try:
                art.remove()
            except:
                pass
        self.current_artists.clear()

    def highlight(self, idx):
        """
        Highlight the polygon at given index by setting it as selected and redrawing.
        """
        self.selected_idx = idx
        self.redraw_polygons()

    def unhighlight(self):
        """
        Clear any polygon selection.
        """
        self.selected_idx = None
        self.redraw_polygons()

        for art in self.current_artists:
            try:
                art.remove()
            except:
                pass
        self.current_artists.clear()

    def redraw_polygons(self):
        ax = self.canvas.figure.axes[0]
        ax.cla()
        ax.axhline(0, color='black', linewidth=2)
        ax.axvline(0, color='black', linewidth=2)
        ax.set_aspect('equal', 'box')
        ax.set_xlim(-10, 10)
        ax.set_ylim(-10, 10)
        for idx, poly in enumerate(self.polygons):
            pts = poly['points']
            xs, ys = zip(*pts)
            color = 'green' if idx == self.selected_idx else 'blue'
            sc = ax.scatter(xs, ys, c=color)
            ln, = ax.plot(xs, ys, marker='o', c=color)
            poly['artists'] = [sc, ln]
        self.canvas.draw()

    def on_motion(self, event):
        if not self.dragging or self.selected_idx is None:
            return
        x, y = event.xdata, event.ydata
        dx = x - self.last_mouse[0] if self.last_mouse else 0
        dy = y - self.last_mouse[1] if self.last_mouse else 0
        self.last_mouse = (x, y)
        poly = self.polygons[self.selected_idx]
        if self.mode == 'move':
            pts = [(px + dx, py + dy) for px, py in poly['points']]
            poly['points'] = pts
        elif self.mode == 'modify' and self.modify_vidx is not None:
            pts = list(poly['points'])
            vidx = self.modify_vidx
            px, py = pts[vidx]
            pts[vidx] = (px + dx, py + dy)
            if vidx == 0:
                pts[-1] = pts[0]
            elif vidx == len(pts) - 1:
                pts[0] = pts[-1]
            poly['points'] = pts
        else:
            return
        self.redraw_polygons()

    def on_release(self, event):
        if self.dragging:
            self.dragging = False
            self.mode = None
            self.modify_vidx = None
            self.last_mouse = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

