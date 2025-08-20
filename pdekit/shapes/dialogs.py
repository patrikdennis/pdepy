# # Package for shape-specific dialogs and widgets
# # File: pdekit/gui/shapes/dialogs.py

# from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QDialogButtonBox

# # class DomainCalculatorDialog(QDialog):
# #     def __init__(self, parent):
# #         super().__init__(parent)
# #         self.setWindowTitle("Domain Calculator")
# #         form = QFormLayout(self)
# #         self.domain_edit = QLineEdit("Example: P1 + P2 - P3")
# #         form.addRow(QLabel("Enter Domain:"), self.domain_edit)
        
# #         buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
# #                                    QDialogButtonBox.StandardButton.Cancel)
# #         buttons.accepted.connect(self.accept)
# #         buttons.rejected.connect(self.reject)
# #         form.addRow(buttons)
        
    
# #     def getValues(self):
# #         return self.domain_edit.text()



# class EllipseDialog(QDialog):
#     def __init__(self, parent, xc, yc, rx, ry):
#         super().__init__(parent)
#         self.setWindowTitle("Edit Ellipse")
#         form = QFormLayout(self)
#         self.h_edit = QLineEdit(str(xc))
#         self.k_edit = QLineEdit(str(yc))
#         self.a_edit = QLineEdit(str(rx))
#         self.b_edit = QLineEdit(str(ry))
#         form.addRow(QLabel("Center x-coordinate:"), self.h_edit)
#         form.addRow(QLabel("Center y-coordinate:"), self.k_edit)
#         form.addRow(QLabel("Semi-major axis a:"), self.a_edit)
#         form.addRow(QLabel("Semi-minor axis b:"), self.b_edit)

#         buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
#                                    QDialogButtonBox.StandardButton.Cancel)
#         buttons.accepted.connect(self.accept)
#         buttons.rejected.connect(self.reject)
#         form.addRow(buttons)

#     def getValues(self):
#         return (float(self.h_edit.text()),
#                 float(self.k_edit.text()),
#                 float(self.a_edit.text()),
#                 float(self.b_edit.text()))


# class RectangleDialog(QDialog):
#     def __init__(self, parent, x0, y0, x1, y1):
#         super().__init__(parent)
#         self.setWindowTitle("Edit Rectangle")
#         form = QFormLayout(self)
#         self.x1_edit = QLineEdit(str(x0))
#         self.y1_edit = QLineEdit(str(y0))
#         self.x2_edit = QLineEdit(str(x1))
#         self.y2_edit = QLineEdit(str(y1))
#         form.addRow(QLabel("x1 (bottom-left x):"), self.x1_edit)
#         form.addRow(QLabel("y1 (bottom-left y):"), self.y1_edit)
#         form.addRow(QLabel("x2 (top-right x):"), self.x2_edit)
#         form.addRow(QLabel("y2 (top-right y):"), self.y2_edit)

#         buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
#                                    QDialogButtonBox.StandardButton.Cancel)
#         buttons.accepted.connect(self.accept)
#         buttons.rejected.connect(self.reject)
#         form.addRow(buttons)

#     def getValues(self):
#         return (float(self.x1_edit.text()),
#                 float(self.y1_edit.text()),
#                 float(self.x2_edit.text()),
#                 float(self.y2_edit.text()))







# File: pdekit/shapes/dialogs.py

from PyQt6.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QDialogButtonBox

class DomainCalculatorDialog(QDialog):
    """
    Boolean expression over tags -> result tag.
    Operators:
      + : union
      - : difference (A - B)
      * or &: intersection
      ! : complement (relative to current axes extent)
    Parentheses () supported, e.g. (P1 + P2) - !P3
    """
    def __init__(self, parent, available_tags=None):
        super().__init__(parent)
        self.setWindowTitle("Domain Calculator")
        form = QFormLayout(self)

        self.expr_edit = QLineEdit()
        self.expr_edit.setPlaceholderText("e.g. P1 + P2 - P3    or    (A & B) - !C")
        form.addRow(QLabel("Expression:"), self.expr_edit)

        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("e.g. Pnew")
        form.addRow(QLabel("Result tag:"), self.tag_edit)

        hint = ", ".join(available_tags or [])
        self.hint_label = QLabel(f"Available tags: {hint}" if hint else "No shapes tagged yet.")
        form.addRow(self.hint_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def getValues(self):
        return self.expr_edit.text().strip(), self.tag_edit.text().strip()


class EllipseDialog(QDialog):
    def __init__(self, parent, h, k, a, b):
        super().__init__(parent)
        self.setWindowTitle("Edit Ellipse")
        form = QFormLayout(self)
        self.h_edit = QLineEdit(str(h))
        self.k_edit = QLineEdit(str(k))
        self.a_edit = QLineEdit(str(a))
        self.b_edit = QLineEdit(str(b))

        form.addRow(QLabel("h (center x):"), self.h_edit)
        form.addRow(QLabel("k (center y):"), self.k_edit)
        form.addRow(QLabel("a (semi-axis x):"), self.a_edit)
        form.addRow(QLabel("b (semi-axis y):"), self.b_edit)

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
    def __init__(self, parent, x1, y1, x2, y2):
        super().__init__(parent)
        self.setWindowTitle("Edit Rectangle")
        form = QFormLayout(self)

        self.x1_edit = QLineEdit(str(x1))
        self.y1_edit = QLineEdit(str(y1))
        self.x2_edit = QLineEdit(str(x2))
        self.y2_edit = QLineEdit(str(y2))

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
