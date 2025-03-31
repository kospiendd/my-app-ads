# main.py
import sys
from PyQt5.QtWidgets import QApplication
from ui import KiwoomApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KiwoomApp()
    window.show()
    sys.exit(app.exec_())
