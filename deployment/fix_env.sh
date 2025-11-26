#!/bin/bash

# MoldPark .env dosyasını düzelt

cd /root/moldpark

# .env dosyası yoksa oluştur
if [ ! -f .env ]; then
    cat > .env << 'EOF'
DEBUG=False
SECRET_KEY=django-insecure-change-this-in-production-$(openssl rand -hex 32)
ALLOWED_HOSTS=moldpark.com,www.moldpark.com,72.62.0.8,localhost
CSRF_TRUSTED_ORIGINS=https://moldpark.com,https://www.moldpark.com
# SQLite kullan (PostgreSQL kurulmamış)
DB_ENGINE=sqlite3
DB_NAME=db.sqlite3
# DB_USER=
# DB_PASSWORD=
# DB_HOST=localhost
# DB_PORT=5432
EOF
else
    # .env varsa SQLite'ye çevir
    sed -i 's/DB_ENGINE=.*/DB_ENGINE=sqlite3/' .env
    sed -i 's/DB_NAME=.*/DB_NAME=db.sqlite3/' .env
    sed -i 's/^DB_USER=.*/# DB_USER=/' .env
    sed -i 's/^DB_PASSWORD=.*/# DB_PASSWORD=/' .env
    sed -i 's/^DB_HOST=.*/# DB_HOST=localhost/' .env
    sed -i 's/^DB_PORT=.*/# DB_PORT=5432/' .env
fi

echo ".env dosyası SQLite için güncellendi"

