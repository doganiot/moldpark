#!/bin/bash

# MoldPark VPS Otomatik Kurulum Post-Install Scripti
# Bu script VPS ilk kurulumunda otomatik çalışır

set -e  # Hata durumunda dur

echo "🚀 MoldPark VPS Otomatik Kurulum Başlıyor..."

# Sistem güncellemesi
apt update && apt upgrade -y

# Gerekli paketleri kur
apt install -y python3 python3-pip python3-venv git nginx curl wget

# Proje dizinini oluştur
mkdir -p /root/moldpark

# GitHub'dan projeyi klonla
cd /root
git clone https://github.com/doganiot/moldpark.git

# Virtual environment oluştur
cd /root/moldpark
python3 -m venv venv
source venv/bin/activate

# Python paketlerini kur
pip install --upgrade pip
pip install -r requirements.txt

# .env dosyası oluştur
cat > /root/moldpark/.env << 'EOF'
DEBUG=False
SECRET_KEY=django-insecure-change-this-in-production-$(openssl rand -hex 32)
ALLOWED_HOSTS=moldpark.com,www.moldpark.com,72.62.0.8,localhost
CSRF_TRUSTED_ORIGINS=https://moldpark.com,https://www.moldpark.com
DB_NAME=moldpark
DB_USER=moldpark
DB_PASSWORD=moldpark_pass_2024
DB_HOST=localhost
DB_PORT=5432
EOF

# Log dizini oluştur
mkdir -p /root/moldpark/logs

# Django migrate
python manage.py migrate

# Static dosyaları topla
python manage.py collectstatic --noinput

# Nginx konfigürasyonu
cp /root/moldpark/deployment/nginx_moldpark.conf /etc/nginx/sites-available/moldpark
ln -sf /etc/nginx/sites-available/moldpark /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Nginx test
nginx -t

# Gunicorn servisi
cp /root/moldpark/deployment/gunicorn.service /etc/systemd/system/gunicorn.service

# Systemd reload
systemctl daemon-reload

# Servisleri başlat
systemctl enable gunicorn
systemctl start gunicorn
systemctl enable nginx
systemctl restart nginx

echo "✅ MoldPark kurulumu tamamlandı!"
echo "🌐 Site: http://moldpark.com"
echo "📝 Loglar: /root/moldpark/logs/"

# Durum kontrolü
systemctl status gunicorn --no-pager
systemctl status nginx --no-pager

