#!/bin/bash
# MoldPark Hostinger VPS Kurulum Scripti
# VPS IP: 72.62.0.8
# OS: Ubuntu 24.04 LTS

set -e

echo "🚀 MoldPark Hostinger VPS Kurulumu Başlıyor..."

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Sistem Güncellemeleri
echo -e "${YELLOW}📦 Sistem güncelleniyor...${NC}"
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib redis-server

# 2. Projeyi İndir
echo -e "${YELLOW}📥 Proje indiriliyor...${NC}"
cd /root
if [ -d "moldpark" ]; then
    echo "Proje klasörü zaten var, güncelleniyor..."
    cd moldpark
    git pull
else
    git clone https://github.com/YOUR_REPO/moldpark.git
    cd moldpark
fi

# 3. Virtual Environment
echo -e "${YELLOW}🐍 Virtual environment oluşturuluyor...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. .env Dosyası Oluştur
echo -e "${YELLOW}⚙️ .env dosyası oluşturuluyor...${NC}"
if [ ! -f ".env" ]; then
    cat > .env << 'EOL'
# MoldPark Production Configuration
DEBUG=False
SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
ALLOWED_HOSTS=moldpark.com,www.moldpark.com,72.62.0.8
CSRF_TRUSTED_ORIGINS=https://moldpark.com,https://www.moldpark.com,http://72.62.0.8

# Database - PostgreSQL
DB_ENGINE=postgresql
DB_NAME=moldpark_db
DB_USER=moldpark_user
DB_PASSWORD=MoldPark2024SecurePass!
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@moldpark.com
EMAIL_HOST_PASSWORD=CHANGE_THIS

# Cache
REDIS_URL=redis://127.0.0.1:6379/1

# Security
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

LOG_LEVEL=INFO
EOL
    echo -e "${GREEN}✓ .env dosyası oluşturuldu${NC}"
else
    echo -e "${YELLOW}⚠ .env dosyası zaten var${NC}"
fi

# 5. PostgreSQL Kurulumu
echo -e "${YELLOW}🗄️ PostgreSQL yapılandırılıyor...${NC}"
sudo -u postgres psql << 'EOF'
-- Drop if exists
DROP DATABASE IF EXISTS moldpark_db;
DROP USER IF EXISTS moldpark_user;

-- Create
CREATE DATABASE moldpark_db;
CREATE USER moldpark_user WITH PASSWORD 'MoldPark2024SecurePass!';
ALTER ROLE moldpark_user SET client_encoding TO 'utf8';
ALTER ROLE moldpark_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE moldpark_user SET timezone TO 'Europe/Istanbul';
GRANT ALL PRIVILEGES ON DATABASE moldpark_db TO moldpark_user;
EOF

echo -e "${GREEN}✓ PostgreSQL hazır${NC}"

# 6. Django Kurulumu
echo -e "${YELLOW}🔧 Django yapılandırılıyor...${NC}"
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput

# Superuser oluştur (interaktif)
echo -e "${YELLOW}👤 Superuser oluşturuluyor...${NC}"
python manage.py createsuperuser --noinput --email admin@moldpark.com || echo "Superuser zaten var"

# 7. Log ve Data Klasörleri
echo -e "${YELLOW}📁 Klasörler oluşturuluyor...${NC}"
mkdir -p /root/moldpark/logs
mkdir -p /root/moldpark/data
chmod -R 755 /root/moldpark/logs
chmod -R 755 /root/moldpark/media

# 8. Gunicorn Servisi
echo -e "${YELLOW}⚙️ Gunicorn servisi kuruluyor...${NC}"
cp /root/moldpark/deployment/gunicorn.service /etc/systemd/system/gunicorn.service
systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn

# 9. Nginx Konfigürasyonu
echo -e "${YELLOW}🌐 Nginx yapılandırılıyor...${NC}"
cp /root/moldpark/deployment/nginx_moldpark.conf /etc/nginx/sites-available/moldpark
ln -sf /etc/nginx/sites-available/moldpark /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
systemctl enable nginx

# 10. Firewall Ayarları
echo -e "${YELLOW}🔥 Firewall yapılandırılıyor...${NC}"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 11. Durum Kontrolü
echo -e "\n${GREEN}✅ Kurulum Tamamlandı!${NC}\n"

echo "📊 Servis Durumları:"
systemctl status gunicorn --no-pager | head -n 5
systemctl status nginx --no-pager | head -n 5

echo -e "\n🌐 Site Erişim:"
echo "  - HTTP: http://72.62.0.8"
echo "  - HTTP: http://moldpark.com (DNS yayılımından sonra)"
echo "  - Admin: http://72.62.0.8/admin/"

echo -e "\n📝 Log Dosyaları:"
echo "  - Gunicorn: /root/moldpark/logs/gunicorn_error.log"
echo "  - Nginx: /var/log/nginx/moldpark_error.log"

echo -e "\n🔧 Yönetim Komutları:"
echo "  - Gunicorn restart: systemctl restart gunicorn"
echo "  - Nginx restart: systemctl restart nginx"
echo "  - Log izleme: tail -f /root/moldpark/logs/gunicorn_error.log"

echo -e "\n⚠️ HTTPS İçin:"
echo "  apt install -y certbot python3-certbot-nginx"
echo "  certbot --nginx -d moldpark.com -d www.moldpark.com"

echo -e "\n${GREEN}🎉 MoldPark yayında!${NC}"

