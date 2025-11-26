#!/bin/bash

# MoldPark Servis Düzeltme Scripti

echo "🔧 MoldPark Servis Düzeltme"
echo "==========================="

# 1. Gunicorn kontrolü ve yeniden başlatma
echo ""
echo "🐍 Gunicorn Kontrolü:"
echo "---------------------"

if systemctl is-active --quiet gunicorn; then
    echo "✅ Gunicorn çalışıyor"
else
    echo "❌ Gunicorn çalışmıyor, yeniden başlatılıyor..."
    sudo systemctl restart gunicorn

    # 3 saniye bekle
    sleep 3

    if systemctl is-active --quiet gunicorn; then
        echo "✅ Gunicorn başarıyla başlatıldı"
    else
        echo "❌ Gunicorn başlatılamadı"
        sudo systemctl status gunicorn --no-pager -l
        exit 1
    fi
fi

# 2. Nginx kontrolü ve yeniden başlatma
echo ""
echo "🌐 Nginx Kontrolü:"
echo "------------------"

if systemctl is-active --quiet nginx; then
    echo "✅ Nginx çalışıyor"
else
    echo "❌ Nginx çalışmıyor, yeniden başlatılıyor..."
    sudo systemctl restart nginx

    if systemctl is-active --quiet nginx; then
        echo "✅ Nginx başarıyla başlatıldı"
    else
        echo "❌ Nginx başlatılamadı"
        sudo systemctl status nginx --no-pager -l
        exit 1
    fi
fi

# 3. Port kontrolü
echo ""
echo "🔌 Port Kontrolü:"
echo "-----------------"

echo "Port 8000 (Gunicorn):"
if netstat -tuln 2>/dev/null | grep -q :8000; then
    echo "✅ Port 8000 açık"
else
    echo "❌ Port 8000 kapalı"
fi

echo "Port 80 (Nginx):"
if netstat -tuln 2>/dev/null | grep -q :80; then
    echo "✅ Port 80 açık"
else
    echo "❌ Port 80 kapalı"
fi

# 4. Local test
echo ""
echo "🧪 Bağlantı Testleri:"
echo "---------------------"

echo "Local Gunicorn test:"
if curl -s -I http://127.0.0.1:8000 | head -1 | grep -q "200\|301\|302"; then
    echo "✅ Gunicorn yanıt veriyor"
else
    echo "❌ Gunicorn yanıt vermiyor"
fi

echo "Local Nginx test:"
if curl -s -I http://localhost | head -1 | grep -q "200\|301\|302"; then
    echo "✅ Nginx yanıt veriyor"
else
    echo "❌ Nginx yanıt vermiyor"
fi

# 5. Son durum
echo ""
echo "📊 Final Durum:"
echo "---------------"
sudo systemctl status gunicorn --no-pager -l | grep -E "(Active|Loaded|Main PID)"
sudo systemctl status nginx --no-pager -l | grep -E "(Active|Loaded|Main PID)"

echo ""
echo "🎉 Test tamamlandı!"
echo "🌐 Site: http://moldpark.com"
echo "👤 Admin: http://moldpark.com/admin/ (admin/admin123)"

