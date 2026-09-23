from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

class DropZone(QWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFixedHeight(170)
        self.reset_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("Перетащите файлы в эту область")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""color: #b0b5be;font-size: 14px;font-weight: 600;letter-spacing: 0.5px;background: transparent;border: none;""")
        layout.addWidget(self.label)

        self.sub_label = QLabel("или нажмите для выбора фото и документов")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("""color: #7b8190;font-size: 11px;background: transparent;border: none;""")
        layout.addWidget(self.sub_label)

    def reset_style(self):
        self.setStyleSheet("""
            QWidget {background: rgba(33, 29, 27, 0.75);border: 2px dashed rgba(160, 165, 175, 0.35);border-radius: 16px; }""")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QWidget {background: rgba(46, 40, 36, 0.9);border: 2px dashed #b0b5be;border-radius: 16px; }""")
            self.label.setStyleSheet("color: #d1d5db; font-size: 14px; font-weight: 700; background: transparent; border: none;")

    def dragLeaveEvent(self, event):
        self.reset_style()
        self.label.setStyleSheet("color: #b0b5be; font-size: 14px; font-weight: 600; background: transparent; border: none;")

    def dropEvent(self, event: QDropEvent):
        self.reset_style()
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.label.setText(f"Подготовлено объектов: {len(paths)}")
            self.label.setStyleSheet("color: #d1d5db; font-size: 14px; font-weight: 700; background: transparent; border: none;")
            self.sub_label.setText("Нажмите «Отправить на телефон»")
            self.files_dropped.emit(paths)