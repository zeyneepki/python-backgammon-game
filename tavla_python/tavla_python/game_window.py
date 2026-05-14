import queue
import threading
from typing import Callable

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox, QPushButton, QWidget

from .client import TavlaClient
from .end_screen import EndScreen
from .game_board import GameBoard
from .protocol import Message
from .ui_game_window import Ui_TavlaGameWindow

WHITE = 1
BROWN = 2


class TavlaGameWindow(QWidget):

    # Oyun ekranını, bağlantıyı, oyuncu rolünü ve ilk oyun durumunu hazırlar.
    def __init__(self, client: TavlaClient, player_role: int, on_back_to_menu: Callable[[], None]) -> None:
        super().__init__()
        self.setWindowTitle("Online Tavla - Python PyQt6")
        self.resize(1280, 620)
        self.setMinimumSize(1100, 560)

        self.client = client
        self.player_role = player_role
        self.on_back_to_menu = on_back_to_menu
        self.game = GameBoard()
        self.game.current_player = player_role

        self.selected_from = -1
        self.awaiting_to_selection = False
        self.active_dice: list[int] = []
        self.last_roll: list[int] = [0, 0, 0, 0]

        self.beyaz_kirik = 0
        self.kahverengi_kirik = 0
        self.white_off_count = 0
        self.brown_off_count = 0
        self.your_turn = False
        self._closing = False
        self._message_queue: queue.Queue[Message | None] = queue.Queue()

        self.point_buttons: dict[int, QPushButton] = {}
        self.end_screen: EndScreen | None = None

        self._load_ui()
        self.update_board_buttons()

        role_text = "Beyaz" if player_role == WHITE else "Kahverengi"
        self.log(f"Siz {role_text} Oyuncusunuz.")
        self.btn_roll.setEnabled(False)
        self.btn_white_return.setEnabled(False)
        self.btn_brown_return.setEnabled(False)

        threading.Thread(target=self._listen_from_server, daemon=True).start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._process_messages)
        self.timer.start(80)

    # Qt Designer .ui dosyasından üretilen arayüz sınıfını pencereye yerleştirir.
    def _load_ui(self) -> None:
        self.ui = Ui_TavlaGameWindow()
        self.ui.setupUi(self)

        # .ui içindeki bileşenleri eski kodun kullandığı kısa isimlere bağlarız.
        self.btn_roll = self.ui.btn_roll
        self.btn_leave = self.ui.btn_leave
        self.lbl_dice = self.ui.lbl_dice
        self.lbl_current_player = self.ui.lbl_current_player
        self.lbl_role_badge = self.ui.lbl_role_badge
        self.lbl_white_broken = self.ui.lbl_white_broken
        self.lbl_brown_broken = self.ui.lbl_brown_broken
        self.btn_white_return = self.ui.btn_white_return
        self.btn_brown_return = self.ui.btn_brown_return
        self.lbl_white_out = self.ui.lbl_white_out
        self.lbl_brown_out = self.ui.lbl_brown_out
        self.txt_log = self.ui.txt_log

        self.btn_roll.clicked.connect(self.roll_dice)
        self.btn_leave.clicked.connect(self.leave_game)
        self.btn_white_return.clicked.connect(self.return_white_piece)
        self.btn_brown_return.clicked.connect(self.return_brown_piece)

        self.ui.role_bar.setStyleSheet(
            f"background: {self._role_bg()}; border: 2px solid {self._role_border()}; color: {self._role_fg()};"
        )
        self.lbl_role_badge.setText(self._role_badge_text())
        self.lbl_role_badge.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self._role_fg()};")

        self.point_buttons = {}
        for index in range(1, 25):
            button = getattr(self.ui, f"btn{index}")
            button.clicked.connect(lambda checked=False, idx=index: self.handle_board_click(idx))
            self.point_buttons[index] = button

    # Oyun günlüğüne yeni satır ekler ve yazıyı en sona kaydırır.
    def log(self, text: str) -> None:
        self.txt_log.appendPlainText(text)
        self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())

    # Tahtadaki tüm butonları mevcut taş sayılarına göre yeniler.
    def update_board_buttons(self) -> None:
        for index in range(1, 25):
            value = self.game.get_board_value(index)
            button = self.point_buttons[index]
            prefix = self._point_header(index)
            is_own_point = (self.player_role == WHITE and value > 0) or (self.player_role == BROWN and value < 0)
            border_color = self._role_border() if is_own_point else "black"
            border_width = 3 if is_own_point else 1
            bg = "#ffcc66" if index % 2 else "#d5d78b"

            if value > 0:
                button.setText(prefix + self._stack_text("⚪", value))
            elif value < 0:
                button.setText(prefix + self._stack_text("🟤", -value))
            else:
                button.setText(prefix + "·")

            button.setStyleSheet(
                f"background: {bg}; border: {border_width}px solid {border_color}; "
                "font-weight: bold; text-align: center;"
            )

        self.lbl_white_broken.setText(f"Beyaz Taş: {self.beyaz_kirik}")
        self.lbl_brown_broken.setText(f"Kahverengi Taş: {self.kahverengi_kirik}")
        self.lbl_white_out.setText(f"Beyaz Çıkardı: {self.white_off_count}")
        self.lbl_brown_out.setText(f"Kahverengi Çıkardı: {self.brown_off_count}")
        self._refresh_return_buttons()

    # Bir noktadaki taş yığınını ekranda kısa sembol metni olarak hazırlar.
    @staticmethod
    def _stack_text(symbol: str, count: int) -> str:
        visible = min(count, 5)
        lines = [symbol] * visible
        if count > 5:
            lines.append(f"+{count - 5}")
        return "\n".join(lines)

    # Oyuncu rolünün okunabilir renk adını döndürür.
    def _role_name(self) -> str:
        return "Beyaz" if self.player_role == WHITE else "Kahverengi"

    # Oyuncu rolüne göre taş sembolünü döndürür.
    def _role_symbol(self) -> str:
        return "⚪" if self.player_role == WHITE else "🟤"

    # Oyuncu rolüne göre üst bilgi çubuğunun arka plan rengini döndürür.
    def _role_bg(self) -> str:
        return "#f7f7f7" if self.player_role == WHITE else "#5b3a29"

    # Oyuncu rolüne göre üst bilgi çubuğunun yazı rengini döndürür.
    def _role_fg(self) -> str:
        return "#111111" if self.player_role == WHITE else "#ffffff"

    # Oyuncu rolüne göre vurgu/kenarlık rengini döndürür.
    def _role_border(self) -> str:
        return "#2e86de" if self.player_role == WHITE else "#8e5a33"

    # Üst çubukta görünen oyuncu rozeti metnini üretir.
    def _role_badge_text(self) -> str:
        return f"SEN: {self._role_symbol()} {self._role_name().upper()}"

    # Tahta noktası başlığı olarak yalnızca nokta numarasını döndürür.
    @staticmethod
    def _point_header(index: int) -> str:
        return f"{index}\n"

    # Sunucudan gelen mesajları arka planda dinleyip kuyruğa koyar.
    def _listen_from_server(self) -> None:
        while not self._closing:
            try:
                msg = self.client.receive_message()
                self._message_queue.put(msg)
                if msg is None:
                    break
            except Exception:
                self._message_queue.put(None)
                break

    # Mesaj kuyruğunu Qt ana threadinde işler.
    def _process_messages(self) -> None:
        while True:
            try:
                msg = self._message_queue.get_nowait()
            except queue.Empty:
                break
            if msg is None:
                if not self._closing:
                    self.log("Sunucuyla bağlantı kesildi.")
                    QMessageBox.critical(self, "Bağlantı", "Sunucuyla bağlantı kesildi.")
                    self._return_to_menu_after_close()
                continue
            self._handle_server_message(msg)

    # Sunucudan gelen mesaj türüne göre oyun ekranını ve yerel durumu günceller.
    def _handle_server_message(self, msg: Message) -> None:
        if msg.type == "TURN_START":
            self.your_turn = True
            self.game.current_player = self.player_role
            self.btn_roll.setEnabled(True)
            self.lbl_current_player.setText("Sıra: Sizde")
            self.log("Sıra sizde!")
            self._refresh_return_buttons()
        elif msg.type == "TURN_END":
            self.your_turn = False
            self.game.current_player = BROWN if self.player_role == WHITE else WHITE
            self.btn_roll.setEnabled(False)
            self.btn_white_return.setEnabled(False)
            self.btn_brown_return.setEnabled(False)
            self.lbl_current_player.setText("Sıra: Rakibinizde")
            self.log("Rakibinizi bekleyin...")
        elif msg.type == "PLAYER_LEFT":
            self.log("Rakip oyundan ayrıldı!")
            QMessageBox.information(self, "Oyun", "Rakibiniz oyundan ayrıldı.")
            self._return_to_menu_after_close()
        elif msg.type == "MOVE":
            self.log(f"Rakibinizin hamlesi: {msg.content}")
            self.handle_opponent_move(msg.content)
        elif msg.type == "BROKEN_UPDATE":
            self._apply_broken_update(msg.content)
        elif msg.type == "OFF_UPDATE":
            self._apply_off_update(msg.content)
        elif msg.type == "DICE":
            self._show_opponent_dice(msg.content)
        elif msg.type == "GAME_OVER":
            winner = "Beyaz Oyuncu" if msg.content == "WHITE" else "Kahverengi Oyuncu"
            self.open_end_screen(winner)
        elif msg.type == "LOG":
            self.log(msg.content)
        else:
            self.log(f"Bilinmeyen mesaj türü: {msg.type}")

    # Sıra oyuncudaysa zar atar, aktif zar listesini kurar ve rakibe bildirir.
    def roll_dice(self) -> None:
        if not self.your_turn:
            self.log("Sıra sizde değil!")
            return

        self.btn_roll.setEnabled(False)
        z1, z2 = self.game.roll_dice()
        if z1 == z2:
            self.active_dice = [z1, z1, z1, z1]
            self.last_roll = [z1, z1, z1, z1]
            self.log(f"Oyuncu {self.player_role} çift zar attı!")
        else:
            self.active_dice = [z1, z2]
            self.last_roll = [z1, z2, 0, 0]

        self.lbl_dice.setText(f"Zarlar: {', '.join(map(str, self.active_dice))}")
        self.lbl_current_player.setText(f"Sıra: Sizde ({', '.join(map(str, self.active_dice))})")
        self.log(f"Zarlar atıldı: {z1} ve {z2}")

        if not self._can_play_with_broken_piece_if_needed():
            self.log("Çıkış yapılamıyor, sıra rakibe geçiyor!")
            self.active_dice.clear()
            self._send(Message("DICE", self._dice_payload()))
            self.end_turn()
            return

        self._send(Message("DICE", self._dice_payload()))
        self._refresh_return_buttons()

    # Tahta butonuna tıklanınca taş seçme veya hedefe oynama işlemini yönetir.
    def handle_board_click(self, index: int) -> None:
        if not self.your_turn:
            self.log("Sıra sizde değil!")
            return
        if not self.active_dice:
            self.log("Zar kullanmadınız. Önce zar atmalısınız!")
            return

        if not self.awaiting_to_selection:
            piece = self.game.get_board_value(index)
            if self._own_broken_count() > 0:
                self.log("Kırık taşın varken sadece onu çıkarabilirsin!")
                return
            if (self.player_role == WHITE and piece <= 0) or (self.player_role == BROWN and piece >= 0):
                self.log("Sadece kendi taşınızı seçebilirsiniz!")
                return
            self.selected_from = index
            self.awaiting_to_selection = True
            self.log(f"Taş seçildi: {index}")
            return

        from_index = self.selected_from
        to_index = index
        self.awaiting_to_selection = False
        self.selected_from = -1

        chosen_die = self._die_for_target(from_index, to_index)
        if chosen_die is None and self.is_bearing_off_move(from_index):
            chosen_die = self._die_for_bearing_off(from_index)
            if chosen_die is not None:
                self._bear_off_piece(from_index, chosen_die)
                return

        if chosen_die is None:
            self.log("Geçersiz hamle! Zarlarla uyumlu değil.")
            return

        if not (1 <= to_index <= 24):
            self.log("Geçersiz hedef.")
            return

        target_piece = self.game.get_board_value(to_index)
        if not self._target_is_open(target_piece):
            self.log("Geçersiz hamle! Hedef kapalı (2+ rakip taşı var).")
            return

        result = self.game.make_move(from_index, to_index, self.player_role)
        if result.captured_color:
            self._increment_broken(result.captured_color)
            self.send_broken_update(result.captured_color)

        self._consume_die(chosen_die)
        self.update_board_buttons()
        self.log(f"Taş {from_index} -> {to_index} hareket etti.")
        self._send(Message("MOVE", f"{from_index}->{to_index}:{self.player_role}"))
        self.after_successful_action()

    # Beyaz oyuncunun kırık taşını oyuna sokma isteğini başlatır.
    def return_white_piece(self) -> None:
        if self.player_role != WHITE or self.beyaz_kirik <= 0:
            return
        self._return_broken_piece(WHITE)

    # Kahverengi oyuncunun kırık taşını oyuna sokma isteğini başlatır.
    def return_brown_piece(self) -> None:
        if self.player_role != BROWN or self.kahverengi_kirik <= 0:
            return
        self._return_broken_piece(BROWN)

    # Kırık taşı uygun zar ve giriş noktasına göre tahtaya geri koyar.
    def _return_broken_piece(self, role: int) -> None:
        if not self.your_turn or not self.active_dice:
            return

        for die in list(self.active_dice):
            target = die if role == WHITE else 25 - die
            if 1 <= target <= 24 and self._target_is_open(self.game.get_board_value(target)):
                from_index = -1 if role == WHITE else -2
                result = self.game.make_move(from_index, target, role)
                if role == WHITE:
                    self.beyaz_kirik -= 1
                    color = "WHITE"
                else:
                    self.kahverengi_kirik -= 1
                    color = "BROWN"

                self._consume_die(die)
                self._send(Message("MOVE", f"{from_index}->{target}:{role}"))
                self.send_broken_update(color)
                if result.captured_color:
                    self._increment_broken(result.captured_color)
                    self.send_broken_update(result.captured_color)

                name = "Beyaz" if role == WHITE else "Kahverengi"
                self.log(f"{name} taş {target} konumuna çıkarıldı.")
                self.update_board_buttons()
                self.after_successful_action()
                return

        self.log("Çıkış yapılacak yer kapalı. Sıra geçiyor.")
        self.end_turn()

    # Ana menüye dönmeden önce rakibe oyundan ayrılma mesajı yollar.
    def leave_game(self) -> None:
        try:
            self._send(Message("PLAYER_LEFT", ""))
        except Exception:
            pass
        self._return_to_menu_after_close()

    # Pencere kapatılırken rakibe ayrılma mesajı yollayıp menüye döner.
    def closeEvent(self, event) -> None:  # noqa: N802
        if not self._closing:
            try:
                self._send(Message("PLAYER_LEFT", ""))
            except Exception:
                pass
            self._return_to_menu_after_close()
        event.accept()

    # Son zar atışını protokolün beklediği dört sayılık metne çevirir.
    def _dice_payload(self) -> str:
        return ",".join(str(x) for x in self.last_roll)

    # Oyuncunun kendi kırık taş sayısını döndürür.
    def _own_broken_count(self) -> int:
        return self.beyaz_kirik if self.player_role == WHITE else self.kahverengi_kirik

    # Hedef noktada hamle yapılabilir mi kontrol eder.
    def _target_is_open(self, target_piece: int) -> bool:
        if self.player_role == WHITE:
            return target_piece >= -1
        return target_piece <= 1

    # Normal hamlede hedef noktanın hangi zarla tutarlı olduğunu bulur.
    def _die_for_target(self, from_index: int, to_index: int) -> int | None:
        for die in self.active_dice:
            expected = from_index + die if self.player_role == WHITE else from_index - die
            if to_index == expected:
                return die
        return None

    # Taş çıkarma hamlesi için doğru zarı bulur.
    # Önce tam denk gelen zar kullanılır. Büyük zarla eksik/erken taş çıkarma
    # sadece tavla kuralına göre daha uzakta taş kalmadıysa yapılabilir.
    def _die_for_bearing_off(self, from_index: int) -> int | None:
        exact_die = self._exact_bearing_die(from_index)
        if exact_die in self.active_dice:
            return exact_die

        valid_big_dice: list[int] = []
        for die in self.active_dice:
            if self._can_bear_off_with_bigger_die(from_index, die):
                valid_big_dice.append(die)

        if not valid_big_dice:
            return None
        return min(valid_big_dice)

    # Seçilen pulun dışarı çıkması için tam gereken zar değerini hesaplar.
    def _exact_bearing_die(self, from_index: int) -> int:
        if self.player_role == WHITE:
            return 25 - from_index
        return from_index

    # Büyük zarla taş çıkarma kuralını kontrol eder.
    # Beyaz için seçilen noktadan daha geride, yani daha küçük numaralı evlerde,
    # beyaz taş kalmamalıdır. Kahverengi için daha büyük numaralı evlerde
    # kahverengi taş kalmamalıdır.
    def _can_bear_off_with_bigger_die(self, from_index: int, die: int) -> bool:
        needed_die = self._exact_bearing_die(from_index)
        if die <= needed_die:
            return False

        if self.player_role == WHITE:
            for point in range(19, from_index):
                if self.game.get_board_value(point) > 0:
                    return False
            return True

        for point in range(from_index + 1, 7):
            if self.game.get_board_value(point) < 0:
                return False
        return True

    # Kullanılan zarı aktif zar listesinden siler ve etiketleri yeniler.
    def _consume_die(self, die: int) -> None:
        try:
            self.active_dice.remove(die)
        except ValueError:
            pass
        dice_text = ", ".join(map(str, self.active_dice)) or "-"
        self.lbl_dice.setText(f"Kalan zarlar: {dice_text}")
        self.lbl_current_player.setText(f"Sıra: Sizde ({dice_text})")

    # Taşı tahtadan dışarı çıkarır, sayaçları günceller ve rakibe bildirir.
    def _bear_off_piece(self, from_index: int, die: int) -> None:
        if self.player_role == WHITE:
            self.game.set_board_value(from_index, self.game.get_board_value(from_index) - 1)
            self.white_off_count += 1
            color = "WHITE"
            self.log("Beyaz taş çıkarıldı.")
        else:
            self.game.set_board_value(from_index, self.game.get_board_value(from_index) + 1)
            self.brown_off_count += 1
            color = "BROWN"
            self.log("Kahverengi taş çıkarıldı.")

        self._consume_die(die)
        self.send_off_update(color, from_index)
        self.update_board_buttons()
        self.check_winner()
        self.after_successful_action()

    # Oyuncunun tüm taşları çıkış bölgesinde mi ve seçilen taş çıkarılabilir mi kontrol eder.
    def is_bearing_off_move(self, from_index: int) -> bool:
        if self.player_role == WHITE:
            for i in range(1, 19):
                if self.game.get_board_value(i) > 0:
                    return False
            return from_index >= 19
        for i in range(7, 25):
            if self.game.get_board_value(i) < 0:
                return False
        return from_index <= 6

    # Kırık taş varsa mevcut zarlarla giriş yapılabilir mi kontrol eder.
    def _can_play_with_broken_piece_if_needed(self) -> bool:
        if self.player_role == WHITE and self.beyaz_kirik > 0:
            return any(self.game.get_board_value(die) >= -1 for die in self.active_dice)
        if self.player_role == BROWN and self.kahverengi_kirik > 0:
            return any(self.game.get_board_value(25 - die) <= 1 for die in self.active_dice)
        return True

    # Kırık taş geri getirme düğmelerinin aktif/pasif durumunu yeniler.
    def _refresh_return_buttons(self) -> None:
        self.btn_white_return.setEnabled(self.your_turn and self.player_role == WHITE and self.beyaz_kirik > 0 and bool(self.active_dice))
        self.btn_brown_return.setEnabled(self.your_turn and self.player_role == BROWN and self.kahverengi_kirik > 0 and bool(self.active_dice))

    # Başarılı hamleden sonra sıranın bitip bitmediğini kontrol eder.
    def after_successful_action(self) -> None:
        self._refresh_return_buttons()
        if not self.active_dice:
            self.end_turn()

    # Aktif zarları sıfırlar, sırayı kapatır ve TURN_END mesajı gönderir.
    def end_turn(self) -> None:
        self.active_dice.clear()
        self.your_turn = False
        self.game.switch_player()
        self.btn_roll.setEnabled(False)
        self.btn_white_return.setEnabled(False)
        self.btn_brown_return.setEnabled(False)
        self.lbl_current_player.setText("Sıra: Rakibinizde")
        self.log("Hamleler bitti. Sıra değişti.")
        self._send(Message("TURN_END", ""))

    # Çıkarılan taş sayısı 15 olunca oyunu bitirir.
    def check_winner(self) -> None:
        if self.white_off_count >= 15:
            self._send(Message("GAME_OVER", "WHITE"))
            self.open_end_screen("Beyaz Oyuncu")
        elif self.brown_off_count >= 15:
            self._send(Message("GAME_OVER", "BROWN"))
            self.open_end_screen("Kahverengi Oyuncu")

    # Rakipten gelen hamle metnini çözümler ve yerel tahtaya uygular.
    def handle_opponent_move(self, move: str) -> None:
        try:
            if "->" not in move:
                self.log(f"Hatalı hamle formatı: {move}")
                return
            from_part, rest = move.split("->", 1)
            from_index = int(from_part)
            if ":" in rest:
                to_part, role_part = rest.split(":", 1)
                to_index = int(to_part)
                move_owner_role = int(role_part)
            else:
                to_index = int(rest)
                move_owner_role = BROWN if self.player_role == WHITE else WHITE

            if from_index in (-1, -2) and move_owner_role != self.player_role:
                if move_owner_role == WHITE:
                    self.beyaz_kirik = max(0, self.beyaz_kirik - 1)
                else:
                    self.kahverengi_kirik = max(0, self.kahverengi_kirik - 1)

            if 1 <= from_index <= 24 and ((move_owner_role == WHITE and to_index > 24) or (move_owner_role == BROWN and to_index < 1)):
                self.game.set_board_value(from_index, self.game.get_board_value(from_index) - (1 if move_owner_role == WHITE else -1))
                if move_owner_role == WHITE:
                    self.white_off_count += 1
                else:
                    self.brown_off_count += 1
            else:
                self.game.make_move(from_index, to_index, move_owner_role)
            self.update_board_buttons()
        except Exception as exc:
            self.log(f"Rakip hamlesi işlenemedi: {exc}")

    # Rakipten gelen kırık taş sayısı güncellemesini uygular.
    def _apply_broken_update(self, content: str) -> None:
        try:
            color, count_text = content.split(":", 1)
            count = int(count_text)
            if color == "WHITE":
                self.beyaz_kirik = count
            elif color == "BROWN":
                self.kahverengi_kirik = count
            self.update_board_buttons()
        except ValueError:
            self.log(f"BROKEN_UPDATE format hatası: {content}")

    # Rakipten gelen taş çıkarma güncellemesini uygular.
    def _apply_off_update(self, content: str) -> None:
        try:
            color, count_text, from_text = content.split(":", 2)
            count = int(count_text)
            from_index = int(from_text)
            if color == "WHITE":
                self.white_off_count = count
                self.game.set_board_value(from_index, self.game.get_board_value(from_index) - 1)
            elif color == "BROWN":
                self.brown_off_count = count
                self.game.set_board_value(from_index, self.game.get_board_value(from_index) + 1)
            self.update_board_buttons()
        except ValueError:
            self.log(f"OFF_UPDATE format hatası: {content}")

    # Rakibin zar bilgisini oyun günlüğünde gösterir.
    def _show_opponent_dice(self, content: str) -> None:
        try:
            parts = [int(x) for x in content.split(",")]
            while len(parts) < 4:
                parts.append(0)
            z1, z2, z3, _z4 = parts[:4]
            if z1 == z2 and z3 == z1:
                self.log(f"Rakip çift zar attı: {z1}")
            else:
                self.log(f"Rakip zar attı: {z1} ve {z2}")
        except ValueError:
            self.log(f"DICE format hatası: {content}")

    # Taş çıkarma sayısını OFF_UPDATE mesajı olarak gönderir.
    def send_off_update(self, color: str, from_index: int) -> None:
        count = self.white_off_count if color == "WHITE" else self.brown_off_count
        self._send(Message("OFF_UPDATE", f"{color}:{count}:{from_index}"))

    # Kırık taş sayısını BROKEN_UPDATE mesajı olarak gönderir.
    def send_broken_update(self, color: str) -> None:
        count = self.beyaz_kirik if color == "WHITE" else self.kahverengi_kirik
        self._send(Message("BROKEN_UPDATE", f"{color}:{count}"))

    # Belirtilen renkteki kırık taş sayacını bir artırır.
    def _increment_broken(self, color: str) -> None:
        if color == "WHITE":
            self.beyaz_kirik += 1
        elif color == "BROWN":
            self.kahverengi_kirik += 1

    # Mesajı istemci üzerinden güvenli şekilde sunucuya gönderir.
    def _send(self, msg: Message) -> None:
        try:
            self.client.send_message(msg)
        except Exception as exc:
            self.log(f"Mesaj gönderilemedi: {exc}")

    # Kazanan ekranını açar ve oyun ekranını kapatır.
    def open_end_screen(self, winner_name: str) -> None:
        if self._closing:
            return
        self._closing = True
        self.timer.stop()
        self.end_screen = EndScreen(winner_name, self.on_back_to_menu)
        self.end_screen.show()
        self.close()

    # Bağlantıyı kapatıp başlangıç menüsüne döner.
    def _return_to_menu_after_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.timer.stop()
        self.client.close()
        self.close()
        self.on_back_to_menu()
