import argparse
import queue
import socket
import threading
from dataclasses import dataclass

from .protocol import Message, receive_message, send_message

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5000


@dataclass
class PlayerConnection:
    socket: socket.socket
    address: tuple[str, int]
    send_lock: threading.Lock

    # Bu oyuncuya Message gönderir.
    def send(self, message: Message) -> None:
        with self.send_lock:
            send_message(self.socket, message)

    # Bu oyuncudan Message okur.
    def receive(self) -> Message | None:
        return receive_message(self.socket)

    # Oyuncunun socket bağlantısını kapatır.
    def close(self) -> None:
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.socket.close()
        except OSError:
            pass


class GameSession(threading.Thread):

    # İki oyunculu oyun oturumunu hazırlar.
    def __init__(self, player1: PlayerConnection, player2: PlayerConnection) -> None:
        super().__init__(daemon=True)
        self.player1 = player1
        self.player2 = player2
        self._incoming: queue.Queue[tuple[PlayerConnection, Message | None]] = queue.Queue()
        self._active = True

    # Oyunculara rol verir, iki oyuncuyu da aynı anda dinler ve sıra yönetimini yapar.
    def run(self) -> None:
        print("Yeni oyun başlatıldı.")
        try:
            self.player1.send(Message("ROLE", "1"))
            self.player2.send(Message("ROLE", "2"))

            self.player1.send(Message("TURN_START", ""))
            self.player2.send(Message("TURN_END", ""))

            threading.Thread(target=self._listen_player, args=(self.player1,), daemon=True).start()
            threading.Thread(target=self._listen_player, args=(self.player2,), daemon=True).start()

            self._message_loop()
        except OSError:
            print("Bir oyuncu bağlantıyı kesti.")
        finally:
            self._active = False
            self.player1.close()
            self.player2.close()

    # Belirtilen oyuncudan gelen mesajları sürekli okuyup ortak kuyruğa koyar.
    def _listen_player(self, player: PlayerConnection) -> None:
        while self._active:
            try:
                msg = player.receive()
            except OSError:
                msg = None
            except Exception:
                msg = None

            self._incoming.put((player, msg))
            if msg is None:
                return

    # Kuyruğa düşen mesajları işler; rakip ayrılırsa sırayı beklemeden anında bildirir.
    def _message_loop(self) -> None:
        current = self.player1
        other = self.player2

        while self._active:
            sender, msg = self._incoming.get()
            receiver = self._other_player(sender)

            if msg is None or msg.type == "PLAYER_LEFT":
                self._notify_player_left(receiver)
                return

            # Sıra kimdeyse yalnız onun oyun mesajları işlenir.
            # Böylece rakip sırada değilken hamle/zar mesajı gönderemez.
            if sender is not current:
                continue

            try:
                other.send(msg)
            except OSError:
                return

            if msg.type == "TURN_END":
                try:
                    other.send(Message("TURN_START", ""))
                    current.send(Message("TURN_END", ""))
                except OSError:
                    return
                current, other = other, current

    # Verilen oyuncunun rakibini döndürür.
    def _other_player(self, player: PlayerConnection) -> PlayerConnection:
        return self.player2 if player is self.player1 else self.player1

    # Oyunculardan biri ayrıldığında rakibe PLAYER_LEFT mesajı gönderir.
    def _notify_player_left(self, receiver: PlayerConnection) -> None:
        try:
            receiver.send(Message("PLAYER_LEFT", ""))
        except OSError:
            pass


class TavlaServer:

    # Sunucunun dinleyeceği host, port ve bekleme kuyruğunu hazırlar.
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self.waiting_players: queue.Queue[PlayerConnection] = queue.Queue()

    # Yeni bağlantıları kabul eder, iki oyuncu gelince yeni oyun oturumu başlatır.
    def serve_forever(self) -> None:
        print(f"Sunucu başlatılıyor: {self.host}:{self.port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen()

            while True:
                client_socket, address = server_socket.accept()
                print(f"Yeni oyuncu bağlandı: {address[0]}:{address[1]}")
                player = PlayerConnection(client_socket, address, threading.Lock())
                self.waiting_players.put(player)

                if self.waiting_players.qsize() >= 2:
                    player1 = self.waiting_players.get()
                    player2 = self.waiting_players.get()
                    GameSession(player1, player2).start()


# Komut satırı ayarlarını okuyup sunucuyu başlatır.
def main() -> None:
    parser = argparse.ArgumentParser(description="Python Online Tavla Sunucusu")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Dinlenecek host/IP")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help="Dinlenecek port")
    args = parser.parse_args()
    TavlaServer(args.host, args.port).serve_forever()


if __name__ == "__main__":
    main()
