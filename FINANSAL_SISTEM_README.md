# MoldPark Finansal Yönetim Sistemi

## 📋 Genel Bakış

MoldPark'a kapsamlı bir finansal yönetim sistemi eklendi. Sistem, kullandıkça öde modeliyle çalışır ve hem işitme merkezleri hem de üretici merkezleri için otomatik faturalandırma sunar.

## 💰 Fiyatlandırma Yapısı

### MoldPark Standart Paket
- **Aylık Sistem Kullanımı:** 100 TL
- **Fiziksel Kalıp Gönderme:** 450 TL/adet
- **3D Kalıp Modelleme Hizmeti:** 50 TL/adet
- **Kullanım Limiti:** Sınırsız (kullandıkça öde)

### Komisyon Oranları
- **Kredi Kartı Komisyonu:** %3 (tüm işlemlerden)
- **MoldPark Komisyonu:** %6.5 (sadece üretici siparişlerinden)

### Yeni Fatura Sistemi (Merkezileştirilmiş)
- **İşitme Merkezi Admin:** Kalıp gönderimi için fatura keser (450 TL + %3 KK + %6.5 MoldPark)
- **Üretici Merkez:** Hizmet bedeli için fatura keser (üreticiye ödeme bilgilendirmesi)
- **Müşteri Ödemesi:** 450 TL + komisyonlar = 450 + 13.5 + 29.25 = 492.75 TL
- **Üretici Ödemesi:** 450 - 13.5 - 29.25 = 407.25 TL
- **MoldPark Kazancı:** 13.5 (KK) + 29.25 (hizmet) = 42.75 TL

## 🔧 Özellikler

### 1. Finansal Dashboard (`/financial/`)
**Erişim:** Sadece süper kullanıcılar (admin)

**İçerik:**
- Toplam gelir, net kar, komisyonlar
- İşitme merkezi ve üretici gelirleri
- Aylık trendler (son 6 ay)
- Genel istatistikler (aktif merkez, üretici, kalıp sayıları)
- Son faturalar
- Vadesi geçmiş faturalar
- Dönem filtreleme (Bu ay, Geçen ay, Bu yıl, Tüm zamanlar)

### 2. Fatura Listesi (`/financial/invoices/`)
**Özellikler:**
- Tür filtresi (İşitme Merkezi / Üretici)
- Durum filtresi (Bekliyor / Ödendi / Vadesi Geçmiş)
- Özet istatistikler
- Toplu fatura görüntüleme
- Ödendi işaretleme

### 3. Fatura Detayı (`/financial/invoices/<id>/`)
**İçerik:**
- Detaylı fatura bilgileri
- Kalıp/hizmet kalemleri
- Komisyon hesaplamaları
- Yazdırılabilir format
- Ödeme durumu güncelleme

### 4. Finansal Raporlar (`/financial/reports/`)
**İçerik:**
- Yıllık finansal özet
- Aylık detaylı raporlar
- Gelir dağılımı grafikleri
- Ortalama değerler
- Kar marjları

### 5. Yeni Fatura Oluşturma Sistemi
**Merkez Admin Fatura Oluşturma:**
```javascript
// AJAX ile kalıp gönderimi faturası oluşturma
POST /invoices/create/center-admin/{mold_id}/
```

**Üretici Fatura Oluşturma:**
```javascript
// AJAX ile hizmet bedeli faturası oluşturma
POST /invoices/create/producer/{mold_id}/
```

**Özellikler:**
- Sadece ilgili kullanıcılar fatura kesebilir
- Otomatik komisyon hesaplaması
- Detaylı işlem takibi
- Kaynak ve hedef bilgilerinin loglanması

### 6. MoldPark Tahsilat Raporu (`/financial/collections/`)
**Erişim:** Sadece süper kullanıcılar

**İçerik:**
- Toplam tahsilat ve ödemeler
- MoldPark kazanç analizi
- Komisyon kırılımları
- Hizmet veren bazlı analiz
- Tutar kaynakları takibi
- İşlem durumu raporlaması
- Detaylı transaction geçmişi

### 7. Otomatik Fatura Oluşturma (Eski Sistem)

