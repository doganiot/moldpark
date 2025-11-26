#!/bin/bash

# MoldPark Hızlı Düzeltme Scripti

cd /root/moldpark

# Git pull
echo "🔄 Güncellemeler çekiliyor..."
git pull

# .env dosyasını oluştur/düzelt
echo "⚙️  .env dosyası ayarlanıyor..."
cat > .env << 'EOF'
DEBUG=False
SECRET_KEY=django-insecure-$(openssl rand -hex 32)
ALLOWED_HOSTS=moldpark.com,www.moldpark.com,72.62.0.8,localhost
CSRF_TRUSTED_ORIGINS=https://moldpark.com,https://www.moldpark.com
DB_ENGINE=sqlite3
DB_NAME=db.sqlite3
EOF

# Virtual environment
echo "🐍 Virtual environment aktive ediliyor..."
source venv/bin/activate

# Requirements
echo "📦 Paketler kuruluyor..."
pip install -r requirements.txt

# Migrate
echo "🗄️  Database migrate ediliyor..."
python manage.py migrate

# Admin user
echo "👤 Admin kullanıcısı oluşturuluyor..."
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell

# Servisleri yeniden başlat
echo "🔄 Servisler yeniden başlatılıyor..."
sudo systemctl restart gunicorn
sudo systemctl reload nginx

echo ""
echo "✅ Kurulum tamamlandı!"
echo "🌐 Site: http://moldpark.com"
echo "👤 Admin: admin / admin123"
echo "📍 Admin Panel: http://moldpark.com/admin/"
echo ""

