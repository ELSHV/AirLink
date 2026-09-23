import os
from PyQt6.QtCore import QObject, pyqtSignal

PORT = 8000
DOWNLOADS_DIR = os.path.abspath("downloads")

class AppSignals(QObject):
    log_msg = pyqtSignal(str, str)
    files_received = pyqtSignal(int)

signals = AppSignals()
active_sessions = {}