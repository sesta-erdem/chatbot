"""
WS endpoint entegrasyon testleri.
GeminiProvider yerine FakeProvider kullanmak için ws.py'de
GeminiProvider'ı monkeypatch ile değiştiriyoruz.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TOKEN, ORIGIN, FakeProvider


def ws_connect(client: TestClient, token: str = TOKEN, origin: str = ORIGIN):
    return client.websocket_connect(f"/ws?token={token}", headers={"origin": origin})


def send_msg(ws, content: str):
    ws.send_json({"type": "user_message", "content": content})


def collect_until_done(ws) -> tuple[str, str]:
    """chunk'ları birleştir, done/error/system'de dur. (text, final_type) döndür."""
    parts = []
    while True:
        data = ws.receive_json()
        t = data["type"]
        if t == "chunk":
            parts.append(data["content"])
        elif t == "done":
            return "".join(parts), "done"
        elif t in ("error", "system"):
            return data.get("content", ""), t


# --- auth / origin ---

def test_wrong_token_rejected(client):
    with pytest.raises(Exception):
        with ws_connect(client, token="yanlis-token"):
            pass


def test_wrong_origin_rejected(client):
    with pytest.raises(Exception):
        with ws_connect(client, origin="http://evil.com"):
            pass


# --- happy path ---

def test_normal_message_returns_done(client):
    provider = FakeProvider(chunks=["test ", "yanıt"])
    with patch("app.routers.ws.GeminiProvider", return_value=provider):
        with ws_connect(client) as ws:
            send_msg(ws, "merhaba")
            text, mtype = collect_until_done(ws)
    assert mtype == "done"
    assert text == "test yanıt"


# --- validation ---

def test_empty_message_returns_system(client):
    with ws_connect(client) as ws:
        send_msg(ws, "   ")
        text, mtype = collect_until_done(ws)
    assert mtype == "system"


def test_too_long_message_returns_system(client):
    with ws_connect(client) as ws:
        send_msg(ws, "x" * 2001)
        text, mtype = collect_until_done(ws)
    assert mtype == "system"


def test_invalid_json_returns_error_and_connection_survives(client):
    provider = FakeProvider(chunks=["hâlâ çalışıyorum"])
    with patch("app.routers.ws.GeminiProvider", return_value=provider):
        with ws_connect(client) as ws:
            ws.send_text("bu json değil {{{")
            _, mtype1 = collect_until_done(ws)
            assert mtype1 == "error"

            # Bağlantı hâlâ canlı
            send_msg(ws, "test")
            text2, mtype2 = collect_until_done(ws)
            assert mtype2 == "done"
            assert "hâlâ çalışıyorum" in text2


# --- health endpoint ---

def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["gemini_client"] is True


# --- metrics ---

def test_metrics_endpoint_reports_zero_initially(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_connections"] == 0
    assert body["total_messages"] == 0


def test_metrics_counts_active_connection(client):
    with ws_connect(client):
        resp = client.get("/metrics")
        body = resp.json()
        assert body["active_connections"] == 1
    # Bağlantı kapandıktan sonra düşmeli
    resp = client.get("/metrics")
    assert resp.json()["active_connections"] == 0


def test_metrics_counts_total_messages(client):
    provider = FakeProvider(chunks=["ok"])
    with patch("app.routers.ws.GeminiProvider", return_value=provider):
        with ws_connect(client) as ws:
            send_msg(ws, "bir")
            collect_until_done(ws)
            send_msg(ws, "iki")
            collect_until_done(ws)
    resp = client.get("/metrics")
    assert resp.json()["total_messages"] == 2
