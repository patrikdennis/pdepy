# Package for shape-specific dialogs and widgets
# File: pdekit/gui/shapes/dialogs.py

from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QDialogButtonBox


class EllipseDialog(QDialog):
    def __init__(self, parent, xc, yc, rx, ry):
        super().__init__(parent)
        self.setWindowTitle("Edit Ellipse")
        form = QFormLayout(self)
        self.h_edit = QLineEdit(str(xc))
        self.k_edit = QLineEdit(str(yc))
        self.a_edit = QLineEdit(str(rx))
        self.b_edit = QLineEdit(str(ry))
        form.addRow(QLabel("Center x-coordinate:"), self.h_edit)
        form.addRow(QLabel("Center y-coordinate:"), self.k_edit)
        form.addRow(QLabel("Semi-major axis a:"), self.a_edit)
        form.addRow(QLabel("Semi-minor axis b:"), self.b_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def getValues(self):
        return (float(self.h_edit.text()),
                float(self.k_edit.text()),
                float(self.a_edit.text()),
                float(self.b_edit.text()))


class RectangleDialog(QDialog):
    def __init__(self, parent, x0, y0, x1, y1):
        super().__init__(parent)
        self.setWindowTitle("Edit Rectangle")
        form = QFormLayout(self)
        self.x1_edit = QLineEdit(str(x0))
        self.y1_edit = QLineEdit(str(y0))
        self.x2_edit = QLineEdit(str(x1))
        self.y2_edit = QLineEdit(str(y1))
        form.addRow(QLabel("x1 (bottom-left x):"), self.x1_edit)
        form.addRow(QLabel("y1 (bottom-left y):"), self.y1_edit)
        form.addRow(QLabel("x2 (top-right x):"), self.x2_edit)
        form.addRow(QLabel("y2 (top-right y):"), self.y2_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def getValues(self):
        return (float(self.x1_edit.text()),
                float(self.y1_edit.text()),
                float(self.x2_edit.text()),
                float(self.y2_edit.text()))
