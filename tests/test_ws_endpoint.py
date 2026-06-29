"""WS endpoint entegrasyon testleri (JWT auth + IDOR)."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ORIGIN, OTHER_USER_ID, USER_TOKEN, FakeProvider


def ws_connect(client: TestClient, token: str = USER_TOKEN, origin: str = ORIGIN, conversation_id=None):
    url = f"/ws?token={token}"
    if conversation_id is not None:
        url += f"&conversation_id={conversation_id}"
    return client.websocket_connect(url, headers={"origin": origin})


def send_msg(ws, content: str):
    ws.send_json({"type": "user_message", "content": content})


def collect_until_done(ws) -> tuple[str, str]:
    parts = []
    while True:
        data = ws.receive_json()
        t = data["type"]
        if t == "conversation":
            continue
        if t == "chunk":
            parts.append(data["content"])
        elif t == "done":
            return "".join(parts), "done"
        elif t in ("error", "system"):
            return data.get("content", ""), t


def read_conversation_id(ws) -> str:
    data = ws.receive_json()
    assert data["type"] == "conversation"
    return data["conversation_id"]


# --- auth / origin ---

def test_invalid_jwt_rejected(client):
    with pytest.raises(Exception):
        with ws_connect(client, token="not.a.valid.jwt"):
            pass


def test_missing_token_rejected(client):
    with pytest.raises(Exception):
        with ws_connect(client, token=""):
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
        _, mtype = collect_until_done(ws)
    assert mtype == "system"


def test_too_long_message_returns_system(client):
    with ws_connect(client) as ws:
        send_msg(ws, "x" * 2001)
        _, mtype = collect_until_done(ws)
    assert mtype == "system"


# --- IDOR: başkasının konuşmasına bağlanamamalı ---

def test_cannot_attach_to_another_users_conversation(client, conv_repo):
    # OTHER_USER'a ait bir konuşma (senkron seed)
    others_cid = conv_repo.seed_conversation(OTHER_USER_ID)
    # USER bu conversation_id ile bağlanmaya çalışır → sahip olmadığı için YENİ konuşma açılmalı
    with ws_connect(client, conversation_id=others_cid) as ws:
        new_cid = read_conversation_id(ws)
    assert new_cid != str(others_cid)


# --- health / metrics ---

def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["gemini_client"] is True


def test_metrics_counts_active_connection(client):
    with ws_connect(client):
        assert client.get("/metrics").json()["active_connections"] == 1
    assert client.get("/metrics").json()["active_connections"] == 0
