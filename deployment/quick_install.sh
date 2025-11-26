#!/bin/bash

# MoldPark Hızlı Kurulum Scripti
# SSH ile bağlandıktan sonra bu komutu çalıştırın

echo "🚀 MoldPark Kurulum Başlıyor..."

# Sistem güncelle
apt update && apt upgrade -y

# Gerekli paketleri kur
apt install -y python3 python3-pip python3-venv git nginx curl wget

# Proje klonla
cd /root
git clone https://github.com/doganiot/moldpark.git

# Virtual environment
cd /root/moldpark
python3 -m venv venv
source venv/bin/activate

# Python paketleri
pip install --upgrade pip
pip install -r requirements.txt

# .env dosyası
cat > .env << 'EOF'
DEBUG=False
SECRET_KEY=django-insecure-$(openssl rand -hex 32)
ALLOWED_HOSTS=moldpark.com,www.moldpark.com,72.62.0.8,localhost
CSRF_TRUSTED_ORIGINS=https://moldpark.com,https://www.moldpark.com
EOF

# Log dizini
mkdir -p logs

# Django setup
python manage.py migrate
python manage.py collectstatic --noinput

# Nginx
cp deployment/nginx_moldpark.conf /etc/nginx/sites-available/moldpark
ln -sf /etc/nginx/sites-available/moldpark /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t

# Gunicorn
cp deployment/gunicorn.service /etc/systemd/system/gunicorn.service
systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn
systemctl enable nginx
systemctl restart nginx

echo ""
echo "✅ Kurulum tamamlandı!"
echo "🌐 Site: http://moldpark.com"
echo ""
echo "📊 Durum:"
systemctl status gunicorn --no-pager -l
systemctl status nginx --no-pager -l