**İşlevler:**
- Her ayın 28'inde otomatik çalışacak şekilde ayarlanabilir (cron/scheduler)
- İşitme merkezleri için: Aylık ücret + fiziksel kalıp + 3D kalıp modelleme
- Üretici merkezler için: Brüt gelir - MoldPark komisyonu (%6.5) - kredi kartı komisyonu (%3)
- Otomatik mali özet oluşturma

### 6. İşitme Merkezi Kullanım Detayları Bölümü (`/center/usage/`)
**Erişim:** Sadece işitme merkezi kullanıcıları

**Özellikler:**
- Mevcut ay kullanım özeti (toplam kalıp, aylık ücret, tahmini maliyet)
- Aylık kullanım geçmişi tablosu
- Detaylı maliyet kırılımları (fiziksel kalıp, 3D modelleme, komisyonlar)
- Fatura listesi görüntüleme ve filtreleme
- Fatura detay görüntüleme
- İlgili kalıp bilgilerini görüntüleme
- Ödeme durumu takibi

### 7. Üretici Merkezler Ödemeler Bölümü (`/producer/payments/`)
**Erişim:** Sadece üretici merkezi kullanıcıları

**Özellikler:**
- Mevcut ay ödeme özeti (tamamlanan sipariş, tahmini gelir, komisyonlar, net ödeme)
- Aylık ödeme geçmişi tablosu
- Detaylı komisyon hesaplaması (%6.5 MoldPark + %3 KK)
- Ödeme faturası görüntüleme ve filtreleme
- Ödeme detay görüntüleme
- İlgili sipariş bilgilerini görüntüleme
- Ödeme durumu takibi

## 📊 Veritabanı Modelleri

### Invoice (Fatura)
**Alanlar:**
- `invoice_type`: center (İşitme Merkezi) veya producer (Üretici)
- `user`: Fatura sahibi
- `invoice_number`: Otomatik oluşturulan numara (örn: INV-2025-10-0001)
- `issue_date`, `due_date`, `payment_date`: Tarih bilgileri
- `status`: issued, paid, overdue, cancelled

**İşitme Merkezi Faturaları:**
- `monthly_fee`: Aylık sistem kullanım ücreti (100 TL)
- `physical_mold_count`, `physical_mold_cost`: Fiziksel kalıp sayısı ve maliyeti
- `digital_scan_count`, `digital_scan_cost`: Digital tarama sayısı ve maliyeti
- `subtotal`: Ara toplam
- `credit_card_fee`: Kredi kartı komisyonu (%2.6)
- `total_amount`: Toplam tutar

**Üretici Faturaları:**
- `producer_order_count`: Sipariş sayısı
- `producer_revenue`: Brüt gelir
- `moldpark_commission`: MoldPark komisyonu (%6.5)
- `credit_card_fee`: Kredi kartı komisyonu (%2.6)
- `net_amount`: Üreticiye net ödeme

### FinancialSummary (Mali Özet)
**Alanlar:**
- `year`, `month`: Dönem
- `center_monthly_fees`: Merkez aylık ücretler toplamı
- `center_mold_revenue`: Fiziksel kalıp gelirleri
- `center_modeling_revenue`: Digital tarama gelirleri
- `producer_gross_revenue`: Üretici brüt gelirleri
- `moldpark_commission_revenue`: MoldPark komisyon gelirleri
- `total_credit_card_fees`: Toplam kredi kartı ücretleri
- `total_gross_revenue`: Toplam brüt gelir
- `total_net_revenue`: Toplam net gelir
- İstatistikler: merkez, üretici, kalıp, digital tarama sayıları

### Yeni Sistem Alanları (Invoice Modeli)

**Yetkilendirme Alanları:**
- `issued_by_center`: Faturayı kesen merkez
- `issued_by_producer`: Faturayı kesen üretici

**Yeni Fatura Türleri:**
- `center_admin_invoice`: İşitme merkezi admin faturası
- `producer_invoice`: Üretici hizmet bedeli faturası

