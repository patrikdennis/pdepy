# Package for plotting canvas widgets
# File: pdekit/canvas.py
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QMenu,
    QToolButton, QWidget, QVBoxLayout, QSizePolicy,
    QDialog, QFormLayout, QLabel, QLineEdit, QDialogButtonBox
)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
from matplotlib.patches import Polygon as MplPolygon, Ellipse as MplEllipse, Rectangle as MplRectangle
from shapely.geometry import Polygon as ShapelyPoly, Point as ShapelyPoint
from pdekit.shapes.dialogs import EllipseDialog, RectangleDialog
from math import hypot, atan2, cos, sin
import numpy as np

class Canvas(QWidget):
    
    #CLOSE_THRESHOLD = 0.5  # tolerance for vertex/edge selection
    CLOSE_PIXEL_THRESHOLD = 5
    
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        #super().__init__(self.fig)
        super().__init__(parent)
        
        #self.setParent(parent)

        # Create matplotlib Figure and Axes
        fig, ax = plt.subplots()
        self.figure = fig
        self.ax = ax

        # Wrap the Figure in a Qt widget
        self.canvas = FigureCanvas(self.figure)
        
        
        self.drawing = False
        self.draw_type = None   # 'polygon', 'circle', 'rectangle'
        
        self.selected_idx = None
        self.mode = None        # 'move', 'modify_poly', 'modify_ellipse', 'modify_rect'
        self.dragging = False
        self.modify_vidx = None
        self.modify_corner = None
        self.last_mouse = None
        self.circle_center = None
        self.rect_start = None
        
        # store geometry
        self.shapes = []
        self.current_points = []
        self.current_artists = []

        # Event connections
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        fig.canvas.mpl_connect('scroll_event', self.zoom_callback)
        
        # Create navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Lay out toolbar + canvas
        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def initialize(self):
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

    def start_polygon_mode(self):
        
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

    def start_circle_mode(self):
        
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

    def start_rectangle_mode(self):
        
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
        
    def _pixel_dist(self, xdata, ydata, event):
        xpix, ypix = self.ax.transData.transform((xdata, ydata))
        return np.hypot(xpix - event.x, ypix - event.y)
    
    def _is_close_pixel(self, xdata, ydata, event):
        # transform data coords to pixel coords
        xpix, ypix = self.ax.transData.transform((xdata, ydata))
        # event.x, event.y are in pixel coords relative to canvas
        dx = xpix - event.x
        dy = ypix - event.y
        dist = np.hypot(dx, dy)
        return dist < self.CLOSE_PIXEL_THRESHOLD
        
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

    def on_click(self, event):
        ax = event.inaxes
        if not ax:
            return
        
        x, y = event.xdata, event.ydata
        xpix, ypix = event.x, event.y
        
        if not self.shapes and (x is None or y is None):
            return
        
        # ── double-click to edit ellipse or rectangle ──
        if getattr(event, 'dblclick', False) and not self.drawing and event.button == 1:
                
            for idx, patch in enumerate(self.shapes):
                # edit ellipse/circle
                if isinstance(patch, MplEllipse):
                    xc, yc = patch.center
                    rx, ry = patch.width/2, patch.height/2
                    if ((x-xc)/rx)**2 + ((y-yc)/ry)**2 <= 1:
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
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
                        if getattr(self, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
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
            #if len(self.current_points) >= 3 and hypot(x - self.current_points[0][0], y - self.current_points[0][1]) <= self.CLOSE_THRESHOLD:
            if len(self.current_points) >= 3 and self._is_close_pixel(self.current_points[0][0], self.current_points[0][1], event):
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
            
            # polygon editing
            for idx, patch in enumerate(self.shapes):
                if isinstance(patch, MplPolygon):
                    verts = patch.get_xy()[:-1]
                    #dists = [hypot(px - x, py - y) for px, py in verts]
                    # pixel distance
                    pixel_dists = [self._pixel_dist(px, py, event) for px, py in verts]
                    
                    #if min(dists) <= self.CLOSE_THRESHOLD:
                    if min(pixel_dists) < self.CLOSE_PIXEL_THRESHOLD:
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
                        # modify polygon vertex
                        self.selected_idx = idx
                        self.modify_vidx = pixel_dists.index(min(pixel_dists))
                        self.mode = 'modify_poly'
                        self.dragging = True
                        self.last_mouse = (xpix, ypix)
                        return
                    # move polygon
                    if ShapelyPoly(patch.get_xy()).contains(ShapelyPoint(x, y)):
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
                        self.selected_idx = idx
                        self.mode = 'move'
                        self.dragging = True
                        self.last_mouse = (xpix, ypix)
                        return
                    
                # ellipse editing
                if isinstance(patch, MplEllipse):
                    xc, yc = patch.center
                    rx, ry = patch.width / 2, patch.height / 2
                    
                    # boundary: nearest point
                    angle = atan2(y - yc, x - xc)
                    bx = xc + rx * cos(angle)
                    by = yc + ry * sin(angle)
                    
                    if self._is_close_pixel(bx, by, event):
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
                            
                        # modify ellipse boundary
                        self.selected_idx = idx
                        self.mode = 'modify_ellipse'
                        self.dragging = True
                        return
                    
                    # interior: move ellipse
                    if rx and ry and ((x - xc)/rx)**2 + ((y - yc)/ry)**2 <= 1:
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
                        self.selected_idx = idx
                        self.mode = 'move'
                        self.dragging = True
                        self.last_mouse = (xpix, ypix)
                        return
                    
                # rectangle editing
                if isinstance(patch, MplRectangle):
                    
                    x0, y0 = patch.get_x(), patch.get_y()
                    w, h = patch.get_width(), patch.get_height()
                    corners = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
                    pixel_dists = [self._pixel_dist(cx, cy, event) for cx, cy in corners]
                    if min(pixel_dists) < self.CLOSE_PIXEL_THRESHOLD:
                        
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
                            
                        # modify rectangle corner
                        self.selected_idx = idx
                        self.modify_corner = pixel_dists.index(min(pixel_dists))
                        self.mode = 'modify_rect'
                        self.dragging = True
                        return
                    
                    # move rectangle
                    if x0 <= x <= x0 + w and y0 <= y <= y0 + h:
                        
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
                            
                        self.selected_idx = idx
                        self.mode = 'move'
                        self.dragging = True
                        self.last_mouse = (xpix, ypix)
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
                                  width=abs(2*(x - x0)), 
                                  height=abs(2*(y - y0)))
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
            #xc, yc = patch.center
            
            xpix, ypix = event.x, event.y
            inv = self.ax.transData.inverted()
            xdata, ydata = inv.transform((xpix, ypix))
            # original center
            xc, yc = patch.center

            # update radii based on cursor
            rx = abs(xdata - xc)
            ry = abs(ydata - yc)
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
            patch.set_x(min(nx, ox))
            patch.set_y(min(ny, oy))
            patch.set_width(abs(nx - ox))
            patch.set_height(abs(ny - oy))
            self.redraw_shapes()
            return

        if not getattr(self, 'dragging', False) or self.selected_idx is None:
            return
        # current mouse in pixel coords
        xpix, ypix = event.x, event.y
        inv = self.ax.transData.inverted()
        x0, y0 = inv.transform(self.last_mouse)
        x1, y1 = inv.transform((xpix, ypix))
        dx, dy = x1 - x0, y1 - y0
        
        #dx = x - self.last_mouse[0]
        #dy = y - self.last_mouse[1]
        self.last_mouse = (xpix, ypix)
        patch = self.shapes[self.selected_idx]
        if self.mode == 'move':
            if isinstance(patch, MplPolygon):
                pts = patch.get_xy() + [dx, dy]
                patch.set_xy(pts)
            elif isinstance(patch, MplEllipse):
                xc, yc = patch.center
                patch.center = (xc + dx, yc + dy)
            elif isinstance(patch, MplRectangle):
                patch.set_x(patch.get_x() + dx)
                patch.set_y(patch.get_y() + dy)
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
                                  width=abs(2*(x1 - x0)), 
                                  height=abs(2*(y1 - y0)))
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

    def show_mesh(self, mesh):
        for elem in mesh.elements:
            xs, ys = zip(*elem)
            self.ax.plot(xs, ys, '-k')
        self.draw()
