#!/bin/bash

# MoldPark Site Test Script

echo "🔍 MoldPark Site Testi"
echo "======================"

# 1. DNS Kontrolü
echo ""
echo "📡 DNS Kontrolü:"
echo "----------------"
echo "moldpark.com DNS sorgusu:"
nslookup moldpark.com 2>/dev/null || host moldpark.com 2>/dev/null || dig moldpark.com +short

echo ""
echo "www.moldpark.com DNS sorgusu:"
nslookup www.moldpark.com 2>/dev/null || host www.moldpark.com 2>/dev/null || dig www.moldpark.com +short

# 2. Ping Testi
echo ""
echo "🏓 Ping Testi:"
echo "--------------"
ping -c 3 moldpark.com 2>/dev/null || echo "Ping başarısız"

# 3. HTTP Testleri
echo ""
echo "🌐 HTTP Testleri:"
echo "-----------------"

echo "Domain ile test (moldpark.com):"
curl -I http://moldpark.com 2>/dev/null | head -3

echo ""
echo "IP ile test (72.62.0.8):"
curl -I http://72.62.0.8 2>/dev/null | head -3

echo ""
echo "Localhost test:"
curl -I http://localhost 2>/dev/null | head -3

echo ""
echo "Gunicorn direkt test:"
curl -I http://127.0.0.1:8000 2>/dev/null | head -3

# 4. Port Kontrolü
echo ""
echo "🔌 Port Durumu:"
echo "---------------"
netstat -tuln | grep -E ':80|:8000' || ss -tuln | grep -E ':80|:8000'

# 5. Servis Kontrolü
echo ""
echo "⚙️  Servis Durumu:"
echo "------------------"
echo "Nginx: $(systemctl is-active nginx)"
echo "Gunicorn: $(systemctl is-active gunicorn)"

# 6. DNS Cache Temizleme
echo ""
echo "🧹 DNS Cache Temizleme:"
echo "-----------------------"
if command -v systemd-resolve &> /dev/null; then
    sudo systemd-resolve --flush-caches 2>/dev/null && echo "✅ DNS cache temizlendi" || echo "❌ Cache temizlenemedi"
else
    echo "systemd-resolve bulunamadı"
fi

# 7. Alternatif DNS Test
echo ""
echo "🔄 Google DNS ile Test:"
echo "-----------------------"
nslookup moldpark.com 8.8.8.8 2>/dev/null || dig @8.8.8.8 moldpark.com +short

echo ""
echo "📊 Test Sonuçları:"
echo "------------------"
echo "✅ Eğer IP ile erişim çalışıyorsa: DNS yayılma bekleniyor"
echo "✅ Eğer localhost çalışıyorsa: Site aktif"
echo "❌ Eğer hiçbiri çalışmıyorsa: Servis sorunu var"
echo ""
echo "🌐 Tarayıcınızda test edin:"
echo "   http://72.62.0.8 (IP ile)"
echo "   http://moldpark.com (Domain ile)"
