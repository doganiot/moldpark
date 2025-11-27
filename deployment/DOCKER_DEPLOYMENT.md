# 🐳 MoldPark Docker Deployment Rehberi

## 📋 Gereksinimler

- Hostinger VPS (Ubuntu 24.04)
- Domain: moldpark.com
- Docker & Docker Compose

## 🚀 Hızlı Kurulum (Önerilen)

### 1️⃣ VPS'i Sıfırlayın

Hostinger hPanel'den:
1. VPS → srv1141206
2. "Reinstall" veya "Reset" butonu
3. **Ubuntu 24.04 LTS** seçin
4. Onaylayın

### 2️⃣ Post-Install Script Kullanın

VPS sıfırlandıktan sonra ilk açılışta:

```bash
curl -fsSL https://raw.githubusercontent.com/doganiot/moldpark/main/deployment/vps_docker_install.sh | bash
```

✅ **Tek komut, her şey hazır!**

## 📝 Manuel Kurulum

### 1. Docker Kurulumu

```bash
# Sistem güncelleme
sudo apt-get update && sudo apt-get upgrade -y

# Docker kurulumu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose kurulumu
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Projeyi İndirin

```bash
cd /root
git clone https://github.com/doganiot/moldpark.git
cd moldpark
```

### 3. .env Dosyası Oluşturun

```bash
cat > .env << EOF
DEBUG=False
SECRET_KEY=django-insecure-$(openssl rand -hex 32)
ALLOWED_HOSTS=moldpark.com,www.moldpark.com,72.62.0.8,localhost
CSRF_TRUSTED_ORIGINS=http://moldpark.com,http://www.moldpark.com

# SQLite için
DB_ENGINE=sqlite3
EOF
```

### 4. Docker'ı Başlatın

```bash
# Klasörleri oluştur
mkdir -p staticfiles media logs
chmod -R 777 staticfiles media logs

# Container'ları başlat
docker-compose up -d --build

# Log'ları izle
docker-compose logs -f
```

## 🔧 Firewall Ayarları

Hostinger hPanel → VPS → Firewall:

| Port | Protokol | Kaynak |
|------|----------|--------|
| 22   | SSH      | any    |
| 80   | HTTP     | any    |
| 443  | HTTPS    | any    |

## 🎯 Site Erişimi

- **HTTP**: http://moldpark.com
- **Admin**: http://moldpark.com/admin/
  - Kullanıcı: `admin`
  - Şifre: `admin123`

## 📋 Faydalı Komutlar

```bash
# Log'ları izle
docker-compose logs -f

# Container durumu
docker-compose ps

# Yeniden başlat
docker-compose restart

# Durdur
docker-compose down

# Başlat
docker-compose up -d

# Django komutları
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic

# Container içine gir
docker-compose exec web bash
```

## 🔄 Güncelleme

```bash
cd /root/moldpark
git pull
docker-compose down
docker-compose up -d --build
```

## 🐛 Sorun Giderme

### Container'lar başlamıyor

```bash
docker-compose logs
docker-compose ps
```

### Port 80 kullanımda

```bash
sudo netstat -tlnp | grep :80
sudo lsof -i :80
```

### Static dosyalar yüklenmiyor

```bash
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart nginx
```

## 🔐 SSL Sertifikası (Opsiyonel)

```bash
# Certbot kurulumu
sudo apt-get install certbot

# SSL al (Container'lar durdurulmalı)
docker-compose down
sudo certbot certonly --standalone -d moldpark.com -d www.moldpark.com

# Docker Compose'u SSL ile güncelleyin
# nginx_docker.conf'a SSL konfigürasyonu ekleyin
```

## 📊 Sistem Durumu

```bash
# Disk kullanımı
df -h

# Docker kullanımı
docker system df

# Container log boyutu
docker-compose logs --tail=100

# Temizlik
docker system prune -a
```

## ✅ Başarılı Kurulum Kontrol Listesi

- [ ] VPS sıfırlandı
- [ ] Docker kuruldu
- [ ] Proje indirildi
- [ ] .env dosyası oluşturuldu
- [ ] Container'lar başlatıldı
- [ ] Firewall kuralları eklendi
- [ ] Site açılıyor
- [ ] Admin paneli çalışıyor

## 🆘 Destek

Sorun yaşarsanız:

1. Log'ları kontrol edin: `docker-compose logs -f`
2. Container durumunu kontrol edin: `docker-compose ps`
3. GitHub Issues: https://github.com/doganiot/moldpark/issues

