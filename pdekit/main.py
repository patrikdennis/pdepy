from PyQt6.QtWidgets import QApplication
from pdekit.gui.main_window import MainWindow
import matplotlib.pyplot as plt
def main():
    plt.style.use("dark_background")
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()

if __name__ == '__main__':
    main()