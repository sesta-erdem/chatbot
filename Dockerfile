FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Önce sadece requirements'ı kopyala: kod değişince pip katmanı cache'ten gelir.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sonra uygulama kodu.
COPY . .

# Root olarak çalışma (güvenlik): ayrı bir kullanıcı oluştur.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# WebSocket'te bağlantı-içi durum (rate-limit listesi) worker'lar arası paylaşılmaz;
# bu yüzden tek worker. Ölçekleme gerekince paylaşımlı durum (Redis) ile çoğaltılır.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
