#!/bin/bash

# MoldPark Tanılama Scripti

echo "🔍 MoldPark Sistem Tanılama"
echo "============================"

# 1. Servis durumları
echo ""
echo "📊 Servis Durumları:"
echo "--------------------"

if systemctl is-active --quiet gunicorn; then
    echo "✅ Gunicorn: ÇALIŞIYOR"
else
    echo "❌ Gunicorn: ÇALIŞMIYOR"
    sudo systemctl status gunicorn --no-pager -l
fi

if systemctl is-active --quiet nginx; then
    echo "✅ Nginx: ÇALIŞIYOR"
else
    echo "❌ Nginx: ÇALIŞMIYOR"
    sudo systemctl status nginx --no-pager -l
fi

# 2. Port kontrolü
echo ""
echo "🔌 Port Durumları:"
echo "------------------"
echo "Port 80 (HTTP):"
sudo netstat -tuln | grep :80 || echo "❌ Port 80 açık değil"

echo "Port 8000 (Gunicorn):"
sudo netstat -tuln | grep :8000 || echo "❌ Port 8000 açık değil"

# 3. Firewall kontrolü
echo ""
echo "🔥 Firewall Durum:"
echo "------------------"
if command -v ufw &> /dev/null; then
    sudo ufw status | head -10
else
    echo "UFW kurulu değil"
fi

# 4. Local test
echo ""
echo "🧪 Local Testler:"
echo "-----------------"

echo "Localhost test:"
curl -s -I http://localhost | head -3 || echo "❌ Localhost yanıt vermiyor"

echo "Gunicorn test:"
curl -s -I http://127.0.0.1:8000 | head -3 || echo "❌ Gunicorn yanıt vermiyor"

# 5. Nginx konfigürasyonu
echo ""
echo "⚙️  Nginx Konfigürasyonu:"
echo "------------------------"
if [ -f /etc/nginx/sites-enabled/moldpark ]; then
    echo "✅ Nginx konfigürasyon dosyası mevcut"
    sudo nginx -t 2>&1 || echo "❌ Nginx konfigürasyon hatası"
else
    echo "❌ Nginx konfigürasyon dosyası bulunamadı"
fi

# 6. Log kontrolü
echo ""
echo "📝 Son Log Kayıtları:"
echo "---------------------"

echo "Gunicorn Error Log:"
tail -5 /root/moldpark/logs/gunicorn_error.log 2>/dev/null || echo "Log dosyası bulunamadı"

echo "Nginx Error Log:"
sudo tail -5 /var/log/nginx/moldpark_error.log 2>/dev/null || echo "Log dosyası bulunamadı"

echo ""
echo "🎯 Öneriler:"
echo "------------"
echo "1. Servisler çalışmıyorsa: sudo systemctl restart gunicorn && sudo systemctl restart nginx"
echo "2. Port 80 kapalıysa: Hostinger panelinden firewall kuralı ekleyin"
echo "3. DNS sorun varsa: 5-30 dakika bekleyin"
echo "4. Hâlâ çalışmıyorsa: Bu script çıktısını paylaşın"

