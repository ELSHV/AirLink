import os
import sys
import threading
import subprocess
from datetime import datetime
from io import BytesIO
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QIcon
import requests
import qrcode
from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget,QPushButton, QFrame, QStackedWidget,QListWidget, QListWidgetItem, QGraphicsDropShadowEffect, QFileDialog, QSpacerItem, QSizePolicy)
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter
from PyQt6.QtCore import Qt
from config import PORT, DOWNLOADS_DIR, signals
from core.network import get_local_ip
from ui.drop_zone import DropZone






def get_resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

def add_soft_shadow(widget, blur=24, alpha=70):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setColor(QColor(15, 12, 10, alpha))
    shadow.setOffset(0, 6)
    widget.setGraphicsEffect(shadow)

class BackgroundWidget(QWidget):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.bg_pixmap = QPixmap(image_path)

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.fillRect(self.rect(), QColor(26, 22, 20, 180))
        else:
            painter.fillRect(self.rect(), QColor(26, 22, 20))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AirLink — Локальная передача файлов")
        self.setFixedSize(760, 640)
        
        icon_path = get_resource_path(os.path.join("ui", "icon.ico"))
        self.setWindowIcon(QIcon(icon_path))

        self.staged_files = []
        self.local_ip = get_local_ip()
        self.connected_devices_history = []

        self.init_ui()

        signals.log_msg.connect(self.handle_log_msg)
        signals.files_received.connect(self.on_files_received)

    def init_ui(self):
        bg_image_path = get_resource_path(os.path.join("ui", "login_back.jpg"))

        root = BackgroundWidget(bg_image_path, self)
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(16)

        sidebar = QFrame()
        sidebar.setFixedWidth(190)
        sidebar.setStyleSheet("""
            QFrame {
                background: rgba(36, 31, 28, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
            }
        """)
        add_soft_shadow(sidebar)
        side_l = QVBoxLayout(sidebar)
        side_l.setContentsMargins(16, 22, 16, 22)
        side_l.setSpacing(10)

        logo = QLabel("AIRLINK")
        logo.setStyleSheet("font-size: 15px; font-weight: 800; letter-spacing: 3px; color: #d1d5db; border:none; background:transparent;")
        side_l.addWidget(logo)

        sub_logo = QLabel("ЛОКАЛЬНАЯ СЕТЬ")
        sub_logo.setStyleSheet("font-size: 9px; font-weight: 700; letter-spacing: 2px; color: #8c92a4; border:none; background:transparent; margin-bottom: 14px;")
        side_l.addWidget(sub_logo)

        self.btn_nav_dash = QPushButton("Главная")
        self.btn_nav_storage = QPushButton("Хранилище")
        self.btn_nav_nodes = QPushButton("Устройства")

        self.nav_buttons = [self.btn_nav_dash, self.btn_nav_storage, self.btn_nav_nodes]
        for i, btn in enumerate(self.nav_buttons):
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, idx=i: self.switch_page(idx))
            side_l.addWidget(btn)

        side_l.addStretch()
        main_layout.addWidget(sidebar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        page_dash = QWidget()
        p_dash_l = QVBoxLayout(page_dash)
        p_dash_l.setContentsMargins(0, 0, 0, 0)
        p_dash_l.setSpacing(14)

        qr_card = QFrame()
        qr_card.setFixedHeight(170)
        qr_card.setStyleSheet("background: rgba(38, 33, 30, 0.82); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px;")
        add_soft_shadow(qr_card)
        
        qr_card_layout = QHBoxLayout(qr_card)
        qr_card_layout.setContentsMargins(28, 12, 28, 12)

        qr_text_box = QVBoxLayout()
        qr_text_box.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        qr_title = QLabel("Сканируйте QRCode")
        qr_title.setStyleSheet("font-size: 19px; font-weight: 700; letter-spacing: 0.5px; color: #d1d5db; border: none; background: transparent;")
        qr_subtitle = QLabel("для подключения телефона")
        qr_subtitle.setStyleSheet("font-size: 12px; color: #8c909e; border: none; background: transparent; margin-top: 4px;")
        qr_text_box.addWidget(qr_title)
        qr_text_box.addWidget(qr_subtitle)
        qr_card_layout.addLayout(qr_text_box)

        qr_card_layout.addStretch()

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setStyleSheet("border: none; background: transparent;")
        qr_card_layout.addWidget(self.qr_label)
        self.render_qr(box_size=3)

        p_dash_l.addWidget(qr_card)

        transfer_island = QFrame()
        transfer_island.setStyleSheet("background: rgba(38, 33, 30, 0.88); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px;")
        add_soft_shadow(transfer_island)
        t_layout = QVBoxLayout(transfer_island)
        t_layout.setContentsMargins(22, 22, 22, 22)
        t_layout.setSpacing(0)

        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.on_files_staged)
        self.drop_zone.mousePressEvent = self.open_file_dialog
        t_layout.addWidget(self.drop_zone)

        t_layout.addSpacerItem(QSpacerItem(20, 24, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        self.btn_send = QPushButton("Отправить на телефон")
        self.btn_send.setFixedHeight(48)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: #525662;
                color: #e5e7eb;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 1px;
                border: none;
            }
            QPushButton:hover {
                background: #636875;
            }
            QPushButton:disabled {
                background: rgba(255, 255, 255, 0.05);
                color: #555b68;
            }
        """)
        self.btn_send.setEnabled(False)
        self.btn_send.clicked.connect(self.send_to_device)
        t_layout.addWidget(self.btn_send)

        p_dash_l.addWidget(transfer_island, 1)
        self.stack.addWidget(page_dash)

        page_storage = QWidget()
        p_store_l = QVBoxLayout(page_storage)
        p_store_l.setContentsMargins(0, 0, 0, 0)
        p_store_l.setSpacing(14)

        store_header = QHBoxLayout()
        store_title = QLabel("Полученные файлы")
        store_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #d1d5db;")
        store_header.addWidget(store_title)
        store_header.addStretch()

        btn_open_folder = QPushButton("Открыть папку на диске")
        btn_open_folder.setFixedHeight(34)
        btn_open_folder.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: #c5cbd3;
                font-size: 11px;
                font-weight: 600;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
            }
        """)
        btn_open_folder.clicked.connect(lambda: subprocess.Popen(f'explorer "{DOWNLOADS_DIR}"'))
        store_header.addWidget(btn_open_folder)
        p_store_l.addLayout(store_header)

        self.storage_list = QListWidget()
        self.storage_list.setStyleSheet("""
            QListWidget {
                background: rgba(38, 33, 30, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 10px;
                color: #b0b5be;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 8px;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.06);
            }
        """)
        self.storage_list.itemDoubleClicked.connect(self.open_selected_file)
        p_store_l.addWidget(self.storage_list)
        self.stack.addWidget(page_storage)

        page_history = QWidget()
        p_hist_l = QVBoxLayout(page_history)
        p_hist_l.setContentsMargins(0, 0, 0, 0)
        p_hist_l.setSpacing(14)

        hist_box = QFrame()
        hist_box.setStyleSheet("background: rgba(38, 33, 30, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px;")
        add_soft_shadow(hist_box)
        hb_l = QVBoxLayout(hist_box)
        hb_l.setContentsMargins(20, 18, 20, 18)
        hb_l.setSpacing(12)

        hb_title = QLabel("ИСТОРИЯ ПОДКЛЮЧЕНИЙ УСТРОЙСТВ")
        hb_title.setStyleSheet("font-size: 12px; font-weight: 700; letter-spacing: 1.5px; color: #9499a5; border: none; background: transparent;")
        hb_l.addWidget(hb_title)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                background: rgba(24, 20, 18, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 10px;
                padding: 8px;
                color: #b0b5be;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 6px;
            }
        """)
        hb_l.addWidget(self.history_list)
        p_hist_l.addWidget(hist_box)

        self.stack.addWidget(page_history)

        main_layout.addWidget(self.stack, 1)

        self.switch_page(0)
        self.refresh_storage()

    def handle_log_msg(self, msg, color):
        if msg.startswith("device_connected:"):
            device_str = msg.replace("device_connected:", "")
            now = datetime.now().strftime("%H:%M:%S")
            entry = f"[{now}] {device_str}"
            if not any(device_str in item for item in self.connected_devices_history):
                self.connected_devices_history.insert(0, entry)
                self.refresh_history_ui()

    def refresh_history_ui(self):
        self.history_list.clear()
        if not self.connected_devices_history:
            self.history_list.addItem("Список пуст. Устройства появятся после сканирования QR-кода.")
        else:
            for entry in self.connected_devices_history:
                self.history_list.addItem(QListWidgetItem(entry))

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.12);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        border-radius: 10px;
                        color: #ffffff;
                        font-size: 12px;
                        font-weight: 600;
                        text-align: left;
                        padding-left: 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        border-radius: 10px;
                        color: #7b8190;
                        font-size: 12px;
                        font-weight: 500;
                        text-align: left;
                        padding-left: 14px;
                    }
                    QPushButton:hover {
                        color: #d1d5db;
                        background: rgba(255, 255, 255, 0.04);
                    }
                """)

        if index == 1:
            self.refresh_storage()
        elif index == 2:
            self.refresh_history_ui()

    def refresh_storage(self):
        self.storage_list.clear()
        if os.path.exists(DOWNLOADS_DIR):
            files = [f for f in os.listdir(DOWNLOADS_DIR) if not f.startswith('.')]
            if not files:
                self.storage_list.addItem("В папке downloads пока нет файлов")
            for f in files:
                fpath = os.path.join(DOWNLOADS_DIR, f)
                size_mb = os.path.getsize(fpath) / (1024 * 1024)
                item = QListWidgetItem(f"{f}  ({size_mb:.2f} МБ)")
                item.setData(Qt.ItemDataRole.UserRole, fpath)
                self.storage_list.addItem(item)

    def open_selected_file(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            os.startfile(path)

    def render_qr(self, box_size=3):
        qr = qrcode.QRCode(box_size=box_size, border=1)
        qr.add_data(f"http://{self.local_ip}:{PORT}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="#241f1c", back_color="#c5cbd3")
        buf = BytesIO()
        img.save(buf, format="PNG")
        qimage = QImage.fromData(buf.getvalue())
        self.qr_label.setPixmap(QPixmap.fromImage(qimage))

    def open_file_dialog(self, event):
        paths, _ = QFileDialog.getOpenFileNames(self, "Выбрать файлы для передачи")
        if paths:
            self.on_files_staged(paths)
            self.drop_zone.label.setText(f"Подготовлено объектов: {len(paths)}")
            self.drop_zone.label.setStyleSheet("color: #d1d5db; font-size: 14px; font-weight: 700; background: transparent; border: none;")
            self.drop_zone.sub_label.setText("Нажмите «Отправить на телефон»")

    def on_files_staged(self, paths):
        self.staged_files = paths
        self.btn_send.setEnabled(True)

    def send_to_device(self):
        self.btn_send.setEnabled(False)
        self.btn_send.setText("Отправка...")

        def worker():
            try:
                files_payload = [('files', (os.path.basename(p), open(p, 'rb'))) for p in self.staged_files]
                r = requests.post(f"http://127.0.0.1:{PORT}/api/prepare-pc-files", files=files_payload)
                if r.status_code == 200:
                    pass
            except Exception:
                pass
            finally:
                self.staged_files = []
                self.drop_zone.label.setText("Перетащите файлы в эту область")
                self.drop_zone.label.setStyleSheet("color: #b0b5be; font-size: 14px; font-weight: 600; background: transparent; border: none;")
                self.drop_zone.sub_label.setText("или нажмите для выбора фото и документов")
                self.btn_send.setText("Отправить на телефон")

        threading.Thread(target=worker, daemon=True).start()

    def on_files_received(self, count):
        self.refresh_storage()