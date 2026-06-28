# FastAPI + WebSocket + Gemini Chatbot

WebSocket üzerinden Google Gemini ile streaming sohbet eden bir FastAPI uygulaması.

## Çalıştırma

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

`.env` dosyası gerekli değişkenler:

```
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
APP_ACCESS_TOKEN=...
ALLOWED_ORIGINS=["http://127.0.0.1:8000"]
LOG_LEVEL=INFO
HISTORY_WINDOW=10
```

## Test

```bash
pytest
```

Testler gerçek Gemini API'sini **çağırmaz**; `FakeProvider` ile çalışır (faturalama yok, hızlı).

## Dizin yapısı

```
app/
  main.py                       # FastAPI app + lifespan + router include
  config.py                     # Settings (pydantic-settings)
  logging_config.py             # logging setup + ConnectionLoggerAdapter
  schemas/messages.py           # Pydantic mesaj modelleri (chunk/done/error/system/user)
  routers/web.py                # GET / (chat sayfası), /health, /metrics
  routers/ws.py                 # WS /ws endpoint
  services/llm_provider.py      # LLMProvider Protocol + GeminiProvider
  services/chat_service.py      # ChatService: history window + rate limit + stream
  services/connection_manager.py# Aktif bağlantı izleme + metrics + close_all
tests/                          # pytest unit + entegrasyon testleri
```

## Mimari Kararlar

### WebSocket close code seçimi
- **1008 (Policy Violation):** Yanlış `Origin` veya yanlış `token`. Bağlantı `accept` edilmeden reddedilir.
- **1011 (Internal Error):** Beklenmedik exception sonrası, kullanıcıya generic mesaj gönderip kapanış.
- **1012 (Service Restart):** SIGTERM ile kapanışta uvicorn'un kendisi gönderir (aşağıdaki graceful shutdown notuna bakın).

### Hata yönetimi
- `WebSocketDisconnect` normal bir lifecycle olayı olarak ele alınır — sessizce loglanır, hata sayılmaz.
- Ham exception mesajı kullanıcıya **sızdırılmaz**; sadece `connection_id` içeren generic mesaj döner, detay sunucu logunda kalır.
- Gemini hataları tiplerine göre ayrılır: `ServerError` 503 (yoğunluk), `ClientError` 429 (kota), idle timeout.

### Rate limit
- **Sliding window** algoritması: `time.monotonic()` ile son 10 saniyedeki mesajlar sayılır, 5'i aşınca reddedilir.
- `monotonic` seçildi çünkü sistem saati değişse bile (NTP, DST) pencere bozulmaz.

### History pencereleme (maliyet kontrolü)
- Gemini'nin `chat` nesnesi yerine history **manuel** tutulur (`list[types.Content]`).
- Her istekte yalnızca son `HISTORY_WINDOW` turn modele gönderilir → token maliyeti plato yapar, sınırsız büyümez.
- Pencere slice'ı tek bir `_windowed_history()` metodunda — loglanan turn sayısı ile gerçekte gönderilen her zaman aynı.

### Generation config
- `temperature=0.2` (tutarlı, daha az halüsinasyon), `max_output_tokens=3000` (maliyet tavanı).
- System instruction `GeminiProvider` içinde sabit; her bağlantıda yeniden oluşturulmaz.

### Katmanlı yapı ve LLM soyutlaması
- `LLMProvider` bir `Protocol` (structural typing) — `GeminiProvider` onu implement eder, `FakeProvider` testlerde yerine geçer.
- `ChatService` connection-bağlı state tutar (history, rate-limit timestamps), bu yüzden **her bağlantı için ayrı** oluşturulur.
- `genai.Client` connection-bağımsız ve pahalı, bu yüzden **lifespan**'da bir kez oluşturulup `app.state`'e konur.

### Lifespan ve kaynak yönetimi
- `genai.Client` ve `ConnectionManager` startup'ta oluşturulur, `app.state`'e bağlanır.
- 12-factor "backing services" prensibi: kaynaklar uygulama yaşam döngüsüne bağlı.

### Gözlemlenebilirlik
- `/health`: liveness probe — Gemini client init olmuşsa 200, olmamışsa 503.
- `/metrics`: `active_connections` (gauge) ve `total_messages` (counter). Prometheus entegrasyonu için doğal büyüme noktası.
- `ConnectionLoggerAdapter` her log satırına `connection_id` ekler (aranabilir, structured).

### Graceful shutdown (önemli gözlem)
- `ConnectionManager.close_all(code=1001)` lifespan shutdown'da çağrılır.
- **Ancak:** uvicorn, SIGTERM aldığında açık WS bağlantılarını **lifespan shutdown'dan önce** kendisi kapatır (close code **1012**). Bu yüzden `close_all` çalıştığında bağlantı listesi genelde boştur ve istemci pratikte 1012 alır, 1001 değil.
- Bu, ASGI lifespan protokolünün doğal sırasıdır, bir bug değildir. Hem 1001 (Going Away) hem 1012 (Service Restart) geçerli "sunucu kapanıyor" kodlarıdır; 1012 deploy/restart senaryosu için anlamca daha doğrudur.
- `close_all` yine de tutuluyor: (1) programatik kapatma yeteneği, (2) uvicorn'un yakalamadığı bir bağlantı kalırsa güvenlik ağı.

### Heartbeat / zombie connection
- Uygulama seviyesinde ping/pong **eklenmedi** (bilinçli karar). uvicorn'un kendi WebSocket ping interval'ı half-open bağlantıları tespit etmek için yeterli. Uygulama seviyesi heartbeat erken karmaşıklık olurdu.

### Test stratejisi
- Test piramidi: çoğunluk unit (`ChatService`, `ConnectionManager`), birkaç entegrasyon (`TestClient` ile WS happy/negative path).
- `FakeProvider` ile gerçek API çağrısı yapılmaz — testler hızlı (~0.2s) ve faturasız.
- pytest tuzağı: `settings` singleton modül yüklenirken oluştuğu için `monkeypatch.setenv` çalışmaz; `monkeypatch.setattr(settings, ...)` ile patch edilir.

## Ertelenen konular (ikinci tur)
Dockerfile, reverse proxy, JWT auth, persistent storage, tam Prometheus/OpenTelemetry entegrasyonu, multi-cihaz oturum.
