# --- Aşama 1: React (Vite) frontend'i derle ---
FROM node:22-slim AS frontend
WORKDIR /fe
# Önce manifest: bağımlılık katmanı cache'lensin
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build   # → /fe/dist

# --- Aşama 2: Python uygulaması ---
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Önce sadece requirements: kod değişince pip katmanı cache'ten gelir.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodu.
COPY . .

# Derlenmiş React'i kopyala → FastAPI '/' ve '/assets' üzerinden servis eder (tek origin, CORS yok).
COPY --from=frontend /fe/dist ./frontend/dist

# Root olarak çalışma (güvenlik): ayrı bir kullanıcı.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Tek worker: WS bağlantı-içi durum (rate-limit) worker'lar arası paylaşılmaz.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
