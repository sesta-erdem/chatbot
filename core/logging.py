import logging


class ConnectionLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        connection_id = self.extra.get("connection_id", "-")
        return f"{connection_id}: {msg}", kwargs


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
