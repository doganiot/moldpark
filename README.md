# 🦻 MoldPark - Kulak Kalıbı Üretim Yönetim Sistemi

MoldPark, işitme cihazı merkezleri ve kalıp üreticileri arasında şeffaf, güvenli ve verimli bir üretim sürecini yönetmek için geliştirilmiş kapsamlı bir web platformudur.

## 🌟 Özellikler

### 🏥 İşitme Merkezleri İçin
- **Kalıp Yönetimi**: 7 farklı kalıp türü desteği (Tam Konka, Yarım Konka, İskelet, Probe, CIC, ITE, ITC)
- **3D Dosya Yönetimi**: STL, OBJ, PLY formatlarında dosya yükleme ve indirme
- **Üretici Ağı**: Güvenilir üreticilerle network kurma ve yönetme
- **Sipariş Takibi**: Gerçek zamanlı üretim süreci takibi
- **Kalite Kontrol**: Detaylı kalite skorlama sistemi
- **Mesajlaşma**: Üreticilerle doğrudan iletişim

### 🏭 Üreticiler İçin
- **Sipariş Yönetimi**: Gelen siparişleri öncelik sırasına göre yönetme
- **Üretim Takibi**: 8 aşamalı üretim süreci (Tasarım → Üretim → Kalite → Teslimat)
- **Dosya Transfer**: Güvenli dosya indirme ve yükleme sistemi
- **Kargo Entegrasyonu**: Kargo takip numarası ve maliyet yönetimi
- **Kapasite Yönetimi**: Aylık üretim limiti ve kullanım takibi
- **Performans Analizi**: Detaylı üretim metrikleri

### 🔧 Sistem Yöneticileri İçin
- **Merkezi Yönetim**: Tüm merkezler ve üreticilerin tek panelden yönetimi
- **Güvenlik Kontrolü**: Çok katmanlı güvenlik sistemi ve erişim kontrolü
- **Performans İzleme**: Gerçek zamanlı sistem metrikleri ve uyarılar
- **API Entegrasyonu**: RESTful API ile dış sistem entegrasyonları
- **Otomatik Raporlama**: Detaylı analiz ve raporlama araçları

## 🚀 Yeni Özellikler (v2.0.0)

### ⚡ Performans İyileştirmeleri
- **Database Optimizasyonu**: Kritik sorgular için özel index'ler
- **Cache Sistemi**: Redis entegrasyonu ile hızlı veri erişimi
- **Lazy Loading**: Büyük dosyalar için optimize edilmiş yükleme
- **Query Optimization**: N+1 sorgu sorunlarının çözümü

### 🔒 Güvenlik Geliştirmeleri
- **Rol Bazlı Erişim**: Üretici/Merkez/Admin ayrımı ile güvenli erişim
- **Session Management**: Gelişmiş oturum yönetimi
- **File Security**: Dosya yükleme güvenlik kontrolleri
- **CSRF Protection**: Cross-site request forgery koruması

### 📊 Yeni Dashboard Özellikleri
- **Sistem İstatistikleri**: Gerçek zamanlı performans metrikleri
- **Üretim Hattı Görünümü**: Aşama bazlı sipariş takibi
- **Uyarı Sistemi**: Otomatik sistem uyarıları ve bildirimler
- **Aktivite Timeline**: Son aktiviteler ve değişiklikler

### 🔧 Geliştirici Araçları
- **Debug Toolbar**: Development ortamında detaylı debug bilgileri
- **Management Commands**: Sistem kontrolü ve bakım komutları
- **API Endpoints**: Sistem durumu ve istatistikler için REST API
- **Logging System**: Kapsamlı log kayıt sistemi

## 🛠️ Teknoloji Stack'i

- **Backend**: Django 4.2.23 (Python)
- **Frontend**: Bootstrap 5 + JavaScript
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Cache**: Redis (Production) / LocalMem (Development)
- **File Storage**: Local Storage / Cloud Storage Ready
- **Authentication**: Django AllAuth
- **API**: Django REST Framework Ready

## 📋 Sistem Gereksinimleri

- Python 3.8+
- Django 4.2+
- 2GB RAM (minimum)
- 10GB Disk Space
- Modern web browser

## ⚙️ Kurulum

