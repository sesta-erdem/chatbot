# DEVAM — Yeni oturum için handoff

Yeni bir Claude oturumu açtığında ona şunu de: **"DEVAM.md'yi oku ve kaldığın yerden devam et."**

---

Bu, FastAPI + WebSocket + Google Gemini tabanlı bir chatbot öğrenme projesi. 12 döngülük bir yol haritasıyla ilerliyoruz. Sen mentor + birlikte-kuran geliştiricisin: kodu doğrudan yaz, her döngüde **test + ruff + commit + push + CI yeşil** kontrolü yap, sonra Türkçe kısa özet ver. (AI'a kod yazdırmama kuralı KALDIRILDI — doğrudan kur.)

## Önce şunları oku (repo kökünde)
- `README.md` → mimari + quickstart + kararlar
- `yolharitasi-2-dongu-7-12.md` → Döngü 7–12 spec'leri (asıl referans)
- `KOD_REHBERI.md` → dosya dosya "neyin neden yazıldığı"
- `app/` → mevcut kod

## Nerede kaldık
- **Döngü 1–12 BİTTİ** ve commit'li, CI yeşil: D7 PostgreSQL kalıcılık + token-bazlı pencere, D8 Docker+Compose+CI, D9 JWT+kullanıcılar+RBAC, D10 RAG (pgvector + embeddings + PDF), D11 React (Vite) frontend, D12 pazara çıkış kiti (`PAZARA_CIKIS.md`).
- **Tek deploy birimi HAZIR ve canlı doğrulandı:** multi-stage Dockerfile React'i derler, FastAPI hem UI'ı hem API/WS'i `:8000`'den (aynı origin, prod'da CORS yok) servis eder → `docker compose up --build` tek komutla tüm sistem.
- **Döngü 12 gerçek-dünya adımları kullanıcının işi:** profil açma, canlı deploy linki (Railway/Render/VPS — `docker compose` ile), demo video, teklif gönderme, yorum toplama.
- Backend sözleşmeleri: `/auth/register`, `/auth/login` (JWT), `/ws` (JWT'li, RAG'li, `done`'da `sources`), `/documents/upload`, `/admin/stats`, `/metrics`. Frontend: `frontend/` (Vite+React), prod'da `frontend/dist` FastAPI'den servis edilir.
- **Açık teknik işler / sıradaki tur:** canlı Gemini doğrulaması (kota), canlı hosting'e deploy (kullanıcı hesabı gerekli), embed widget + Telegram botu, üçüncü harita (ödeme, multi-tenancy) — pazar verisiyle.

## Ortam
- Branch: **`claude/vigorous-murdock-60a43a`** (tüm iş burada; `main`'de değil). Fresh clone'da önce: `git checkout claude/vigorous-murdock-60a43a`
- venv: `.venv` · çalıştırma: `.venv/bin/uvicorn app.main:app --reload`
- Testler: `.venv/bin/python -m pytest tests/` (fake'lerle, DB/Gemini'siz)
- Lint: `.venv/bin/ruff check .`
- Postgres: local `brew postgresql@16` + pgvector kurulu, DB adı `chatbot`, migration'lar Alembic (`.venv/bin/alembic upgrade head`)
- `.env` gerekli: `GEMINI_API_KEY`, `APP_ACCESS_TOKEN`, `JWT_SECRET`, `DATABASE_URL` (`postgresql+asyncpg://...`), `ALLOWED_ORIGINS` (`.env.example`'a bak)
- NOT: Gemini ücretsiz kotası dolmuş olabilir → canlı LLM/embedding çağrıları 429 "Kotam doldu" dönebilir; kod doğru, kota sıfırlanınca çalışır.

## Kullanıcı hakkında
Yazılım öğrenen biri; geliştirici araçlarına (debugger, venv) yeni. Araç/komut konularını temelden anlat, Türkçe konuş.
