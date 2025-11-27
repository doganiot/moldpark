#!/bin/bash

echo "🐳 MoldPark Docker VPS Kurulumu"
echo "================================"

# Sistem güncelleme
echo "📦 Sistem güncelleniyor..."
apt-get update
apt-get upgrade -y

# Docker kurulumu
echo "🐳 Docker kurulumu..."
apt-get install -y ca-certificates curl gnupg lsb-release
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Docker Compose kurulumu
echo "🔧 Docker Compose kurulumu..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Git kurulumu
echo "📚 Git kurulumu..."
apt-get install -y git

# Proje klasörü
echo "📁 Proje indiriliyor..."
cd /root
rm -rf moldpark
git clone https://github.com/doganiot/moldpark.git
cd moldpark

# .env dosyası oluştur
echo "⚙️ .env dosyası oluşturuluyor..."
cat > .env << 'EOF'
DEBUG=False
SECRET_KEY=django-insecure-$(openssl rand -hex 32)
ALLOWED_HOSTS=moldpark.com,www.moldpark.com,72.62.0.8,localhost
CSRF_TRUSTED_ORIGINS=http://moldpark.com,http://www.moldpark.com,http://72.62.0.8

# Database (SQLite için)
DB_ENGINE=sqlite3
EOF

# Klasörleri oluştur
mkdir -p staticfiles media logs
chmod -R 777 staticfiles media logs

# Entrypoint script'e izin ver
chmod +x deployment/docker-entrypoint.sh

# Docker build ve start
echo "🚀 Docker container'lar başlatılıyor..."
docker-compose up -d --build

# Durum kontrolü
echo ""
echo "⏳ Container'ların hazır olması bekleniyor (30 saniye)..."
sleep 30

echo ""
echo "📊 Container durumu:"
docker-compose ps

echo ""
echo "✅ Kurulum tamamlandı!"
echo ""
echo "🌐 Site: http://moldpark.com"
echo "👤 Admin: http://moldpark.com/admin/"
echo "   Kullanıcı: admin"
echo "   Şifre: admin123"
echo ""
echo "📋 Faydalı komutlar:"
echo "   docker-compose logs -f          # Log'ları izle"
echo "   docker-compose restart          # Yeniden başlat"
echo "   docker-compose down             # Durdur"
echo "   docker-compose up -d            # Başlat"
echo ""

