## MoldPark Prodüksiyon Kurulum Rehberi

Bu doküman, projeyi Hostinger (veya benzeri) bir VPS üzerinde **Gunicorn + Nginx** mimarisi ile yayınlamak için atılması gereken adımları özetler. Tüm komutlar Ubuntu/Debian tabanlı sistemler içindir.

### 1. Ön Koşullar
- Python 3.12+
- Git, Nginx, build-essential paketleri
- PostgreSQL (opsiyonel, SQLite sadece geliştirme içindir)
- Alan adı > sunucu IP eşlemesi

```
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nginx
```

### 2. Kaynak Kod ve Sanal Ortam
```
cd ~/www
git clone <repo-url> moldpark
cd moldpark
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Ortam Değişkenleri
- `env.example` dosyasını `.env` olarak kopyalayın.
- `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` ve veritabanı bilgilerinin tamamını güncelleyin.
- Eğer reverse proxy kullanıyorsanız HTTPS trafiği otomatik algılanır (`SECURE_PROXY_SSL_HEADER` tanımlı).

### 4. Django Hazırlığı
```
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser  # ilk kurulumda
```

### 5. Gunicorn Servisi (systemd)
`/etc/systemd/system/gunicorn.service`
```
[Unit]
Description=Gunicorn service for MoldPark
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/home/<USER>/www/moldpark
Environment="PATH=/home/<USER>/www/moldpark/venv/bin"
ExecStart=/home/<USER>/www/moldpark/venv/bin/gunicorn backend.wsgi:application --bind 127.0.0.1:8002
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn
sudo systemctl status gunicorn
```

### 6. Nginx Reverse Proxy
`/etc/nginx/sites-available/moldpark`
```
server {
    server_name example.com www.example.com;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/<USER>/www/moldpark/staticfiles/;
    }

    location /media/ {
        alias /home/<USER>/www/moldpark/media/;
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8002;
    }
}
```

```
sudo ln -s /etc/nginx/sites-available/moldpark /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

HTTPS için: `sudo apt install certbot python3-certbot-nginx` ardından `sudo certbot --nginx -d example.com -d www.example.com`.

### 7. Güncellemeler ve Deploy
```
cd ~/www/moldpark
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

Bu adımlar tamamlandığında uygulama `http://localhost:8002` üzerinden Gunicorn’da çalışır, Nginx ise HTTP/HTTPS trafiğini yönlendirir.

