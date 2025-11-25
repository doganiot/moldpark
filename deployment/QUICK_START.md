# 🚀 MoldPark Hızlı Kurulum Rehberi

## ✅ Otomatik Kurulum (Önerilen)

VPS'de tek komutla tüm kurulumu yapabilirsiniz:

```bash
# Proje dizinine gidin
cd /root/moldpark

# Script'i çalıştırılabilir yapın
chmod +x deployment/auto_setup.sh

# Otomatik kurulumu başlatın
sudo bash deployment/auto_setup.sh
```

Bu script otomatik olarak:
- ✅ Nginx kurulumunu kontrol eder/kurur
- ✅ Nginx konfigürasyonunu ayarlar
- ✅ Gunicorn systemd servisini kurar
- ✅ Static dosyaları toplar
- ✅ Servisleri başlatır
- ✅ Durum kontrolü yapar

## 📋 Manuel Kurulum (Alternatif)

Eğer otomatik script çalışmazsa, adım adım manuel kurulum yapabilirsiniz:

### 1. Nginx Kurulumu
```bash
sudo apt update
sudo apt install -y nginx
sudo cp /root/moldpark/deployment/nginx_moldpark.conf /etc/nginx/sites-available/moldpark
sudo ln -s /etc/nginx/sites-available/moldpark /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 2. Gunicorn Servisi
```bash
sudo cp /root/moldpark/deployment/gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

### 3. Static Dosyalar
```bash
cd /root/moldpark
source venv/bin/activate
python manage.py collectstatic --noinput
```

## 🔍 Kurulum Sonrası Kontrol

```bash
# Servis durumları
sudo systemctl status gunicorn
sudo systemctl status nginx

# Port kontrolü
sudo netstat -tuln | grep -E ':(80|8000)'

# Log kontrolü
tail -f /root/moldpark/logs/gunicorn_error.log
tail -f /var/log/nginx/moldpark_error.log
```

## 🌐 Site Erişimi

- **HTTP**: http://moldpark.com
- **IP**: http://72.62.0.8
- **DNS yayılımı**: 5-30 dakika sürebilir

## 🔒 HTTPS Kurulumu (Opsiyonel)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d moldpark.com -d www.moldpark.com
```

## ❌ Sorun Giderme

### Gunicorn çalışmıyor
```bash
sudo systemctl status gunicorn
sudo journalctl -u gunicorn -n 50
```

### Nginx çalışmıyor
```bash
sudo systemctl status nginx
sudo nginx -t
```

### Port 8000 kullanımda
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
sudo systemctl restart gunicorn
```

