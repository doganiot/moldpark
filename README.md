# MoldPark - Kulak Kalıbı Üretim Yönetim Sistemi

MoldPark, işitme merkezi ve kulak kalıbı üretim süreçlerini dijitalleştiren modern bir Django web uygulamasıdır.

## 📋 Özellikler

### 🏢 **Merkez Yönetimi**
- Merkez kaydı ve profil yönetimi
- Kalıp gönderim limitleri
- Bildirim tercihleri
- Performans takibi

### 🧩 **Kalıp İşlemleri**
- Kalıp oluşturma ve düzenleme (Tam Konka, Yarım Konka, Probe, İskelet, CIC, ITE, ITC)
- Durum takibi (Bekliyor, İşleniyor, Tamamlandı, Revizyon, Kargoda, Teslim Edildi)
- STL/OBJ/PLY dosya yükleme
- Kalıp geçmişi ve detayları

### 👨‍💼 **Admin Paneli**
- Merkez yönetimi ve istatistikleri
- Kalıp durumu güncelleme
- Model yükleme sistemi
- Sistem geneli raporlar
- Chart.js ile dinamik grafikler

### 🔔 **Bildirim Sistemi**
- Gerçek zamanlı bildirimler
- Email bildirimleri
- Okunma durumu takibi
- Filtreleme ve arama

### 💬 **Mesajlaşma**
- Merkezler arası iletişim
- Mesaj arşivleme
- Hızlı yanıt sistemi

### 🎯 **Kalite Kontrol**
- Kalite kontrol listeleri
- Puanlama sistemi
- Kontrol geçmişi

## 🛠️ Teknoloji Stack

- **Backend:** Django 4.2.23
- **Frontend:** Bootstrap 5, jQuery, Font Awesome 6
- **Database:** SQLite (Development)
- **Authentication:** django-allauth
- **Notifications:** django-notifications-hq
- **Forms:** django-crispy-forms
- **File Management:** django-cleanup

## 📦 Kurulum

### Gereksinimler
- Python 3.13.0+
- pip
- virtualenv (önerilen)

### Adımlar

1. **Repository'yi klonlayın:**
```bash
git clone https://github.com/yourusername/moldpark.git
cd moldpark
```

2. **Virtual environment oluşturun:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate     # Windows
```

3. **Bağımlılıkları yükleyin:**
```bash
pip install -r requirements.txt
```

4. **Veritabanını oluşturun:**
```bash
python manage.py migrate
```

5. **Superuser oluşturun:**
```bash
python manage.py createsuperuser
```

6. **Statik dosyaları toplayın:**
```bash
python manage.py collectstatic
```

7. **Sunucuyu başlatın:**
```bash
python manage.py runserver
```

## 🎮 Kullanım

### Admin Paneli
- Superuser hesabı ile `/admin/` adresinden yönetim paneline erişin
- Merkez yönetimi için `/center/admin/` adresini kullanın

### Merkez Kullanıcıları
- Ana sayfadan kayıt olun
- Merkez bilgilerinizi tamamlayın
- Kalıp oluşturmaya başlayın

## 📊 Kalıp Türleri

- **Tam Konka:** Güçlü performans ve maksimum yalıtım
- **Yarım Konka:** Konforlu kullanım ve estetik görünüm
- **Probe:** Görünmez tasarım ve kanal içi konfor
- **İskelet:** Hafif yapı ve kozmetik görünüm
- **CIC, ITE, ITC:** Çeşitli işitme kaybı seviyeleri için

## 🔧 Yapılandırma

### Environment Variables
```bash
# .env dosyası oluşturun
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email ayarları
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 📝 API Endpoints

### Bildirimler
- `GET /center/notifications/` - Bildirim listesi
- `POST /center/notifications/{id}/read/` - Bildirimi okundu işaretle
- `POST /center/notifications/mark-all-read/` - Tümünü okundu işaretle

### Admin
- `GET /center/admin/centers/` - Merkez listesi
- `GET /center/admin/centers/stats/` - İstatistikler
- `POST /center/admin/molds/{id}/update-status/` - Kalıp durumu güncelle

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit yapın (`git commit -m 'Add some AmazingFeature'`)
4. Branch'i push edin (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasını inceleyin.

## 📞 İletişim

- **Email:** info@moldpark.com
- **Telefon:** +90 (544) 221 92 84
- **Website:** [moldpark.com](https://moldpark.com)

## 🙏 Teşekkürler

- Bootstrap ekibi
- Django topluluğu
- Font Awesome
- Chart.js geliştiricileri

---

**MoldPark** - Kulak kalıbı üretim süreçlerinizi dijitalleştirin! 🎯 