**Komisyon Alanları:**
- `moldpark_service_fee_rate`: MoldPark hizmet bedeli oranı (%6.5)
- `credit_card_fee_rate`: Kredi kartı komisyonu oranı (%3)
- `moldpark_service_fee`: MoldPark hizmet bedeli tutarı
- `credit_card_fee`: Kredi kartı komisyonu tutarı

### Transaction Modeli Genişletmeleri

**Kaynak Takip Alanları:**
- `service_provider`: Hizmet veren kurum/kişi
- `service_type`: Hizmet kategorisi
- `amount_source`: Tutarın nereden geldiği
- `amount_destination`: Tutarın nereye gideceği
- `moldpark_fee_amount`: İşlemden MoldPark'ın aldığı ücret
- `credit_card_fee_amount`: İşlemden kesilen KK komisyonu

**İlişkili Nesneler:**
- `ear_mold`: İlgili kalıp
- `center`: İlgili merkez

**Yeni İşlem Türleri:**
- `center_invoice_payment`: Merkez fatura ödemesi
- `producer_invoice_payment`: Üretici fatura ödemesi
- `moldpark_collection`: MoldPark tahsilatı
- `moldpark_payment`: MoldPark ödemesi

## 🔄 Kullanım Akışı

### Yeni Fatura Kullanım Akışı

#### Fiziksel Kalıp İşlemi
1. İşitme merkezi kalıp gönderir (450 TL)
2. **Merkez Admin** fatura keser:
   - Müşteri ödemesi: 450 + 13.50(KK) + 29.25(MoldPark) = 492.75 TL
   - Sistem tahsilatı otomatik olarak kaydeder
3. **Üretici** hizmet bedeli faturası keser:
   - Üreticiye ödeme bilgilendirmesi: 450 - 13.50 - 29.25 = 407.25 TL
   - MoldPark ödemeyi beklemeye alır
4. Müşteri ödeme yaptığında:
   - MoldPark tahsilat transaction'ı oluşturulur
   - Üreticiye ödeme transaction'ı beklemeye alınır

#### Ödeme Takibi
1. MoldPark tüm tahsilatları takip eder
2. Üreticilere ödemeler manuel olarak gerçekleştirilir
3. Her ödeme transaction olarak kaydedilir
4. Detaylı raporlar ile takip edilir

### Eski Aylık Faturalandırma Sistemi
1. Her ayın 28'inde `generate_monthly_invoices` komutu çalıştırılır
2. Tüm aktif işitme merkezleri için faturalar oluşturulur:
   - 100 TL aylık ücret (her zaman)
   - + Fiziksel kalıp maliyetleri
   - + 3D kalıp modelleme maliyetleri
   - + %3 kredi kartı komisyonu
3. Tüm aktif üretici merkezler için faturalar oluşturulur:
   - Brüt gelir hesaplanır
   - - %6.5 MoldPark komisyonu
   - - %3 kredi kartı komisyonu
   - = Net ödeme (üreticiye ödenen tutar)
4. Aylık mali özet otomatik oluşturulur

### Fatura Takibi
1. Admin finansal dashboard'dan tüm faturaları görür
2. Vadesi geçmiş faturalar otomatik işaretlenir
3. Manuel olarak "ödendi" işaretlenebilir
4. Detaylı fatura görüntüleme ve yazdırma

## 🎯 Örnek Hesaplamalar

### Yeni Sistem - Fiziksel Kalıp İşlemi (450 TL)

#### Müşteri Görüşü (Merkez Admin Faturası)
```
Kalıp Ücreti:               450.00 TL
Kredi Kartı (%3):           13.50 TL
MoldPark Hizmet (%6.5):     29.25 TL
                           -----------
TOPLAM ÖDEME:              492.75 TL
```

#### Üretici Görüşü (Üretici Faturası)
```
Brüt Gelir:                 450.00 TL
MoldPark Hizmet Kesintisi:  -29.25 TL
Kredi Kartı Kesintisi:      -13.50 TL
                           -----------
NET ÖDEME (Üreticiye):      407.25 TL
```

#### MoldPark Kazancı (Bu işlemden)
```
MoldPark Hizmet Bedeli:     29.25 TL
Kredi Kartı Komisyonu:      13.50 TL
                           -----------
TOPLAM KAZANÇ:             42.75 TL
```

