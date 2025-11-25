# MoldPark Domain Kurulum Adımları

## ✅ Tamamlanan İşlemler

1. **DNS A Kaydı Güncellendi**
   - Domain: moldpark.com
   - IP: 72.62.0.8 (VPS IP adresi)
   - Durum: ✅ Güncellendi

## 📋 Yapılacak Adımlar (VPS'de Çalıştırılacak)

### 1. Nginx Kurulumu ve Konfigürasyonu

```bash
# Nginx kurulumu (eğer yoksa)
sudo apt update
sudo apt install -y nginx

# Nginx konfigürasyon dosyasını kopyala
sudo cp /root/moldpark/deployment/nginx_moldpark.conf /etc/nginx/sites-available/moldpark

# Symlink oluştur
sudo ln -s /etc/nginx/sites-available/moldpark /etc/nginx/sites-enabled/

# Varsayılan Nginx sitesini devre dışı bırak (opsiyonel)
sudo rm /etc/nginx/sites-enabled/default

# Nginx konfigürasyonunu test et
sudo nginx -t

# Nginx'i yeniden başlat
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 2. Gunicorn Systemd Servisi

```bash
# Gunicorn servis dosyasını kopyala
sudo cp /root/moldpark/deployment/gunicorn.service /etc/systemd/system/gunicorn.service

# Systemd'yi yeniden yükle
sudo systemctl daemon-reload

# Gunicorn servisini başlat
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

# Durumu kontrol et
sudo systemctl status gunicorn
```

### 3. Static Dosyaları Toplama

```bash
cd /root/moldpark
source venv/bin/activate

# Static dosyaları topla
python manage.py collectstatic --noinput
```

### 4. Environment Variables (.env dosyası)

```bash
cd /root/moldpark
nano .env
```

`.env` dosyasında şunlar olmalı:

```env
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=moldpark.com,www.moldpark.com,72.62.0.8,localhost
CSRF_TRUSTED_ORIGINS=https://moldpark.com,https://www.moldpark.com
DB_NAME=moldpark
DB_USER=moldpark
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
```

### 5. Gunicorn'u Yeniden Başlat

```bash
sudo systemctl restart gunicorn
```

### 6. Log Kontrolü

```bash
# Gunicorn logları
tail -f /root/moldpark/logs/gunicorn_error.log
tail -f /root/moldpark/logs/gunicorn_access.log

# Nginx logları
tail -f /var/log/nginx/moldpark_error.log
tail -f /var/log/nginx/moldpark_access.log
```

## 🔒 HTTPS Kurulumu (Let's Encrypt)

```bash
# Certbot kurulumu
sudo apt install -y certbot python3-certbot-nginx

# SSL sertifikası al
sudo certbot --nginx -d moldpark.com -d www.moldpark.com

# Otomatik yenileme testi
sudo certbot renew --dry-run
```

Certbot otomatik olarak Nginx konfigürasyonunu güncelleyecek ve HTTPS'i aktif edecek.

## 🔍 Sorun Giderme

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
```

### DNS yayılımı kontrolü
```bash
# DNS'in yayıldığını kontrol et
dig moldpark.com
nslookup moldpark.com
```

DNS yayılımı 5-30 dakika sürebilir.

## ✅ Test

1. **HTTP Test**: `http://moldpark.com` veya `http://72.62.0.8`
2. **HTTPS Test**: `https://moldpark.com` (SSL kurulumundan sonra)
3. **Static Dosyalar**: `http://moldpark.com/static/...`
4. **Media Dosyalar**: `http://moldpark.com/media/...`

## 📝 Notlar

- VPS IP: 72.62.0.8
- Domain: moldpark.com
- Gunicorn Port: 8000 (localhost)
- Nginx Port: 80/443
- Proje Dizini: /root/moldpark
- Virtual Environment: /root/moldpark/venv

