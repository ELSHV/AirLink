import os
from PyQt6.QtCore import QObject, pyqtSignal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

PORT = 8000


class TransferSignals(QObject):
    log_msg = pyqtSignal(str, str)
    files_received = pyqtSignal(int)


signals = TransferSignals()
active_sessions = {}