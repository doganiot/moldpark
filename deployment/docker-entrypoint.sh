#!/bin/bash

echo "🐳 MoldPark Docker Container Başlatılıyor..."

# Database bekle (PostgreSQL kullanılıyorsa)
if [ "$DB_ENGINE" = "postgresql" ]; then
    echo "⏳ PostgreSQL bekleniyor..."
    while ! nc -z $DB_HOST $DB_PORT; do
        sleep 0.1
    done
    echo "✅ PostgreSQL hazır!"
fi

# Migration'ları uygula
echo "📦 Migration'lar uygulanıyor..."
python manage.py migrate --noinput

# Static dosyaları topla
echo "📁 Static dosyalar toplanıyor..."
python manage.py collectstatic --noinput --clear

# Superuser kontrolü
echo "👤 Superuser kontrolü..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@moldpark.com', 'admin123')
    print('✅ Superuser oluşturuldu: admin/admin123')
else:
    print('✅ Superuser mevcut')
END

# Log klasörü izinleri
chmod -R 777 /app/logs

echo "🚀 Container hazır!"

# Komut çalıştır
exec "$@"

