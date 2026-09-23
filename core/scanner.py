import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtCore import QThread, pyqtSignal


def is_host_alive(ip: str) -> bool:
    """Быстрая проверка: отвечает ли устройство на 1 ICMP-пакет прямо сейчас"""
    try:
        # -n 1: один пакет, -w 250: таймаут 250 мс
        cmd = f"ping -n 1 -w 250 {ip}"
        res = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return res.returncode == 0
    except Exception:
        return False


class NetworkMonitorThread(QThread):
    devices_updated = pyqtSignal(list)

    def __init__(self, local_ip: str):
        super().__init__()
        self.local_ip = local_ip
        self.running = True

    def run(self):
        while self.running:
            raw_candidates = []
            ip_parts = self.local_ip.split('.')
            
            if len(ip_parts) == 4 and self.local_ip != '127.0.0.1':
                subnet_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}."

                try:
                    output = subprocess.check_output("arp -a", shell=True, text=True, errors="ignore")
                    for line in output.splitlines():
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            ip_cand, mac_cand = parts[0], parts[1]

                            # Фильтруем только адреса текущей подсети
                            if not ip_cand.startswith(subnet_prefix):
                                continue
                            if ip_cand.endswith(".255") or ip_cand.endswith(".1"):
                                continue
                            if ip_cand == self.local_ip:
                                continue

                            if '-' in mac_cand:
                                raw_candidates.append((ip_cand, mac_cand.upper()))
                except Exception:
                    pass

                # Проверяем кандидатов из ARP на реальный живой отклик
                alive_devices = []
                with ThreadPoolExecutor(max_workers=10) as executor:
                    check_results = executor.map(lambda c: (c[0], c[1], is_host_alive(c[0])), raw_candidates)
                    for ip, mac, alive in check_results:
                        if alive:
                            alive_devices.append((ip, mac, "Устройство в сети"))

                # Добавляем свой ПК
                alive_devices.insert(0, (self.local_ip, "LOCAL-HOST", "Этот компьютер (Хост)"))
                self.devices_updated.emit(alive_devices)
            else:
                self.devices_updated.emit([(self.local_ip, "LOCAL-HOST", "Этот компьютер (Хост)")])

            time.sleep(4)

    def stop(self):
        self.running = False