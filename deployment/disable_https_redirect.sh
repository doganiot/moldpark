#!/bin/bash

echo "🔧 HTTPS Redirect Kapatılıyor..."

# HTTPS redirect satırlarını yorum yap
sudo sed -i 's/return 301 https/# return 301 https/g' /etc/nginx/sites-available/moldpark

# Nginx test
echo "📋 Nginx test ediliyor..."
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Konfigürasyon geçerli"
    
    # Nginx restart
    echo "🔄 Nginx yeniden başlatılıyor..."
    sudo systemctl restart nginx
    
    echo "✅ Tamamlandı!"
    echo "🌐 Şimdi http://moldpark.com adresini deneyin"
else
    echo "❌ Nginx konfigürasyon hatası"
fi

