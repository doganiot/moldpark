#!/bin/bash

# MoldPark Otomatik Kurulum Scripti
# Bu script Nginx ve Gunicorn kurulumunu otomatik yapar

set -e  # Hata durumunda dur

echo "🚀 MoldPark Otomatik Kurulum Başlıyor..."

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Proje dizini
PROJECT_DIR="/root/moldpark"
NGINX_CONF="/etc/nginx/sites-available/moldpark"
GUNICORN_SERVICE="/etc/systemd/system/gunicorn.service"

# 1. Nginx Kurulumu
echo -e "${YELLOW}📦 Nginx kurulumu kontrol ediliyor...${NC}"
if ! command -v nginx &> /dev/null; then
    echo "Nginx kuruluyor..."
    sudo apt update
    sudo apt install -y nginx
else
    echo -e "${GREEN}✓ Nginx zaten kurulu${NC}"
fi

# 2. Nginx Konfigürasyonu
echo -e "${YELLOW}⚙️  Nginx konfigürasyonu ayarlanıyor...${NC}"
if [ -f "$PROJECT_DIR/deployment/nginx_moldpark.conf" ]; then
    sudo cp "$PROJECT_DIR/deployment/nginx_moldpark.conf" "$NGINX_CONF"
    echo -e "${GREEN}✓ Nginx konfigürasyon dosyası kopyalandı${NC}"
else
    echo -e "${RED}✗ Nginx konfigürasyon dosyası bulunamadı: $PROJECT_DIR/deployment/nginx_moldpark.conf${NC}"
    exit 1
fi

# Symlink oluştur
if [ ! -L /etc/nginx/sites-enabled/moldpark ]; then
    sudo ln -s "$NGINX_CONF" /etc/nginx/sites-enabled/moldpark
    echo -e "${GREEN}✓ Nginx symlink oluşturuldu${NC}"
fi

# Varsayılan siteyi kaldır (opsiyonel)
if [ -L /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
    echo -e "${GREEN}✓ Varsayılan Nginx sitesi kaldırıldı${NC}"
fi

# Nginx konfigürasyonunu test et
echo -e "${YELLOW}🔍 Nginx konfigürasyonu test ediliyor...${NC}"
if sudo nginx -t; then
    echo -e "${GREEN}✓ Nginx konfigürasyonu geçerli${NC}"
else
    echo -e "${RED}✗ Nginx konfigürasyon hatası!${NC}"
    exit 1
fi

# 3. Gunicorn Systemd Servisi
echo -e "${YELLOW}⚙️  Gunicorn servisi ayarlanıyor...${NC}"
if [ -f "$PROJECT_DIR/deployment/gunicorn.service" ]; then
    sudo cp "$PROJECT_DIR/deployment/gunicorn.service" "$GUNICORN_SERVICE"
    echo -e "${GREEN}✓ Gunicorn servis dosyası kopyalandı${NC}"
else
    echo -e "${RED}✗ Gunicorn servis dosyası bulunamadı: $PROJECT_DIR/deployment/gunicorn.service${NC}"
    exit 1
fi

# Systemd'yi yeniden yükle
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Systemd yeniden yüklendi${NC}"

# 4. Static Dosyaları Toplama
echo -e "${YELLOW}📁 Static dosyalar toplanıyor...${NC}"
cd "$PROJECT_DIR"
if [ -d "venv" ]; then
    source venv/bin/activate
    python manage.py collectstatic --noinput
    echo -e "${GREEN}✓ Static dosyalar toplandı${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment bulunamadı, static dosyalar atlandı${NC}"
fi

# 5. Log dizinini oluştur
echo -e "${YELLOW}📝 Log dizinleri oluşturuluyor...${NC}"
mkdir -p "$PROJECT_DIR/logs"
echo -e "${GREEN}✓ Log dizinleri hazır${NC}"

# 6. Servisleri Başlat
echo -e "${YELLOW}🔄 Servisler başlatılıyor...${NC}"

# Gunicorn'u durdur (varsa)
if systemctl is-active --quiet gunicorn; then
    sudo systemctl stop gunicorn
    echo -e "${GREEN}✓ Eski Gunicorn servisi durduruldu${NC}"
fi

# Gunicorn'u başlat
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
echo -e "${GREEN}✓ Gunicorn servisi başlatıldı ve otomatik başlatma aktif edildi${NC}"

# Nginx'i yeniden başlat
sudo systemctl restart nginx
sudo systemctl enable nginx
echo -e "${GREEN}✓ Nginx yeniden başlatıldı ve otomatik başlatma aktif edildi${NC}"

# 7. Durum Kontrolü
echo -e "\n${YELLOW}📊 Servis durumları kontrol ediliyor...${NC}\n"

# Gunicorn durumu
if systemctl is-active --quiet gunicorn; then
    echo -e "${GREEN}✓ Gunicorn: ÇALIŞIYOR${NC}"
else
    echo -e "${RED}✗ Gunicorn: ÇALIŞMIYOR${NC}"
    echo "Detaylar için: sudo systemctl status gunicorn"
fi

# Nginx durumu
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx: ÇALIŞIYOR${NC}"
else
    echo -e "${RED}✗ Nginx: ÇALIŞMIYOR${NC}"
    echo "Detaylar için: sudo systemctl status nginx"
fi

# Port kontrolü
if netstat -tuln | grep -q ":8000"; then
    echo -e "${GREEN}✓ Port 8000: AÇIK${NC}"
else
    echo -e "${YELLOW}⚠ Port 8000: KAPALI (Gunicorn başlatılıyor olabilir)${NC}"
fi

if netstat -tuln | grep -q ":80"; then
    echo -e "${GREEN}✓ Port 80: AÇIK${NC}"
else
    echo -e "${RED}✗ Port 80: KAPALI${NC}"
fi

echo -e "\n${GREEN}✅ Kurulum tamamlandı!${NC}\n"
echo "🌐 Site adresi: http://moldpark.com"
echo "📝 Log dosyaları:"
echo "   - Gunicorn: $PROJECT_DIR/logs/gunicorn_*.log"
echo "   - Nginx: /var/log/nginx/moldpark_*.log"
echo ""
echo "🔍 Durum kontrolü için:"
echo "   sudo systemctl status gunicorn"
echo "   sudo systemctl status nginx"
echo ""
echo "📋 Servis komutları:"
echo "   sudo systemctl restart gunicorn  # Gunicorn'u yeniden başlat"
echo "   sudo systemctl restart nginx      # Nginx'i yeniden başlat"
echo "   sudo systemctl stop gunicorn     # Gunicorn'u durdur"
echo ""

