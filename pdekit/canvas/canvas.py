from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QMenu,
    QToolButton, QWidget, QVBoxLayout, QSizePolicy,
    QDialog, QFormLayout, QLabel, QLineEdit, QDialogButtonBox, QMessageBox
)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar
)
from matplotlib.patches import Polygon as MplPolygon, Ellipse as MplEllipse, Rectangle as MplRectangle, PathPatch
from matplotlib.path import Path
from matplotlib import patheffects as pe
from matplotlib.collections import LineCollection

from shapely.geometry import Polygon as ShapelyPoly, Point as ShapelyPoint, box as shapely_box, MultiPolygon
from shapely.geometry import GeometryCollection
from shapely.ops import unary_union
from shapely import affinity as shapely_aff
from pdekit.mesh.generator import generate_mesh

from pdekit.shapes.dialogs import EllipseDialog, RectangleDialog, DomainCalculatorDialog           
from math import hypot, atan2, cos, sin
import numpy as np
import re



class Canvas(QWidget):
    
    CLOSE_PIXEL_THRESHOLD = 10
    
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(parent)

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
        
        # meshing
        
        # mesh overlay + last-used options
        self._mesh_collection = None         # LineCollection overlay (already used by show_mesh)
        self._last_mesh_kwargs = None        # remembers options used to generate mesh
        
        self._mesh = None                       # last mesh data you drew
        self._mesh_collection = None            # LineCollection overlay
        self._mesh_color = (0.98, 0.67, 0.16)   # warm orange
        self._mesh_alpha_active = 0.75          # normal visibility
        self._mesh_alpha_edit = 0.30            # faded while editing/dragging
        self._mesh_lw = 0.9
            
        # store geometry
        self.shapes = []
        self.current_points = []
        self.current_artists = []

        # tagging state
        self._tag_counter = 1
        self._shape_tags = {}    # id(patch) -> tag
        self._tag_to_shape = {}  # tag -> patch
        self._tag_text = {}      # tag -> Text artist
        self._shape_geom = {}  # id(patch) -> Shapely geometry (Polygon)
        
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

        # clear tags & labels too
        for t in list(self._tag_text.values()):
            try:
                t.remove()
            except:
                pass
        self._tag_text.clear()
        self._shape_tags.clear()
        self._tag_to_shape.clear()
        self._tag_counter = 1

        self.canvas.draw()
        
    def delete_selected(self):
        if self.selected_idx is not None:
            patch = self.shapes.pop(self.selected_idx)

            # also remove its tag + label
            tag = self._shape_tags.pop(id(patch), None)
            if tag:
                self._tag_to_shape.pop(tag, None)
                t = self._tag_text.pop(tag, None)
                if t:
                    try:
                        t.remove()
                    except:
                        pass
                    
            self._shape_geom.pop(id(patch), None)

            self.selected_idx = None
            self.redraw_shapes()
            
    def _highlight(self, idx):
        """Mark a shape as selected and redraw."""
        if idx is not None:
            self.selected_idx = idx
            self.redraw_shapes()      
            
    def _clear_highlight(self, idx):
        """Clear any previous selection and redraw."""
        if idx is not None:
            # Only clear if it was actually selected
            if self.selected_idx == idx:
                self.selected_idx = None
            self.redraw_shapes()

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

        for i, patch in enumerate(self.shapes):
            if i == self.selected_idx:
                # highlighted style
                patch.set_edgecolor('red')
                patch.set_linewidth(1)
                patch.set_alpha(0.4)
                patch.set_zorder(2)
            else:
                # normal/unhighlighted style
                patch.set_edgecolor('white')
                patch.set_linewidth(1)
                patch.set_facecolor('cyan')
                patch.set_alpha(0.3)
                patch.set_zorder(1)
    
            ax.add_patch(patch)
            if isinstance(patch, MplPolygon):
                xs, ys = zip(*patch.get_xy()[:-1])
                ax.scatter(xs, ys, s=10, facecolor='white', edgecolor='white', zorder=2)

            # re-place tag labels for every shape
            self._place_tag_text_for_patch_if_tagged(patch)
            
            # keep boolean-result patches vesting up
            if isinstance(patch, PathPatch):
                try:
                    patch.set_fillrule('evenodd')
                    patch.set_joinstyle('round')
                    patch.set_capstyle('butt')
                    patch.set_snap(False)
                    patch.set_antialiased(True)
                    # also make sure the path still disables simplify
                    patch.get_path().should_simplify = False
                except Exception:
                    pass

        # keep the mesh overlay visible across redraws
        if self._mesh_collection is not None:
            # fade while editing/moving for better geometry visibility
            editing = bool(self.mode) or bool(self.dragging)
            self._mesh_collection.set_alpha(
                self._mesh_alpha_edit if editing else self._mesh_alpha_active
            )
            try:
                self.ax.add_collection(self._mesh_collection)
            except Exception:
                # if Matplotlib still thinks it's attached elsewhere
                try: self._mesh_collection.remove()
                except Exception: pass
                self.ax.add_collection(self._mesh_collection)


        self.canvas.draw()

    def on_click(self, event):
        
        prev_idx  = self.selected_idx
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
                                # === ADDED: tag position update
                                self._update_tag_position_for_patch(patch)
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
                                # === ADDED: tag position update
                                self._update_tag_position_for_patch(patch)
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
                # === ADDED: auto-tag
                self._auto_tag(poly)
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
                hit = False
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
                        #self.selected_idx = idx
                        self.mode = 'move'
                        self.dragging = True
                        hit = True
                        self.last_mouse = (xpix, ypix)
                        #return
                    
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
                        #self.selected_idx = idx
                        self.mode = 'modify_ellipse'
                        self.dragging = True
                        return
                    
                    # interior: move ellipse
                    if rx and ry and ((x - xc)/rx)**2 + ((y - yc)/ry)**2 <= 1:
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
                        #self.selected_idx = idx
                        self.mode = 'move'
                        self.dragging = True
                        hit = True
                        self.last_mouse = (xpix, ypix)
                        #return
                    
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
                        #self.selected_idx = idx
                        self.modify_corner = pixel_dists.index(min(pixel_dists))
                        self.mode = 'modify_rect'
                        self.dragging = True
                        opp_idx = (pixel_dists.index(min(pixel_dists)) + 2) % 4
                        self.opp_corner = corners[opp_idx]
                        return
                    
                    # move rectangle
                    if x0 <= x <= x0 + w and y0 <= y <= y0 + h:
                        
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
                            
                        #self.selected_idx = idx
                        self.mode = 'move'
                        self.dragging = True
                        hit = True
                        self.last_mouse = (xpix, ypix)
                        #return
                # PathPatch (result of domain ops) - move by dragging inside
                if isinstance(patch, PathPatch):
                    geom = self._shape_geom.get(id(patch), self._patch_to_geom(patch))
                    if not geom.is_empty and geom.contains(ShapelyPoint(x, y)):
                        if getattr(self.toolbar, 'mode', '') == 'pan/zoom':
                            self.toolbar.pan()
                        self.mode = 'move'
                        self.dragging = True
                        hit = True
                        self.last_mouse = (xpix, ypix)

                if hit:
                    self._clear_highlight(prev_idx)
                    self.selected_idx = idx 
                    self._highlight(idx)
                    return
            self._clear_highlight(prev_idx)
                    

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
            # === ADDED: tag position update
            self._update_tag_position_for_patch(patch)
            self.redraw_shapes()
            return

        # modify rectangle corner
        if self.mode == 'modify_rect' and self.selected_idx is not None:
            patch = self.shapes[self.selected_idx]
            
            nx, ny = event.xdata, event.ydata
            if nx is None or ny is None:
                return
            
            # fixed opposite corner in data coords
            ox, oy = self.opp_corner
            # compute new origin and size (flips automatically)
            new_x = min(nx, ox)
            new_y = min(ny, oy)
            w = abs(nx - ox)
            h = abs(ny - oy)
            patch.set_x(new_x)
            patch.set_y(new_y)
            patch.set_width(w)
            patch.set_height(h)
            # tag position update
            self._update_tag_position_for_patch(patch)
            self.redraw_shapes()
            # update last mouse position
            self.last_mouse = (event.x, event.y)

        if not getattr(self, 'dragging', False) or self.selected_idx is None:
            return

        xpix, ypix = event.x, event.y
        inv = self.ax.transData.inverted()
        try:
            x0, y0 = inv.transform([self.last_mouse])[0]
            x1, y1 = inv.transform([(xpix, ypix)])[0]
        except Exception:
            return
        dx, dy = x1 - x0, y1 - y0
        patch = self.shapes[self.selected_idx]
        
        self.last_mouse = (xpix, ypix)
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
            elif isinstance(patch, PathPatch):
                # translate the stored geometry, then update the patch path
                geom = self._shape_geom.get(id(patch), self._patch_to_geom(patch))
                if not geom.is_empty:
                    geom2 = shapely_aff.translate(geom, xoff=dx, yoff=dy)
                    self._shape_geom[id(patch)] = geom2
                    # update the path to match new geometry
                    if isinstance(geom2, ShapelyPoly):
                        new_path = self._polygon_to_path(geom2)
                        new_path.should_simplify = False          
                        patch.set_path(new_path)
                        try:
                            patch.set_fillrule('evenodd')
                            patch.set_joinstyle('round')
                            patch.set_capstyle('butt')
                            patch.set_snap(False)
                            patch.set_antialiased(True)
                        except Exception:
                            pass
            
            if isinstance(patch, PathPatch):
                self._translate_mesh_overlay(dx, dy)
                        
        elif self.mode == 'modify_poly':
            pts = patch.get_xy()
            vid = self.modify_vidx
            pts[vid, 0] += dx; pts[vid, 1] += dy
            if vid == 0:
                pts[-1] = pts[0]
            elif vid == len(pts) - 1:
                pts[0] = pts[-1]
            patch.set_xy(pts)
        


        # === ADDED: update tag for the moved/modified shape
        self._update_tag_position_for_patch(patch)
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
            # === ADDED: auto-tag
            self._auto_tag(ellipse)

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
            # === ADDED: auto-tag
            self._auto_tag(rect)
            
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
        
        for tag, patch in list(self._tag_to_shape.items()):
            self._place_tag_text(tag, patch)

    # def show_mesh(self, mesh, *, color='orange', lw=0.8, z=30, clear_prev=True):
    #     ax = self.canvas.figure.axes[0] if self.canvas else self.ax

    #     # (optional) clear previous mesh lines
    #     if clear_prev and hasattr(self, "_mesh_lines"):
    #         for ln in self._mesh_lines:
    #             try: ln.remove()
    #             except Exception: pass
    #         self._mesh_lines.clear()
    #     else:
    #         self._mesh_lines = []

    #     # draw triangle edges
    #     for tri in mesh.elements:
    #         xs, ys = zip(*tri)  # tri is closed: [(x,y),(x,y),(x,y),(x,y)]
    #         ln, = ax.plot(xs, ys, '-', linewidth=lw, color=color, zorder=z)
    #         self._mesh_lines.append(ln)

    #     self.canvas.draw_idle()
    
    def show_mesh(self, mesh, *, color=None, lw=None):
        """Display/replace the mesh overlay and keep it across redraws."""
        # detach old overlay if any
        if self._mesh_collection is not None:
            try: self._mesh_collection.remove()
            except Exception: pass
            self._mesh_collection = None

        self._mesh = mesh
        if color is not None: self._mesh_color = color
        if lw    is not None: self._mesh_lw    = lw

        self._mesh_collection = self._mesh_to_collection(mesh)
        # add now; redraw_shapes() will re-add after every cla()
        self.ax.add_collection(self._mesh_collection)
        self.canvas.draw_idle()


