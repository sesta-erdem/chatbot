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
- **Döngü 1–11 BİTTİ** ve commit'li, CI yeşil: D7 PostgreSQL kalıcılık + token-bazlı pencere, D8 Docker+Compose+CI, D9 JWT+kullanıcılar+RBAC, D10 RAG (pgvector + embeddings + PDF), D11 React (Vite) frontend.
- **Döngü 12 (pazara çıkış)**: yazılı kit hazır → `PAZARA_CIKIS.md`. Gerçek-dünya adımları (profil açma, deploy linkleri, demo video, teklif gönderme, yorum) **kullanıcının** işi.
- Backend sözleşmeleri: `/auth/register`, `/auth/login` (JWT), `/ws` (JWT'li, RAG'li, `done`'da `sources`), `/documents/upload`, `/admin/stats`, `/metrics`. Frontend: `frontend/` (Vite+React).
- **Açık teknik işler / sıradaki tur:** canlı Gemini doğrulaması (kota), 3 paketin deploy'u + embed widget + Telegram botu, üçüncü harita (ödeme, multi-tenancy) — pazar verisiyle.

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
