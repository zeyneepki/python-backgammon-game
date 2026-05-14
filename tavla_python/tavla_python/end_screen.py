from typing import Callable

from PyQt6.QtWidgets import QWidget

from .ui_end_screen import Ui_EndScreen


class EndScreen(QWidget):

    # Kazanan adını ve tekrar oynama callback fonksiyonunu alarak pencereyi hazırlar.
    def __init__(self, winner_name: str, on_replay: Callable[[], None]) -> None:
        super().__init__()
        self.on_replay = on_replay
        self._load_ui(winner_name)

    # Qt Designer .ui dosyasından üretilen arayüzü kurar ve kazanan yazısını yerleştirir.
    def _load_ui(self, winner_name: str) -> None:
        self.ui = Ui_EndScreen()
        self.ui.setupUi(self)
        self.ui.lbl_winner.setText(f"{winner_name} kazandı! Tebrikler!")
        self.ui.btn_replay.clicked.connect(self._replay)

    # Bitiş ekranını kapatır ve başlangıç ekranını yeniden gösterir.
    def _replay(self) -> None:
        self.close()
        self.on_replay()

    # Pencere çarpı ile kapatılırsa da menüye dönülmesini sağlar.
    def closeEvent(self, event) -> None:  # noqa: N802
        self.on_replay()
        event.accept()
