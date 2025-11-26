#!/bin/bash

# Gunicorn Debug Scripti

echo "🐛 Gunicorn Debug Başlıyor"
echo "=========================="

# 1. Gunicorn proses kontrolü
echo ""
echo "📊 Gunicorn Prosesleri:"
echo "-----------------------"
ps aux | grep gunicorn | grep -v grep || echo "Gunicorn prosesi bulunamadı"

# 2. Gunicorn servis durumu
echo ""
echo "⚙️  Servis Durumu:"
echo "------------------"
sudo systemctl status gunicorn --no-pager -l

# 3. Port kontrolü
echo ""
echo "🔌 Port Durumu:"
echo "---------------"
sudo netstat -tuln | grep :8000 || echo "Port 8000 açık değil"

# 4. Socket kontrolü
echo ""
echo "🔗 Socket Bağlantısı:"
echo "---------------------"
sudo ss -tuln | grep :8000 || echo "Socket 8000 bulunamadı"

# 5. Manuel Django testi
echo ""
echo "🐍 Django Uygulama Testi:"
echo "-------------------------"

cd /root/moldpark

# Virtual environment kontrolü
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment aktif"

    # Django check
    echo "Django check:"
    python manage.py check 2>&1 || echo "❌ Django check başarısız"

    # Django test server
    echo "Django runserver test (5 saniye):"
    timeout 5 python manage.py runserver 127.0.0.1:8001 --noreload > django_test.log 2>&1 &
    DJANGO_PID=$!
    sleep 3

    # Test bağlantısı
    if curl -s http://127.0.0.1:8001 | head -1 | grep -q "html"; then
        echo "✅ Django runserver çalışıyor"
    else
        echo "❌ Django runserver çalışmıyor"
        cat django_test.log
    fi

    # Kill test server
    kill $DJANGO_PID 2>/dev/null
    rm -f django_test.log

else
    echo "❌ Virtual environment bulunamadı"
fi

# 6. Log kontrolü
echo ""
echo "📝 Gunicorn Logları:"
echo "--------------------"
tail -10 /root/moldpark/logs/gunicorn_error.log 2>/dev/null || echo "Error log bulunamadı"
tail -10 /root/moldpark/logs/gunicorn_access.log 2>/dev/null || echo "Access log bulunamadı"

# 7. Konfigürasyon kontrolü
echo ""
echo "⚙️  Konfigürasyon:"
echo "------------------"
echo "Gunicorn service dosyası:"
if [ -f "/etc/systemd/system/gunicorn.service" ]; then
    echo "✅ Service dosyası mevcut"
    cat /etc/systemd/system/gunicorn.service | grep -E "(ExecStart|WorkingDirectory|User)"
else
    echo "❌ Service dosyası bulunamadı"
fi

echo ""
echo "Environment dosyası:"
if [ -f "/root/moldpark/.env" ]; then
    echo "✅ .env dosyası mevcut"
    grep -E "(DEBUG|SECRET_KEY|ALLOWED_HOSTS)" /root/moldpark/.env | head -3
else
    echo "❌ .env dosyası bulunamadı"
fi

# 8. Ağ testi
echo ""
echo "🌐 Ağ Testleri:"
echo "---------------"
echo "Localhost bağlantısı:"
curl -s -I http://127.0.0.1:8000 | head -3 || echo "❌ Localhost bağlantı hatası"

echo "Loopback bağlantısı:"
curl -s -I http://localhost:8000 | head -3 || echo "❌ Localhost bağlantı hatası"

# 9. Öneriler
echo ""
echo "🎯 Öneriler:"
echo "------------"
echo "1. Gunicorn restart: sudo systemctl restart gunicorn"
echo "2. Log kontrol: tail -f /root/moldpark/logs/gunicorn_error.log"
echo "3. Manuel test: python manage.py runserver 127.0.0.1:8000"
echo "4. Service reload: sudo systemctl daemon-reload"

