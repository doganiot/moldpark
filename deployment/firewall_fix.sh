#!/bin/bash

# Hostinger VPS Firewall Fix
# Port 80 ve 443'ü açmak için alternatif çözüm

echo "🔥 Hostinger VPS Firewall Fix"

# UFW'yi kur (varsa)
if command -v ufw &> /dev/null; then
    echo "UFW kurulu, ayarları kontrol ediliyor..."
    sudo ufw status

    # UFW kuralları ekle
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable

    echo "✅ UFW kuralları eklendi"
else
    echo "⚠️  UFW kurulu değil, Hostinger panelinden portları açın"
fi

# Nginx'i port 8000'e yönlendir (geçici çözüm)
echo "🔄 Nginx'i port 8000'e yönlendiriyorum..."

sudo cp /etc/nginx/sites-available/moldpark /etc/nginx/sites-available/moldpark.backup

cat > /etc/nginx/sites-available/moldpark << 'EOF'
server {
    listen 8000;
    server_name moldpark.com www.moldpark.com 72.62.0.8;

    access_log /var/log/nginx/moldpark_access.log;
    error_log /var/log/nginx/moldpark_error.log;

    client_max_body_size 100M;

    location /static/ {
        alias /root/moldpark/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /root/moldpark/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location = /favicon.ico {
        access_log off;
        log_not_found off;
        alias /root/moldpark/staticfiles/favicon.ico;
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_pass http://127.0.0.1:8000;
        proxy_redirect off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

sudo systemctl reload nginx

echo ""
echo "✅ Geçici çözüm uygulandı!"
echo "🌐 Site: http://moldpark.com:8000"
echo "📝 Port 8000 kullanılıyor (firewall sorunu çözülünceye kadar)"
echo ""
echo "🔥 Kalıcı çözüm için Hostinger hPanel'den:"
echo "   - Port 80 (HTTP) ve 443 (HTTPS) kuralları ekleyin"
echo "   - Sonra Nginx'i normale döndürün"

