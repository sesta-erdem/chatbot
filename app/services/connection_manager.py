import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Aktif WebSocket bağlantılarını izler.
    - active_count: gauge metric kaynağı (anlık aktif bağlantı sayısı)
    - total_messages: counter metric kaynağı (kümülatif işlenen mesaj sayısı)
    - close_all: graceful shutdown'da tüm bağlantılara 1001 (going away) gönderir
    """

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self.total_messages = 0

    def register(self, connection_id: str, websocket: WebSocket) -> None:
        self._connections[connection_id] = websocket
        logger.info(f"Bağlantı eklendi (aktif={self.active_count})")

    def unregister(self, connection_id: str) -> None:
        self._connections.pop(connection_id, None)
        logger.info(f"Bağlantı çıkarıldı (aktif={self.active_count})")

    def record_message(self) -> None:
        self.total_messages += 1

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def close_all(self, code: int = 1001) -> None:
        logger.info(f"Tüm bağlantılar kapatılıyor (aktif={self.active_count}, code={code})")
        for connection_id, websocket in list(self._connections.items()):
            try:
                await websocket.close(code=code)
            except RuntimeError:
                # Bağlantı zaten kapalıysa sessizce geç
                pass
        self._connections.clear()
