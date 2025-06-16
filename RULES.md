# MoldPark Kulak Kalıbı Merkezi - Proje Kuralları

## 1. Kullanıcı Rolleri ve Yetkiler

### 1.1 Merkez Kullanıcıları
- Sadece kendi kalıplarını görüntüleyebilir ve yönetebilir
- Kalıp oluşturma, düzenleme ve silme yetkisi
- Kendi kalıpları için revizyon talep edebilir
- Yönetici ile mesajlaşabilir
- Bildirim tercihlerini yönetebilir

### 1.2 Yönetici (Admin)
- Tüm kalıpları görüntüleyebilir ve yönetebilir
- Kalıp durumlarını güncelleyebilir
- Revizyon taleplerini yönetebilir
- Kalite kontrol işlemlerini yapabilir
- Sistem ayarlarını yönetebilir

### 1.3 Misafir Kullanıcılar
- İletişim formu üzerinden mesaj gönderebilir
- Hizmetler ve kalıp tipleri hakkında bilgi alabilir
- Kayıt olabilir

## 2. Kalıp İşlemleri

### 2.1 Kalıp Tipleri
- Tam Konka
- Yarım Konka
- İskelet Tip
- Probe
- CIC
- ITE
- ITC

### 2.2 Kalıp Durumları
- Bekliyor
- İşleniyor
- Tamamlandı
- Revizyon
- Kargoda
- Teslim Edildi

### 2.3 Dosya Formatları
- Desteklenen formatlar: STL, OBJ, PLY
- Maksimum dosya boyutu: 50MB
- Tarama dosyaları 'scans/' dizininde saklanır
- Modellenen dosyalar 'modeled/' dizininde saklanır

## 3. Mesajlaşma ve Bildirimler

### 3.1 Mesaj Tipleri
- Merkez-Yönetici mesajları
- İletişim formu mesajları
- Sistem bildirimleri

### 3.2 Bildirim Tercihleri
- Yeni Sipariş
- Revizyon
- Tamamlanan Sipariş
- Acil Durum
- Sistem Bildirimleri



## 4. Güvenlik ve Veri Koruma

### 4.1 Kullanıcı Verileri
- Hasta bilgileri KVKK uyumlu saklanır
- Şifreler hash'lenerek saklanır
- Oturum güvenliği için CSRF koruması aktif

### 4.2 Dosya Güvenliği
- Sadece izin verilen formatlar kabul edilir
- Dosya boyutu kontrolü yapılır
- Virüs taraması yapılır

## 5. Teknik Gereksinimler

### 5.1 Yazılım Gereksinimleri
- Python 3.13.0
- Django 5.0.2
- next.js
- PostgreSQL veya SQLite3
- Modern web tarayıcısı (Chrome, Firefox, Safari)

### 5.2 Donanım Gereksinimleri
- Minimum 4GB RAM
- 10GB disk alanı
- Stabil internet bağlantısı

## 6. Bakım ve Destek

### 6.1 Yedekleme
- Günlük otomatik yedekleme
- Haftalık tam yedekleme
- Yedekler 30 gün saklanır

### 6.2 Destek Süreçleri
- Teknik destek: 09:00-18:00
- Acil durumlar: 7/24
- Maksimum yanıt süresi: 4 saat

## 7. Geliştirme Kuralları

### 7.1 Kod Standartları
- PEP 8 uyumlu Python kodu
- Docstring zorunluluğu
- Türkçe yorum ve değişken isimleri
- Modüler ve tekrar kullanılabilir kod

### 7.2 Versiyon Kontrolü
- Git kullanımı zorunlu
- Feature branch workflow
- Commit mesajları Türkçe
- Pull request incelemesi zorunlu

## 8. Performans Kriterleri

### 8.1 Sayfa Yükleme
- Ana sayfa: <2 saniye
- Dashboard: <3 saniye
- Kalıp listesi: <4 saniye

### 8.2 İşlem Süreleri
- Kalıp yükleme: <30 saniye
- Revizyon yanıtı: <24 saat
- Kalite kontrol: <48 saat

## 9. Raporlama

### 9.1 Merkez Raporları
- Aylık kalıp istatistikleri
- Revizyon oranları
- Ortalama tamamlanma süresi

### 9.2 Sistem Raporları
- Kullanıcı aktiviteleri
- Hata logları
- Performans metrikleri 