### Eski Sistem - İşitme Merkezi (5 fiziksel + 2 3D modelleme)
```
Aylık Sistem Kullanımı:      100.00 TL
Fiziksel Kalıp (5x450):     2,250.00 TL
3D Modelleme (2x50):        100.00 TL
                           -----------
Ara Toplam:                 2,450.00 TL
Kredi Kartı (%3):           73.50 TL
                           -----------
TOPLAM:                     2,523.50 TL
```

### Eski Sistem - Üretici Merkez (10,000 TL brüt gelir)
```
Brüt Gelir:                 10,000.00 TL
MoldPark Komisyon (%6.5):   -650.00 TL
Kredi Kartı (%3):           -300.00 TL
                           -----------
NET ÖDEME:                  9,050.00 TL
```

### Sistem Karşılaştırması
```
YENİ SİSTEM (Merkezileştirilmiş):
- Her kalıp için MoldPark kazancı: 42.75 TL
- Şeffaf tahsilat takibi
- Otomatik komisyon hesaplaması
- Detaylı kaynak takibi

ESKİ SİSTEM (Aylık Toplu):
- MoldPark toplam kazanç: Değişken
- Manuel takip gereksinimi
- Komisyon hesaplaması karmaşık
```

## 🚀 Kurulum ve Ayarlar

### Gerekli Adımlar
1. Migration'ları uygula:
```bash
python manage.py migrate
```

2. Fiyatlandırma sistemini kur:
```bash
python manage.py setup_new_pricing_system
```

3. Test et:
```bash
python manage.py generate_monthly_invoices --dry-run
```

### Cron Job Ayarı (Önerilen)
Aylık otomatik fatura oluşturma için:
```bash
# Her ayın 28. günü saat 00:00'da çalıştır
0 0 28 * * cd /path/to/moldpark && python manage.py generate_monthly_invoices
```

## 📱 Kullanıcı Arayüzü

### Admin Navbar
- Süper kullanıcılar için "Finansal Dashboard" butonu
- Yeşil renkte, chart-line ikonu ile

### Center Dashboard
- İşitme merkezi kullanıcıları için "Kullanım Detaylarım" butonu
- Mavi renkte, chart-line ikonu ile

### Producer Dashboard
- Üretici merkezi kullanıcıları için "Ödemelerim" butonu
- Turuncu renkte, money-bill-wave ikonu ile

### Producer Payments Page
- Mevcut ay ödeme özeti (tamamlanan siparişler, komisyonlar, net ödeme)
- Aylık ödeme geçmişi tablosu
- Detaylı komisyon hesaplaması
- Ödeme faturası listesi ve filtreleme
- Ödeme durumu takibi
- İlgili sipariş detayları

### Dashboard Özellikleri
- Modern, responsive tasarım
- Renkli istatistik kartları
- İnteraktif grafikler (Chart.js)
- Dönem filtreleme
- Yazdırma desteği

## 🔒 Güvenlik

- Tüm finansal sayfalar sadece süper kullanıcılara açık
- CSRF koruması aktif
- Fatura numaraları otomatik ve benzersiz
- Ödeme durumu değişiklikleri loglanabilir

## 📈 Gelecek Geliştirmeler

1. **Ödeme Entegrasyonu:** Online ödeme sistemleri (Stripe, PayTR)
2. **E-Fatura:** Resmi e-fatura entegrasyonu
3. **Mail Bildirimleri:** Fatura oluşturulduğunda otomatik mail
4. **Excel Export:** Finansal raporları Excel'e aktarma
5. **Grafik Genişletme:** Daha detaylı analiz grafikleri
6. **Tahsilat Takibi:** Ödeme planları ve hatırlatmalar

## 📞 Destek

Finansal sistem ile ilgili sorularınız için:
- **Email:** destek@moldpark.com
- **Dokümantasyon:** Bu dosya

---

**Not:** Sistem test edildi ve production'a hazır. Gerçek kullanıma geçmeden önce cron job ayarlarını yapın ve test faturaları oluşturun.