# TAGGING UTILS
    def _auto_tag(self, patch):
        tag = f"P{self._tag_counter}"
        self._tag_counter += 1
        self._shape_tags[id(patch)] = tag
        self._tag_to_shape[tag] = patch
        self._place_tag_text(tag, patch)

    def _place_tag_text_for_patch_if_tagged(self, patch):
        tag = self._shape_tags.get(id(patch))
        if tag:
            self._place_tag_text(tag, patch)
            

    def _place_tag_text(self, tag, patch):
        geom = self._shape_geom.get(id(patch), self._patch_to_geom(patch))
        if geom.is_empty:
            return

        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        view = shapely_box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

        try:
            visible = geom.intersection(view)
        except Exception:
            # repair attempt
            try:
                from shapely.validation import make_valid as _make_valid
            except Exception:
                try:
                    from shapely import make_valid as _make_valid
                except Exception:
                    _make_valid = None
            if _make_valid is not None:
                try:
                    visible = _make_valid(geom).intersection(view)
                except Exception:
                    visible = geom  # last resort
            else:
                visible = geom

        target = (visible if not visible.is_empty else geom).representative_point()
        x, y = target.x, target.y

        old = self._tag_text.get(tag)
        if old is not None:
            try: old.remove()
            except Exception: pass

        txt = self.ax.text(x, y, tag, ha='center', va='center',
                        fontsize=10, color='white', zorder=50, clip_on=True)
        try:
            txt.set_path_effects([pe.withStroke(linewidth=2, foreground='black')])
        except Exception:
            pass
        self._tag_text[tag] = txt


    def _update_tag_position_for_patch(self, patch):
        tag = self._shape_tags.get(id(patch))
        if tag:
            self._place_tag_text(tag, patch)

    def get_shape_tags(self):
        return list(self._tag_to_shape.keys())


    def _patch_to_geom(self, patch):
        stored = self._shape_geom.get(id(patch))
        if stored is not None:
            return stored

        if isinstance(patch, MplPolygon):
            coords = patch.get_xy()
            if len(coords) >= 3:
                return ShapelyPoly(coords)

        elif isinstance(patch, MplRectangle):
            x0, y0 = patch.get_x(), patch.get_y()
            w, h = patch.get_width(), patch.get_height()
            return shapely_box(x0, y0, x0 + w, y0 + h)

        elif isinstance(patch, MplEllipse):
            xc, yc = patch.center
            rx, ry = patch.width/2.0, patch.height/2.0
            circ = ShapelyPoint(xc, yc).buffer(1.0, resolution=256)
            return shapely_aff.scale(circ, rx, ry, origin=(xc, yc))

        elif isinstance(patch, PathPatch):
            # --- NEW: rebuild rings from path codes; drop NaNs from CLOSEPOLY
            path = patch.get_path()
            verts = path.vertices
            codes = path.codes
            if codes is None:
                # defensive: if no codes, just ignore any non-finite rows
                verts = verts[np.isfinite(verts).all(axis=1)]
                if len(verts) >= 3:
                    try:
                        return ShapelyPoly(verts)
                    except Exception:
                        return ShapelyPoly()  # empty on failure
                return ShapelyPoly()

            rings, ring = [], []
            for (x, y), c in zip(verts, codes):
                if c == Path.MOVETO:
                    if len(ring) >= 3:
                        if ring[0] != ring[-1]:
                            ring.append(ring[0])
                        rings.append(ring)
                    ring = []
                    if np.isfinite(x) and np.isfinite(y):
                        ring.append((x, y))
                elif c == Path.LINETO:
                    if np.isfinite(x) and np.isfinite(y):
                        ring.append((x, y))
                elif c == Path.CLOSEPOLY:
                    # CLOSEPOLY row may be (nan, nan) — just close current ring
                    if len(ring) >= 3:
                        if ring[0] != ring[-1]:
                            ring.append(ring[0])
                        rings.append(ring)
                    ring = []
                else:
                    # ignore other codes
                    pass

            if len(rings) == 0:
                return ShapelyPoly()

            exterior = rings[0]
            holes = [r for r in rings[1:] if len(r) >= 4]
            try:
                return ShapelyPoly(exterior, holes)
            except Exception:
                return ShapelyPoly()  # empty fallback

        return ShapelyPoly()

    
    def _polygon_to_path(self, poly: ShapelyPoly):

        def ring_to_path(ring):
            xs, ys = ring.xy
            vs = np.column_stack([xs, ys])

            # drop the duplicated endpoint if present
            if len(vs) > 1 and np.allclose(vs[0], vs[-1]):
                vs = vs[:-1]

            # MOVETO + LINETOs
            codes = np.full(len(vs), Path.LINETO, dtype=np.uint8)
            codes[0] = Path.MOVETO

            # CLOSEPOLY uses a dummy vertex --> prevents any stroke segment
            vs = np.vstack([vs, [np.nan, np.nan]])
            codes = np.append(codes, Path.CLOSEPOLY)

            return Path(vs, codes)

        # exterior + all holes as separate subpaths
        paths = [ring_to_path(poly.exterior)]
        for interior in poly.interiors:
            paths.append(ring_to_path(interior))

        compound = Path.make_compound_path(*paths)
        compound.should_simplify = False
        return compound

    
    def _geom_to_patches(self, geom):
        patches = []
        if geom.is_empty:
            return patches

 
        def make_patch(poly: ShapelyPoly):
            path = self._polygon_to_path(poly)
            path.should_simplify = False
            p = PathPatch(path)

            # keep holes as holes
            try:
                p.set_fillrule('evenodd')
            except Exception:
                pass

            # SAFE STROKE SETTINGS --> prevent spokes
            try:
                p.set_joinstyle('round')
                p.set_capstyle('butt')
                # avoid snapping across subpaths
                p.set_snap(False)
                p.set_antialiased(True)
            except Exception:
                pass

            # remember geometry for moving
            self._shape_geom[id(p)] = poly
            return p


        if isinstance(geom, ShapelyPoly):
            patches.append(make_patch(geom))
            return patches

        if hasattr(geom, "geoms"):  # MultiPolygon or GeometryCollection
            for g in geom.geoms:
                if isinstance(g, ShapelyPoly):
                    patches.append(make_patch(g))
            return patches

        return patches



    # =================================
    # ===   Domain Calculator  ===
    # =================================
    # hyphen is escaped; parentheses split to avoid "bad range" errors
    _token_re = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*|[()]|[+\-*!&])\s*")

    def _tokenize(self, expr: str):
        pos = 0
        tokens = []
        while pos < len(expr):
            m = self._token_re.match(expr, pos)
            if not m:
                raise ValueError(f"Unexpected token near: {expr[pos:pos+16]}")
            tokens.append(m.group(1))
            pos = m.end()
        return tokens

    def _to_rpn(self, tokens):
        prec = {'!': 3, '*': 2, '&': 2, '+': 1, '-': 1}
        right_assoc = {'!'}
        out, stack = [], []
        for t in tokens:
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', t):
                out.append(t)
            elif t in prec:
                while stack and stack[-1] != '(' and (prec[stack[-1]] > prec[t] or (prec[stack[-1]] == prec[t] and t not in right_assoc)):
                    out.append(stack.pop())
                stack.append(t)
            elif t == '(':
                stack.append(t)
            elif t == ')':
                while stack and stack[-1] != '(':
                    out.append(stack.pop())
                if not stack or stack[-1] != '(':
                    raise ValueError("Mismatched parentheses")
                stack.pop()
            else:
                raise ValueError(f"Unknown token: {t}")
        while stack:
            if stack[-1] in ('(', ')'):
                raise ValueError("Mismatched parentheses")
            out.append(stack.pop())
        return out

    def _eval_rpn(self, rpn):
        stack = []
        # Complement universe = current axes rectangle
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        universe = shapely_box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

        for t in rpn:
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', t):
                if t not in self._tag_to_shape:
                    raise KeyError(f"Unknown tag: {t}")
                stack.append(self._patch_to_geom(self._tag_to_shape[t]))
            elif t == '!':
                a = stack.pop()
                stack.append(universe.difference(a))
            elif t in ('*', '&', '+', '-'):
                b = stack.pop()
                a = stack.pop()
                if t in ('*', '&'):
                    stack.append(a.intersection(b))
                elif t == '+':
                    stack.append(a.union(b))
                else:
                    stack.append(a.difference(b))
            else:
                raise ValueError(f"Bad token: {t}")
        if len(stack) != 1:
            raise ValueError("Invalid expression")
        return stack[0]

    def domain_calculator(self):
        """Open the domain calculator dialog and replace existing shapes with the result."""
        tags = self.get_shape_tags()
        dlg = DomainCalculatorDialog(self, tags)
        if not dlg.exec():
            return

        expr, requested_tag = dlg.getValues()
        if not expr:
            QMessageBox.warning(self, "Domain Calculator", "Expression cannot be empty.")
            return

        try:
            tokens = self._tokenize(expr)
            rpn = self._to_rpn(tokens)
            geom = self._eval_rpn(rpn)
        except Exception as e:
            QMessageBox.critical(self, "Domain Calculator", f"Could not evaluate expression:\n{e}")
            return

        # convert to patches
        patches = self._geom_to_patches(geom)
        if not patches:
            QMessageBox.information(self, "Domain Calculator", "Resulting geometry is empty.")
            return

        # --- clear everything else ---
        for p in self.shapes:
            try: p.remove()
            except Exception: pass
        self.shapes.clear()

        for t in list(self._tag_text.values()):
            try: t.remove()
            except Exception: pass
        self._tag_text.clear()
        self._shape_tags.clear()
        self._tag_to_shape.clear()
        self._shape_geom.clear()

        # add only the result --> auto-tag if none provided 
        new_tag = requested_tag.strip() or f"P{self._tag_counter}"
        # If result has multiple disjoint pieces -->  suffix the same base tag
        if len(patches) == 1:
            p = patches[0]
            self.shapes.append(p)
            self._shape_tags[id(p)] = new_tag
            self._tag_to_shape[new_tag] = p
        else:
            for i, p in enumerate(patches, start=1):
                tag_i = f"{new_tag}_{i}"
                self.shapes.append(p)
                self._shape_tags[id(p)] = tag_i
                self._tag_to_shape[tag_i] = p

        self._tag_counter += 1  # advance counter so next auto tag is fresh
        self.redraw_shapes()
        
        # --- auto-regenerate mesh if a mesh existed or if we have remembered options ---
        if self._mesh_collection is not None or self._last_mesh_kwargs:
            from pdekit.mesh.generator import generate_mesh
            try:
                # we already have `geom` here from the calculator; clean and reuse it
                new_geom = geom.buffer(0)
                mesh = generate_mesh(new_geom, **(self._last_mesh_kwargs or {}))
                self.show_mesh(mesh)  # updates the faint overlay in-place
            except Exception as e:
                # Don't block geometry update; just notify about mesh failure
                QMessageBox.warning(self, "Remesh", f"Remeshing failed:\n{e}")


    
    ###############
    ### MESHING ###
    ###############
    
    def _mesh_to_collection(self, mesh, *, color=None, alpha=None, lw=None, z=9):
        """Convert your mesh into a LineCollection (edges only)."""
        color = color if color is not None else self._mesh_color
        alpha = alpha if alpha is not None else self._mesh_alpha_active
        lw    = lw    if lw    is not None else self._mesh_lw

        segments = []
        for tri in mesh.elements:
            pts = list(tri)
            # handle triangles passed as 3 pts or closed (4 with last==first)
            if len(pts) == 4 and pts[0] == pts[-1]:
                pts = pts[:-1]
            if len(pts) >= 3:
                segments.append([pts[0], pts[1]])
                segments.append([pts[1], pts[2]])
                segments.append([pts[2], pts[0]])

        lc = LineCollection(
            segments,
            linewidths=lw,
            colors=[color],
            alpha=alpha,
            zorder=z,
            clip_on=True,
        )
        return lc

    def _translate_mesh_overlay(self, dx: float, dy: float):
        """Translate the mesh LineCollection in data coordinates."""
        if self._mesh_collection is None:
            return
        segs = self._mesh_collection.get_segments()
        if not segs:
            return
        off = np.array([dx, dy], dtype=float)
        segs2 = [s + off for s in segs]   # each s is (2,2)
        self._mesh_collection.set_segments(segs2)

    
    def get_polygons_for_meshing(self):
        """Return a list of Shapely Polygons that represent the current domain(s)."""
        polys = []
        for patch in self.shapes:
            g = self._shape_geom.get(id(patch)) or self._patch_to_geom(patch)
            if g is None or g.is_empty:
                continue
            if isinstance(g, ShapelyPoly):
                polys.append(g)
            elif hasattr(g, "geoms"):
                for gg in g.geoms:
                    if isinstance(gg, ShapelyPoly):
                        polys.append(gg)
        return polys
    
    
    def _current_domain_geom(self):
        """
        Union all current shape geometries into one Shapely geometry suitable for meshing.
        Uses the exact stored geometry for PathPatch results when available.
        """
        geoms = []
        for p in self.shapes:
            g = self._shape_geom.get(id(p), self._patch_to_geom(p))
            if not g.is_empty:
                geoms.append(g)
        if not geoms:
            return GeometryCollection()
        
        try:
            u = unary_union(geoms)
            # clean tiny slivers/self-touching rings, avoids GEOS TopologyException
            return u.buffer(0)
        except Exception:
            return geoms[0].buffer(0)
        

    def generate_and_show_mesh(self, max_area=None, quality=True):
        """
        Triangulate the current domain (union of shapes) and show/update the mesh overlay.
        Remembers kwargs so we can auto-regenerate after domain operations.
        """
        # union the current result shapes into a single (Multi)Polygon
        geoms = [self._patch_to_geom(p) for p in self.shapes]
        domain = unary_union([g for g in geoms if not g.is_empty])

        mesh = generate_mesh(domain, max_area=max_area, quality=quality, quiet=True)
        self.show_mesh(mesh)
            
    # def generate_and_show_mesh(self, **kwargs):
       
    #     geom = self._current_domain_geom()
    #     if geom.is_empty:
    #         QMessageBox.information(self, "Generate Mesh", "No geometry to mesh.")
    #         return

    #     # Remember last options used
    #     self._last_mesh_kwargs = dict(kwargs) if kwargs else {}

    #     try:
    #         mesh = generate_mesh(geom, **self._last_mesh_kwargs)
    #     except Exception as e:
    #         QMessageBox.critical(self, "Generate Mesh", f"Meshing failed:\n{e}")
    #         return

    #     self.show_mesh(mesh)   # your existing overlay drawer (keeps it faint & persistent)


    