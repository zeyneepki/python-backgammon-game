import argparse
import threading

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget

from .client import TavlaClient
from .game_window import TavlaGameWindow
from .ui_start_screen import Ui_StartScreen

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000

#Arka plan bağlantı threadinden Qt arayüzüne güvenli sinyal taşır.
class _ConnectionSignals(QObject):

    role_ready = pyqtSignal(object, int)
    failed = pyqtSignal(str)
    status = pyqtSignal(str)


class StartScreen(QWidget):

    # Başlangıç penceresini, varsayılan IP/port değerlerini ve sinyalleri hazırlar.
    def __init__(self, default_host: str = DEFAULT_HOST, default_port: int = DEFAULT_PORT) -> None:
        super().__init__()
        self.default_host = default_host
        self.default_port = default_port
        self.client: TavlaClient | None = None
        self.game_window: TavlaGameWindow | None = None

        self.signals = _ConnectionSignals()
        self.signals.role_ready.connect(self._open_game)
        self.signals.failed.connect(self._connection_failed)
        self.signals.status.connect(self._set_status)

        self._load_ui()

    # Qt Designer .ui dosyasından üretilen arayüz sınıfını pencereye yerleştirir.
    def _load_ui(self) -> None:
        self.ui = Ui_StartScreen()
        self.ui.setupUi(self)
        self.host_edit = self.ui.host_edit
        self.port_edit = self.ui.port_edit
        self.status_label = self.ui.status_label
        self.btn_start = self.ui.btn_start
        self.host_edit.setText(self.default_host)
        self.port_edit.setText(str(self.default_port))
        self.btn_start.clicked.connect(self.start_game)

    # Kullanıcının girdiği IP/port ile bağlantı sürecini arka planda başlatır.
    def start_game(self) -> None:
        host = self.host_edit.text().strip() or DEFAULT_HOST
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            QMessageBox.critical(self, "Port", "Port sayısal olmalıdır.")
            return

        self.btn_start.setEnabled(False)
        self.status_label.setText("Oyuncu bekleniyor...")
        threading.Thread(target=self._connect_and_wait_role, args=(host, port), daemon=True).start()

    # Arka planda sunucuya bağlanır ve ROLE mesajı gelene kadar diğer oyuncuyu bekler.
    def _connect_and_wait_role(self, host: str, port: int) -> None:
        client = TavlaClient()
        if not client.connect_to_server(host, port):
            self.signals.failed.emit("Sunucuya bağlanılamadı.")
            return

        self.signals.status.emit("Oyuncu bekleniyor...")
        try:
            while True:
                msg = client.receive_message()
                if msg is None:
                    raise ConnectionError("Sunucu bağlantıyı kapattı.")
                if msg.type == "ROLE":
                    self.client = client
                    self.signals.role_ready.emit(client, int(msg.content))
                    return
        except Exception as exc:
            client.close()
            self.signals.failed.emit(str(exc))

    # Durum yazısını güvenli şekilde günceller.
    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    # Bağlantı hatasında butonu tekrar açar ve kullanıcıya hata gösterir.
    def _connection_failed(self, detail: str) -> None:
        self.btn_start.setEnabled(True)
        self.status_label.setText("Bağlantı başarısız.")
        QMessageBox.critical(self, "Hata", detail)

    # Başlangıç ekranını gizleyip asıl tavla oyun penceresini açar.
    def _open_game(self, client: TavlaClient, role: int) -> None:
        self.hide()
        self.status_label.setText("Oyun başladı.")
        self.btn_start.setEnabled(True)
        self.game_window = TavlaGameWindow(client, role, self.show_menu)
        self.game_window.show()

    # Oyun ekranından çıkılınca başlangıç ekranını tekrar gösterir.
    def show_menu(self) -> None:
        self.show()
        self.status_label.setText("Yeni oyun için bağlanabilirsiniz.")
        self.btn_start.setEnabled(True)


# Komut satırı ayarlarını okuyup Qt uygulamasını başlatır.
def main() -> None:
    parser = argparse.ArgumentParser(description="Qt Online Tavla İstemcisi")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bağlanılacak sunucu IP/host")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help="Bağlanılacak port")
    args = parser.parse_args()

    app = QApplication.instance() or QApplication([])
    window = StartScreen(args.host, args.port)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
