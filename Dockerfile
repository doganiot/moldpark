FROM python:3.12-slim

# Sistem paketlerini güncelle
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Requirements'ı kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY . .

# Static ve media klasörleri
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Entrypoint script'i çalıştırılabilir yap
RUN chmod +x /app/deployment/docker-entrypoint.sh

# Port
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/app/deployment/docker-entrypoint.sh"]

