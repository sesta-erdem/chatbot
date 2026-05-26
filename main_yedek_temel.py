import os
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))



app = FastAPI()


html = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket Chat</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            background: #000000;
            color: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }

        .chat-container {
            width: min(780px, 94vw);
            height: min(760px, 92vh);
            background: #000000;
            border: 2px solid #ffffff;
            border-radius: 18px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 0 28px rgba(255, 255, 255, 0.08);
        }

        .chat-header {
            padding: 24px 28px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.28);
            background: #000000;
        }

        .chat-header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 400;
            letter-spacing: -0.03em;
        }

        .status {
            margin-top: 10px;
            display: flex;
            align-items: center;
            gap: 9px;
            font-size: 13px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.58);
        }

        .status-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.35);
        }

        .status-dot.connected {
            background: #ffffff;
            box-shadow: 0 0 12px rgba(255, 255, 255, 0.8);
        }

        .status-dot.disconnected {
            background: rgba(255, 255, 255, 0.18);
        }

        .messages {
            list-style: none;
            margin: 0;
            padding: 24px;
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 14px;
            background: #000000;
            scrollbar-width: thin;
            scrollbar-color: rgba(255, 255, 255, 0.35) transparent;
        }

        .messages::-webkit-scrollbar {
            width: 8px;
        }

        .messages::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.35);
            border-radius: 999px;
        }

        .message {
            max-width: 78%;
            padding: 13px 16px;
            border-radius: 14px;
            line-height: 1.5;
            word-break: break-word;
            font-size: 15.5px;
            animation: fadeIn 0.18s ease-in-out;
        }

        .message.received {
            align-self: flex-start;
            color: #ffffff;
            background: rgba(255, 255, 255, 0.045);
            border: 1px solid rgba(255, 255, 255, 0.38);
            border-bottom-left-radius: 4px;
        }

        .message.sent {
            align-self: flex-end;
            color: #000000;
            background: #ffffff;
            border: 1px solid #ffffff;
            border-bottom-right-radius: 4px;
        }

        .chat-form {
            padding: 18px;
            display: flex;
            gap: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.28);
            background: #000000;
        }

        .chat-form input {
            flex: 1;
            height: 54px;
            border: 1px solid rgba(255, 255, 255, 0.72);
            border-radius: 12px;
            padding: 0 16px;
            font-size: 16px;
            outline: none;
            background: #000000;
            color: #ffffff;
        }

        .chat-form input::placeholder {
            color: rgba(255, 255, 255, 0.36);
        }

        .chat-form input:focus {
            border-color: #ffffff;
            box-shadow: 0 0 0 1px #ffffff;
        }

        .chat-form button {
            min-width: 118px;
            height: 54px;
            border: 1px solid #ffffff;
            background: #000000;
            color: #ffffff;
            border-radius: 12px;
            font-size: 14px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            cursor: pointer;
            transition: 0.18s ease;
        }

        .chat-form button:hover:not(:disabled) {
            background: #ffffff;
            color: #000000;
        }

        .chat-form button:disabled {
            opacity: 0.35;
            cursor: not-allowed;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(6px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @media (max-width: 600px) {
            .chat-container {
                width: 100vw;
                height: 100vh;
                border-radius: 0;
            }

            .message {
                max-width: 88%;
                font-size: 15px;
            }

            .chat-form {
                padding: 14px;
            }

            .chat-form button {
                min-width: 92px;
            }
        }
    </style>
</head>

<body>
    <div class="chat-container">
        <header class="chat-header">
            <h1>WebSocket Chat</h1>

            <div class="status">
                <span id="statusDot" class="status-dot"></span>
                <span id="statusText">Bağlanıyor...</span>
            </div>
        </header>

        <ul id="messages" class="messages"></ul>

        <form class="chat-form" onsubmit="sendMessage(event)">
            <input
                type="text"
                id="messageText"
                placeholder="Mesajını yaz..."
                autocomplete="off"
            />
            <button id="sendButton" type="submit" disabled>Gönder</button>
        </form>
    </div>

    <script>
        const ws = new WebSocket("ws://localhost:8000/ws");
    <!--const ws = new WebSocket("wss://chatbot-production-34b3.up.railway.app/ws");-->


        const messages = document.getElementById("messages");
        const input = document.getElementById("messageText");
        const sendButton = document.getElementById("sendButton");
        const statusText = document.getElementById("statusText");
        const statusDot = document.getElementById("statusDot");

        ws.onopen = function () {
            statusText.textContent = "Bağlandı";
            statusDot.classList.add("connected");
            statusDot.classList.remove("disconnected");
            sendButton.disabled = false;
            input.focus();
        };

        ws.onmessage = function (event) {
            addMessage(event.data, "received");
        };

        ws.onclose = function () {
            statusText.textContent = "Bağlantı kesildi";
            statusDot.classList.remove("connected");
            statusDot.classList.add("disconnected");
            sendButton.disabled = true;
        };

        ws.onerror = function () {
            statusText.textContent = "Bağlantı hatası";
            statusDot.classList.remove("connected");
            statusDot.classList.add("disconnected");
            sendButton.disabled = true;
        };

        function addMessage(text, type) {
            const message = document.createElement("li");
            message.classList.add("message", type);
            message.textContent = text;

            messages.appendChild(message);
            messages.scrollTop = messages.scrollHeight;
        }

        function sendMessage(event) {
            event.preventDefault();

            const text = input.value.trim();

            if (!text || ws.readyState !== WebSocket.OPEN) {
                return;
            }

            ws.send(text);
            addMessage(text, "sent");

            input.value = "";
            input.focus();
        }
    </script>
</body>
</html>
"""


model = genai.GenerativeModel("gemini-2.0-flash")


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        chat = model.start_chat(history=[])
        try:
            while True:
                data = await websocket.receive_text()
                response = chat.send_message(data)
                await websocket.send_text(response.text)
        except Exception as e:
            print(f"Hatamız: {e}")
            await websocket.send_text(f"Hatamız: {e}")
    except Exception as e1:
        print(f"Hata: {e1}")
