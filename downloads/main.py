import sys
import threading
from PyQt6.QtWidgets import QApplication

from core.server import start_server
from ui.main_window import MainWindow


def main():
    # Запуск фонового веб-сервера
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Запуск оконного интерфейса
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()