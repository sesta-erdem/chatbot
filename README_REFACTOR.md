# main.py refactor

Bu sürüm mevcut `main.py` içindeki sorumlulukları küçük bileşenlere ayırır.

## Sorumluluklar

- `main.py`: uygulamayı kurar, lifespan kaynaklarını yönetir.
- `api/websocket.py`: WebSocket taşıma katmanı, giriş doğrulama ve bağlantı olayları.
- `providers/gemini.py`: yalnızca Gemini SDK ayrıntıları.
- `providers/base.py`: uygulamanın LLM sağlayıcısından beklediği arayüz.
- `services/chat.py`: context/history ve generation akışı.
- `services/rate_limit.py`: bağlantı başına rate limit.
- `repositories/chat.py`: mevcut asyncpg SQL işlemleri.
- `core/database.py`: pool oluşturma.
- `core/logging.py`: logging kurulumu ve connection logger.
- `models.py`: WebSocket mesaj sözleşmesi.

## Önemli

1. `.env` dosyana `DATABASE_URL` ekle.
2. Mevcut `templates/item.html` dosyanı `templates/` altında bırak.
3. Klasörlerdeki `__init__.py` dosyalarını silme.
4. Bu refaktörden sonra önce mevcut davranışları tekrar test et.
