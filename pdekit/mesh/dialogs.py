from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QDialogButtonBox, QCheckBox, QDoubleSpinBox,
    QSpinBox, QWidget
)

class MeshRefineDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, *, defaults: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Refine Mesh")

        self._quality = QCheckBox("Quality refinement (q)")
        self._quality.setChecked(True)

        self._min_angle = QDoubleSpinBox()
        self._min_angle.setRange(5.0, 40.0)
        self._min_angle.setSingleStep(1.0)
        self._min_angle.setValue(25.0)

        self._use_max_area = QCheckBox("Limit triangle area (a)")
        self._max_area = QDoubleSpinBox()
        self._max_area.setDecimals(6)
        self._max_area.setRange(1e-12, 1e12)
        self._max_area.setSingleStep(0.1)
        self._max_area.setValue(0.1)
        self._max_area.setEnabled(False)
        self._use_max_area.toggled.connect(self._max_area.setEnabled)

        self._conforming = QCheckBox("Conforming Delaunay (D)")
        self._conforming.setChecked(True)

        self._max_steiner = QSpinBox()
        self._max_steiner.setRange(-1, 10_000)
        self._max_steiner.setValue(-1)  # -1 => unlimited / not set

        self._smooth_iters = QSpinBox()
        self._smooth_iters.setRange(0, 1000)
        self._smooth_iters.setValue(0)

        if defaults:
            self._quality.setChecked(bool(defaults.get("quality", True)))
            self._min_angle.setValue(float(defaults.get("min_angle", 25.0)))
            ma = defaults.get("max_area", None)
            if ma is not None:
                self._use_max_area.setChecked(True)
                self._max_area.setEnabled(True)
                self._max_area.setValue(float(ma))
            self._conforming.setChecked(bool(defaults.get("conforming_delaunay", True)))
            self._max_steiner.setValue(int(defaults.get("max_steiner", -1) or -1))
            self._smooth_iters.setValue(int(defaults.get("smooth_iters", 0)))

        form = QFormLayout(self)
        form.addRow(self._quality)
        form.addRow("Minimum angle (deg):", self._min_angle)
        form.addRow(self._use_max_area)
        form.addRow("Max triangle area:", self._max_area)
        form.addRow(self._conforming)
        form.addRow("Max Steiner points (-1 = none):", self._max_steiner)
        form.addRow("Smoothing iterations:", self._smooth_iters)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> dict:
        return {
            "quality": self._quality.isChecked(),
            "min_angle": float(self._min_angle.value()),
            "max_area": float(self._max_area.value()) if self._use_max_area.isChecked() else None,
            "conforming_delaunay": self._conforming.isChecked(),
            "max_steiner": None if self._max_steiner.value() < 0 else int(self._max_steiner.value()),
            "smooth_iters": int(self._smooth_iters.value()),
        }
