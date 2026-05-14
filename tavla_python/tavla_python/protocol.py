from dataclasses import dataclass
import json
import socket
import struct
from typing import Optional


@dataclass(frozen=True)
class Message:

    type: str
    content: str = ""

    # Mesaj nesnesini JSON için sözlük yapısına çevirir.
    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "content": self.content}

    # Sözlükten Message nesnesi oluşturur.
    @staticmethod
    def from_dict(data: dict) -> "Message":
        return Message(str(data.get("type", "")), str(data.get("content", "")))


class ProtocolError(RuntimeError):
    """Mesaj verisi beklenen formatta değilse çağrilir."""


# Socketten istenen byte sayısı tamamlanana kadar okuma yapar.
def _recv_exact(sock: socket.socket, byte_count: int) -> Optional[bytes]:

    chunks: list[bytes] = []
    remaining = byte_count
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


# Hazırlanan Message nesnesini uzunluk başlığıyla birlikte socket üzerinden gönderir.
def send_message(sock: socket.socket, message: Message) -> None:

    payload = json.dumps(message.to_dict(), ensure_ascii=False).encode("utf-8")
    header = struct.pack("!I", len(payload))
    sock.sendall(header + payload)


# Socketten gelen uzunluk başlığını ve JSON verisini okuyup Message nesnesine çevirir.
def receive_message(sock: socket.socket) -> Optional[Message]:

    header = _recv_exact(sock, 4)
    if header is None:
        return None
    (length,) = struct.unpack("!I", header)
    if length <= 0 or length > 10_000_000:
        raise ProtocolError(f"Geçersiz mesaj uzunluğu: {length}")
    payload = _recv_exact(sock, length)
    if payload is None:
        return None
    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ProtocolError("JSON mesajı çözümlenemedi") from exc
    if not isinstance(data, dict):
        raise ProtocolError("Mesaj sözlük formatında değil")
    return Message.from_dict(data)
