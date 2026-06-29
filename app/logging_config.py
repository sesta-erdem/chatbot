import logging

from app.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


class ConnectionLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        connection_id = self.extra.get("connection_id", "-")
        user_id = self.extra.get("user_id", "-")
        return f"[user={user_id} conn={connection_id}] {msg}", kwargs
