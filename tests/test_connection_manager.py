from unittest.mock import AsyncMock, MagicMock

from app.services.connection_manager import ConnectionManager


def test_register_increases_active_count():
    manager = ConnectionManager()
    assert manager.active_count == 0
    manager.register("c1", MagicMock())
    manager.register("c2", MagicMock())
    assert manager.active_count == 2


def test_unregister_decreases_active_count():
    manager = ConnectionManager()
    manager.register("c1", MagicMock())
    manager.register("c2", MagicMock())
    manager.unregister("c1")
    assert manager.active_count == 1


def test_unregister_unknown_id_is_safe():
    manager = ConnectionManager()
    manager.unregister("yok")  # raise etmemeli
    assert manager.active_count == 0


def test_record_message_increments_counter():
    manager = ConnectionManager()
    assert manager.total_messages == 0
    manager.record_message()
    manager.record_message()
    assert manager.total_messages == 2


async def test_close_all_closes_every_connection_with_1001():
    manager = ConnectionManager()
    ws1, ws2 = MagicMock(), MagicMock()
    ws1.close = AsyncMock()
    ws2.close = AsyncMock()
    manager.register("c1", ws1)
    manager.register("c2", ws2)

    await manager.close_all(code=1001)

    ws1.close.assert_awaited_once_with(code=1001)
    ws2.close.assert_awaited_once_with(code=1001)
    assert manager.active_count == 0


async def test_close_all_tolerates_already_closed():
    manager = ConnectionManager()
    ws = MagicMock()
    ws.close = AsyncMock(side_effect=RuntimeError("zaten kapalı"))
    manager.register("c1", ws)

    # RuntimeError yutulmalı, exception fırlamamalı
    await manager.close_all(code=1001)
    assert manager.active_count == 0