### 1. Projeyi İndirin
```bash
git clone https://github.com/yourusername/moldpark.git
cd moldpark
```

### 2. Virtual Environment Oluşturun
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate     # Windows
```

### 3. Bağımlılıkları Kurun
```bash
pip install -r requirements.txt
```

### 4. Environment Ayarları
```bash
cp env.example .env
# .env dosyasını düzenleyin
```

### 5. Database Kurulumu
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Static Dosyaları Toplayın
```bash
python manage.py collectstatic
```

### 7. Sunucuyu Başlatın
```bash
python manage.py runserver
```

## 🔧 Management Commands

### Sistem Kontrolü
```bash
# Temel kontrol
python manage.py system_check

# Detaylı kontrol
python manage.py system_check --verbose

# Sorunları otomatik düzelt
python manage.py system_check --fix
```

### Test Verisi Oluşturma
```bash
# Test üreticisi oluştur
python manage.py create_test_producer

# Üretici doğrulama
python manage.py verify_producers
```

## 🌐 API Endpoints

### Sistem Durumu
```
GET /api/system-status/          # Genel sistem istatistikleri
GET /api/production-pipeline/    # Üretim hattı durumu
GET /api/alerts/                 # Sistem uyarıları
POST /api/health-check/          # Sağlık kontrolü
```

### Kullanım Örneği
```javascript
fetch('/api/system-status/')
  .then(response => response.json())
  .then(data => {
    console.log('Sistem Sağlığı:', data.system.health_score);
    console.log('Aktif Siparişler:', data.orders.active);
  });
```

## 📊 Dashboard Widget'ları

### Template Tag Kullanımı
```html
{% load moldpark_extras %}

<!-- Sistem istatistikleri -->
{% system_stats %}

<!-- Üretim hattı durumu -->
{% production_pipeline %}

<!-- Performans metrikleri -->
{% performance_metrics %}

<!-- Ağ sağlığı -->
{% network_health %}

<!-- Son aktiviteler -->
{% recent_activities limit=5 %}

<!-- Sistem uyarıları -->
{% system_alerts %}
```

## 🔐 Güvenlik Özellikleri

### Rol Bazlı Erişim Kontrolü
- **Superuser**: Tüm sistem erişimi
- **Center**: Sadece kendi merkez verileri
- **Producer**: Sadece kendi üretici verileri
- **Misafir**: Sadece genel sayfalar

### Veri Güvenliği
- Şifreli dosya aktarımı
- Session timeout yönetimi
- CSRF token koruması
- SQL injection koruması

## 📈 Performans Optimizasyonları

### Database İndexleri
- Sık kullanılan sorgular için özel indexler
- Composite indexler ile hızlı arama
- Foreign key optimizasyonları

### Cache Stratejisi
- Session cache
- Query result cache
- Static file cache
- Template fragment cache

## 🐛 Hata Ayıklama

### Debug Modu
```python
# settings.py
DEBUG = True
```

### Debug Toolbar
```
http://localhost:8000/__debug__/
```

### Log Dosyaları
```
logs/moldpark.log
```

## 📝 Changelog

### v2.0.0 (2025-06-18)
- ✨ Yeni dashboard widget sistemi
- ⚡ Performans optimizasyonları
- 🔒 Güçlendirilmiş güvenlik
- 📊 REST API endpoints
- 🔧 Management commands
- 📈 Database indexleri
- 🎨 UI/UX iyileştirmeleri

### v1.0.0 (2025-06-13)
- 🎉 İlk stable sürüm
- 🏥 Merkez yönetimi
- 🏭 Üretici sistemi
- 👂 Kalıp yönetimi
- 📨 Mesajlaşma sistemi

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit yapın (`git commit -m 'Add some AmazingFeature'`)
4. Push yapın (`git push origin feature/AmazingFeature`)
5. Pull Request açın

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın.

## 📞 İletişim

- **Proje**: MoldPark
- **Versiyon**: 2.0.0
- **Email**: info@moldpark.com
- **Website**: https://moldpark.com

## 🙏 Teşekkürler

Bu projeyi geliştirmede katkıda bulunan herkese teşekkürler!

---

**MoldPark** - Kulak kalıbı üretiminde yeni nesil çözüm 🦻 