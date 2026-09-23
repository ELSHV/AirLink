import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.server import start_server

def main():
    start_server()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()