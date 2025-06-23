import sys
from math import hypot, atan2, cos, sin
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QMenu,
    QToolButton, QWidget, QVBoxLayout, QSizePolicy,
    QDialog, QFormLayout, QLabel, QLineEdit, QDialogButtonBox
)
from PyQt6.QtGui import QAction, QFont
from shapely.geometry import Polygon as ShapelyPoly, Point as ShapelyPoint
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
import matplotlib.pyplot as plt
from matplotlib.patches import (
    Polygon as MplPolygon,
    Ellipse as MplEllipse,
    Rectangle as MplRectangle
)

plt.style.use("dark_background")



# --- Custom dialogs for combined input ---
class EllipseDialog(QDialog):
    def __init__(self, parent, xc, yc, rx, ry):
        super().__init__(parent)
        self.setWindowTitle("Edit Ellipse")
        layout = QFormLayout(self)
        self.h_edit = QLineEdit(str(xc))
        self.k_edit = QLineEdit(str(yc))
        self.a_edit = QLineEdit(str(rx))
        self.b_edit = QLineEdit(str(ry))
        layout.addRow(QLabel("Center x-coordinate:"), self.h_edit)
        layout.addRow(QLabel("Center y-coordinate:"), self.k_edit)
        layout.addRow(QLabel("Semi-major axis a:"), self.a_edit)
        layout.addRow(QLabel("Semi-minor axis b:"), self.b_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def getValues(self):
        return (float(self.h_edit.text()),
                float(self.k_edit.text()),
                float(self.a_edit.text()),
                float(self.b_edit.text()))

class RectangleDialog(QDialog):
    def __init__(self, parent, x0, y0, x1, y1):
        super().__init__(parent)
        self.setWindowTitle("Edit Rectangle")
        layout = QFormLayout(self)
        self.x1_edit = QLineEdit(str(x0))
        self.y1_edit = QLineEdit(str(y0))
        self.x2_edit = QLineEdit(str(x1))
        self.y2_edit = QLineEdit(str(y1))
        layout.addRow(QLabel("x1 (bottom-left x):"), self.x1_edit)
        layout.addRow(QLabel("y1 (bottom-left y):"), self.y1_edit)
        layout.addRow(QLabel("x2 (top-right x):"), self.x2_edit)
        layout.addRow(QLabel("y2 (top-right y):"), self.y2_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def getValues(self):
        return (float(self.x1_edit.text()),
                float(self.y1_edit.text()),
                float(self.x2_edit.text()),
                float(self.y2_edit.text()))


class MainWindow(QMainWindow):
    CLOSE_THRESHOLD = 0.5  # tolerance for vertex/edge selection

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDE Toolbox")
        self.resize(800, 600)

        # Toolbar and menus
        toolbar = QToolBar("Navigation")
        font = QFont()
        font.setPointSize(14)
        toolbar.setFont(font)
        self.addToolBar(toolbar)

        mesh_btn = QToolButton(self)
        mesh_btn.setText("Mesh")
        mesh_btn.setFont(font)
        mesh_menu = QMenu(self)
        mesh_menu.setFont(font)

        canvas_act = QAction("Start Canvas", self)
        gen_act    = QAction("Generate Mesh", self)
        ref_act    = QAction("Refine Mesh", self)
        mesh_menu.addAction(canvas_act)
        mesh_menu.addAction(gen_act)
        mesh_menu.addAction(ref_act)

        draw_menu = mesh_menu.addMenu("Draw")
        poly_act   = QAction("Polygon", self)
        circle_act = QAction("Circle", self)
        rect_act   = QAction("Rectangle", self)
        draw_menu.addAction(poly_act)
        draw_menu.addAction(circle_act)
        draw_menu.addAction(rect_act)

        mesh_btn.setMenu(mesh_menu)
        mesh_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup) if hasattr(QToolButton, 'ToolButtonPopupMode') else mesh_btn.setPopupMode(QToolButton.ToolButtonPopup)
        toolbar.addWidget(mesh_btn)

        # Connect menu actions
        canvas_act.triggered.connect(self.on_generate_canvas)
        gen_act.triggered.connect(self.on_generate_mesh)
        ref_act.triggered.connect(self.on_refine_mesh)
        poly_act.triggered.connect(self.on_draw_polygon)
        circle_act.triggered.connect(self.on_draw_circle)
        rect_act.triggered.connect(self.on_draw_rectangle)

        # State
        self.canvas = None
        self.drawing = False
        self.draw_type = None   # 'polygon', 'circle', 'rectangle'
        self.current_points = []
        self.shapes = []        # list of Matplotlib Patch objects
        self.current_artists = []  # preview patches
        self.selected_idx = None
        self.mode = None        # 'move', 'modify_poly', 'modify_ellipse', 'modify_rect'
        self.dragging = False
        self.modify_vidx = None
        self.modify_corner = None
        self.last_mouse = None
        self.circle_center = None
        self.rect_start = None

        # Central widget layout
        container = QWidget()
        self.setCentralWidget(container)
        self.layout = QVBoxLayout(container)

    def on_generate_canvas(self):
        # Initialize or clear the canvas
        if not self.canvas:
            fig, ax = plt.subplots()
            ax.axhline(0, color='white', linewidth=0.5)
            ax.axvline(0, color='white', linewidth=0.5)
            ax.set_aspect('equal', 'box')
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)

            self.canvas = FigureCanvas(fig)
            self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            fig.canvas.mpl_connect('button_press_event', self.on_click)
            fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
            fig.canvas.mpl_connect('button_release_event', self.on_release)
            fig.canvas.mpl_connect('scroll_event', self.zoom_callback)

            #nav = NavigationToolbar(self.canvas, self)
            self.toolbar = NavigationToolbar(self.canvas, self)

            self.layout.addWidget(self.toolbar)
            self.layout.addWidget(self.canvas)

        ax = self.canvas.figure.axes[0]
        ax.cla()
        ax.axhline(0, color='white', linewidth=0.5)
        ax.axvline(0, color='white', linewidth=0.5)
        ax.set_aspect('equal', 'box')
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)

        # Clear stored shapes
        for patch in self.shapes:
            try:
                patch.remove()
            except:
                pass
        self.shapes.clear()
        self.current_points.clear()
        self.current_artists.clear()
        self.selected_idx = None
        self.mode = None
        self.drawing = False
        self.draw_type = None
        self.circle_center = None
        self.rect_start = None
        self.canvas.draw()

    def on_generate_mesh(self):
        print("Generate mesh selected.")

    def on_refine_mesh(self):
        print("Refine Mesh selected.")

    def on_draw_polygon(self):
        
        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
            self.toolbar.pan()

        if not self.canvas:
            self.on_generate_canvas()
            
        self.drawing = True
        self.draw_type = 'polygon'
        self.current_points.clear()
        self.current_artists.clear()
        self.selected_idx = None
        self.redraw_shapes()
        print("Polygon draw mode activated.")

    def on_draw_circle(self):
        
        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
            self.toolbar.pan()

        if not self.canvas:
            self.on_generate_canvas()
            
        self.drawing = True
        self.draw_type = 'circle'
        self.circle_center = None
        self.current_artists.clear()
        self.selected_idx = None
        self.redraw_shapes()
        print("Circle draw mode activated.")

    def on_draw_rectangle(self):
        
        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
            self.toolbar.pan()

        if not self.canvas:
            self.on_generate_canvas()
            
        self.drawing = True
        self.draw_type = 'rectangle'
        self.rect_start = None
        self.current_artists.clear()
        self.selected_idx = None
        self.redraw_shapes()
        print("Rectangle draw mode activated.")

    def zoom_callback(self, event):
        ax = event.inaxes
        if not ax:
            return
        base_scale = 1.1 if event.button == 'up' else 1/1.1
        xdata, ydata = event.xdata, event.ydata
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        new_w = (xlim[1] - xlim[0]) * base_scale
        new_h = (ylim[1] - ylim[0]) * base_scale
        relx = (xdata - xlim[0]) / (xlim[1] - xlim[0])
        rely = (ydata - ylim[0]) / (ylim[1] - ylim[0])
        ax.set_xlim([xdata - new_w * relx, xdata + new_w * (1 - relx)])
        ax.set_ylim([ydata - new_h * rely, ydata + new_h * (1 - rely)])
        self.canvas.draw_idle()

    def on_click(self, event):
        ax = event.inaxes
        if not ax:
            return
        x, y = event.xdata, event.ydata
        
        # ── double-click to edit ellipse or rectangle ──
        if getattr(event, 'dblclick', False) and not self.drawing and event.button == 1:
            for idx, patch in enumerate(self.shapes):
                # edit ellipse/circle
                if isinstance(patch, MplEllipse):
                    xc, yc = patch.center
                    rx, ry = patch.width/2, patch.height/2
                    if ((x-xc)/rx)**2 + ((y-yc)/ry)**2 <= 1:
                        dlg = EllipseDialog(self, xc, yc, rx, ry)
                        if dlg.exec() == QDialog.DialogCode.Accepted:
                            try:
                                h, k, a, b = dlg.getValues()
                                patch.center = (h, k)
                                patch.width  = 2 * a
                                patch.height = 2 * b
                                self.redraw_shapes()
                            except Exception as e:
                                print(f"Invalid ellipse parameters: {e}")
                        return

                # edit rectangle
                if isinstance(patch, MplRectangle):
                    x0, y0 = patch.get_x(), patch.get_y()
                    w,  h  = patch.get_width(), patch.get_height()
                    if x0 <= x <= x0+w and y0 <= y <= y0+h:
                        dlg = RectangleDialog(self, x0, y0, x0+w, y0+h)
                        if dlg.exec() == QDialog.DialogCode.Accepted:
                            try:
                                x1, y1, x2, y2 = dlg.getValues()
                                patch.set_x(min(x1, x2))
                                patch.set_y(min(y1, y2))
                                patch.set_width(abs(x2 - x1))
                                patch.set_height(abs(y2 - y1))
                                self.redraw_shapes()
                            except Exception as e:
                                print(f"Invalid rectangle parameters: {e}")
                        return

        # Polygon drawing
        if self.drawing and self.draw_type == 'polygon' and event.button == 1:
            if len(self.current_points) >= 3 and hypot(x - self.current_points[0][0], y - self.current_points[0][1]) <= self.CLOSE_THRESHOLD:
                # close polygon
                self.current_points.append(self.current_points[0])
                self.draw_current()
                poly = MplPolygon(self.current_points, closed=True)
                self.shapes.append(poly)
                self.current_points.clear()
                self.drawing = False
                self.draw_type = None
                self.redraw_shapes()
                print("Polygon closed.")
            else:
                self.current_points.append((x, y))
                self.draw_current()
            return

        # Circle drawing start
        if self.drawing and self.draw_type == 'circle' and event.button == 1:
            self.circle_center = (x, y)
            return

        # Rectangle drawing start
        if self.drawing and self.draw_type == 'rectangle' and event.button == 1:
            if self.rect_start is None:
                self.rect_start = (x, y)
            return

        # Select/move/modify existing shapes
        if not self.drawing and event.button == 1:
            # check polygons
            for idx, patch in enumerate(self.shapes):
                if isinstance(patch, MplPolygon):
                    verts = patch.get_xy()[:-1]
                    dists = [hypot(px - x, py - y) for px, py in verts]
                    if min(dists) <= self.CLOSE_THRESHOLD:
                        # modify polygon vertex
                        self.selected_idx = idx
                        self.modify_vidx = dists.index(min(dists))
                        self.mode = 'modify_poly'
                        self.dragging = True
                        self.last_mouse = (x, y)
                        return
                    # move polygon
                    if ShapelyPoly(patch.get_xy()).contains(ShapelyPoint(x, y)):
                        self.selected_idx = idx
                        self.mode = 'move'
                        self.dragging = True
                        self.last_mouse = (x, y)
                        return
                # check ellipses
                if isinstance(patch, MplEllipse):
                    xc, yc = patch.center
                    rx, ry = patch.width / 2, patch.height / 2
                    # boundary: nearest point
                    angle = atan2(y - yc, x - xc)
                    bx = xc + rx * cos(angle)
                    by = yc + ry * sin(angle)
                    if hypot(x - bx, y - by) <= self.CLOSE_THRESHOLD:
                        # modify ellipse boundary
                        self.selected_idx = idx
                        self.mode = 'modify_ellipse'
                        self.dragging = True
                        return
                    # interior: move ellipse
                    if rx and ry and ((x - xc)/rx)**2 + ((y - yc)/ry)**2 <= 1:
                        self.selected_idx = idx
                        self.mode = 'move'
                        self.dragging = True
                        self.last_mouse = (x, y)
                        return
                # check rectangles
                if isinstance(patch, MplRectangle):
                    x0, y0 = patch.get_x(), patch.get_y()
                    w, h = patch.get_width(), patch.get_height()
                    corners = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
                    dists = [hypot(cx - x, cy - y) for cx, cy in corners]
                    if min(dists) <= self.CLOSE_THRESHOLD:
                        # modify rectangle corner
                        self.selected_idx = idx
                        self.modify_corner = dists.index(min(dists))
                        self.mode = 'modify_rect'
                        self.dragging = True
                        return
                    # move rectangle
                    if x0 <= x <= x0 + w and y0 <= y <= y0 + h:
                        self.selected_idx = idx
                        self.mode = 'move'
                        self.dragging = True
                        self.last_mouse = (x, y)
                        return

    def on_motion(self, event):
        ax = event.inaxes or self.canvas.figure.axes[0]
        x, y = event.xdata, event.ydata

        # preview circle
        if self.drawing and self.draw_type == 'circle' and self.circle_center:
            x0, y0 = self.circle_center
            for art in self.current_artists:
                art.remove()
            self.current_artists.clear()
            ellipse = MplEllipse(xy=self.circle_center,
                                  width=abs(2*(x - x0)), height=abs(2*(y - y0)))
            ellipse.set_edgecolor('white') 
            ellipse.set_linewidth(1)
            ellipse.set_facecolor('cyan')
            ellipse.set_alpha(0.3)
            ellipse.set_zorder(2)
            ax.add_patch(ellipse)
            self.current_artists.append(ellipse)
            self.canvas.draw()
            return

        # preview rectangle
        if self.drawing and self.draw_type == 'rectangle' and self.rect_start:
            x0, y0 = self.rect_start
            for art in self.current_artists:
                art.remove()
            self.current_artists.clear()
            rect = MplRectangle((min(x0, x), min(y0, y)), abs(x - x0), abs(y - y0))
            rect.set_edgecolor('white')
            rect.set_linewidth(1)
            rect.set_facecolor('cyan')
            rect.set_alpha(0.3)
            rect.set_zorder(2)
            ax.add_patch(rect)
            self.current_artists.append(rect)
            self.canvas.draw()
            return

        # modify ellipse boundary
        if self.mode == 'modify_ellipse' and self.selected_idx is not None:
            patch = self.shapes[self.selected_idx]
            xc, yc = patch.center
            # update radii based on cursor
            rx = abs(x - xc)
            ry = abs(y - yc)
            patch.width = 2 * rx
            patch.height = 2 * ry
            self.redraw_shapes()
            return

        # modify rectangle corner
        if self.mode == 'modify_rect' and self.selected_idx is not None:
            patch = self.shapes[self.selected_idx]
            x0, y0 = patch.get_x(), patch.get_y()
            w, h = patch.get_width(), patch.get_height()
            corners = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
            opp_idx = (self.modify_corner + 2) % 4
            ox, oy = corners[opp_idx]
            nx, ny = x, y
            patch.set_x(min(nx, ox)); patch.set_y(min(ny, oy))
            patch.set_width(abs(nx - ox)); patch.set_height(abs(ny - oy))
            self.redraw_shapes()
            return

        # moving or modifying existing shapes
        if not self.dragging or self.selected_idx is None:
            return
        dx = x - self.last_mouse[0]
        dy = y - self.last_mouse[1]
        self.last_mouse = (x, y)
        patch = self.shapes[self.selected_idx]
        if self.mode == 'move':
            if isinstance(patch, MplPolygon):
                pts = patch.get_xy() + [dx, dy]
                patch.set_xy(pts)
            elif isinstance(patch, MplEllipse):
                xc, yc = patch.center
                patch.center = (xc + dx, yc + dy)
            elif isinstance(patch, MplRectangle):
                patch.set_x(patch.get_x() + dx); patch.set_y(patch.get_y() + dy)
        elif self.mode == 'modify_poly':
            pts = patch.get_xy()
            vid = self.modify_vidx
            pts[vid, 0] += dx; pts[vid, 1] += dy
            if vid == 0:
                pts[-1] = pts[0]
            elif vid == len(pts) - 1:
                pts[0] = pts[-1]
            patch.set_xy(pts)
        self.redraw_shapes()

    def on_release(self, event):
        # finalize circle
        if self.drawing and self.draw_type == 'circle' and self.circle_center:
            x0, y0 = self.circle_center
            x1, y1 = event.xdata, event.ydata
            ellipse = MplEllipse(xy=self.circle_center,
                                  width=abs(2*(x1 - x0)), height=abs(2*(y1 - y0)))
            self.shapes.append(ellipse)
            for art in self.current_artists:
                art.remove()
            self.current_artists.clear()
            self.circle_center = None
            self.drawing = False
            self.draw_type = None
            self.redraw_shapes()
            print("Circle drawn.")
            return

        # finalize rectangle
        if self.drawing and self.draw_type == 'rectangle' and self.rect_start:
            x0, y0 = self.rect_start
            x1, y1 = event.xdata, event.ydata
            rect = MplRectangle((min(x0, x1), min(y0, y1)), abs(x1 - x0), abs(y1 - y0))
            self.shapes.append(rect)
            for art in self.current_artists:
                art.remove()
            self.current_artists.clear()
            self.rect_start = None
            self.drawing = False
            self.draw_type = None
            self.redraw_shapes()
            print("Rectangle drawn.")
            return

        # end drag
        if self.dragging:
            self.dragging = False
            self.mode = None
            self.modify_vidx = None
            self.modify_corner = None
            self.last_mouse = None

    def draw_current(self):
        self.redraw_shapes()
        ax = self.canvas.figure.axes[0]
        if self.current_points:
            xs, ys = zip(*self.current_points)
            ax.plot(xs, ys, color='white', linewidth=1, zorder=3)
            ax.scatter(xs, ys, s=20, facecolor='white', edgecolor='white', zorder=4)
        self.canvas.draw()

    def redraw_shapes(self):
        ax = self.canvas.figure.axes[0]
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        ax.cla()
        ax.axhline(0, color='white', linewidth=0.5)
        ax.axvline(0, color='white', linewidth=0.5)
        ax.set_aspect('equal', 'box')
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)

        for patch in self.shapes:
            patch.set_edgecolor('white'); patch.set_linewidth(1)
            patch.set_facecolor('cyan'); patch.set_alpha(0.3)
            patch.set_zorder(1)
            ax.add_patch(patch)
            if isinstance(patch, MplPolygon):
                verts = patch.get_xy()[:-1]
                xs, ys = zip(*verts)
                ax.scatter(xs, ys, s=10, facecolor='white', edgecolor='white', zorder=2)
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
