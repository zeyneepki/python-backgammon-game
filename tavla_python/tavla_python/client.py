import socket
import threading
from typing import Optional

from .protocol import Message, receive_message, send_message


class TavlaClient:

    # İstemci nesnesinin socket alanını ve gönderim kilidini hazırlar.
    def __init__(self) -> None:
        self.socket: Optional[socket.socket] = None
        self._send_lock = threading.Lock()

    # Verilen host ve porta bağlanmayı dener; başarılıysa True döner.
    def connect_to_server(self, host: str, port: int, timeout: float = 8.0) -> bool:
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.settimeout(None)
            self.socket = sock
            return True
        except OSError:
            self.socket = None
            return False

    # Sunucuya tek bir Message gönderir.
    def send_message(self, message: Message) -> None:
        if self.socket is None:
            raise ConnectionError("Sunucu bağlantısı yok")
        with self._send_lock:
            send_message(self.socket, message)

    # Sunucudan tek bir Message okur.
    def receive_message(self) -> Optional[Message]:
        if self.socket is None:
            raise ConnectionError("Sunucu bağlantısı yok")
        return receive_message(self.socket)

    # Açık socket bağlantısını güvenli şekilde kapatır.
    def close(self) -> None:
        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.socket.close()
            except OSError:
                pass
            self.socket = None
