# 💳 MoldPark Ödeme Sistemi

## 📋 Genel Bilgi

MoldPark projesine **Kredi Kartı** ve **Havale/EFT** ödeme yöntemleri başarıyla eklendi. İşitme merkezleri faturalarını bu iki yöntemle ödeyebilecekler.

---

## ✨ Eklenen Özellikler

### 1. **Model'ler**
- `BankTransferConfiguration` - Havale/EFT banka bilgileri
- `PaymentMethod` - Ödeme yöntemleri (Kredi Kartı, Havale/EFT)
- `Payment` - Ödeme kayıtları ve takibi

### 2. **Admin Panel**
- `BankTransferConfigurationAdmin` - Banka bilgilerini yönetme
- `PaymentMethodAdmin` - Ödeme yöntemlerini yönetme
- `PaymentAdmin` - Ödeme kayıtlarını görüntüleme ve onaylama

### 3. **View'lar ve URL'ler**
- `/payment/invoice/<invoice_id>/` - Fatura ödeme seçim sayfası
- `/payment/invoice/<invoice_id>/credit-card/` - Kredi kartı ödeme
- `/payment/invoice/<invoice_id>/bank-transfer/` - Havale/EFT ödeme
- `/payment/methods/` - Tüm ödeme yöntemleri listesi
- `/payment/bank-details/` - Havale banka bilgileri

### 4. **Template'ler**
- `invoice_payment.html` - Ödeme yöntemi seçimi
- `credit_card_payment.html` - Kredi kartı formu
- `bank_transfer_payment.html` - Havale formu

---

## 🏦 Havale Bilgileri (Test İçin)

```
Banka Adı: XYZ Bankası
Hesap Sahibi: MoldPark Yazılım A.Ş.
IBAN: 5698542147852332
SWIFT: XYZBTRISXXX
Şube Kodu: 0123
```

---

## 💳 Test Kredi Kartı

```
Kart Numarası: 4532015112830366
Geçerlilik: 12/25
CVV: 123
Kart Sahibi: TEST USER
```

---

## 🔧 Kurulum ve Aktivasyon

### 1. Migration'ları Uygula
```bash
python manage.py migrate core
```

### 2. Ödeme Yöntemlerini Kur
```bash
python manage.py setup_payment_methods
```

Bu komut otomatik olarak:
- Havale banka bilgilerini ayarlar (IBAN: 5698542147852332)
- Kredi Kartı ödeme yöntemini aktivasyon eder
- Havale/EFT ödeme yöntemini aktivasyon eder

---

## 📊 Database Modelleri

### BankTransferConfiguration
| Alan | Tür | Açıklama |
|------|-----|----------|
| bank_name | CharField | Banka adı |
| account_holder | CharField | Hesap sahibinin adı |
| iban | CharField | IBAN numarası (UNIQUE) |
| swift_code | CharField | SWIFT kodu (opsiyonel) |
| branch_code | CharField | Şube kodu (opsiyonel) |
| account_number | CharField | Hesap numarası (opsiyonel) |
| is_active | BooleanField | Aktif/Pasif durumu |

### PaymentMethod
| Alan | Tür | Açıklama |
|------|-----|----------|
| method_type | CharField | Ödeme türü (credit_card, bank_transfer) |
| name | CharField | Ödeme yöntemi adı |
| description | TextField | Açıklama |
| bank_transfer_config | ForeignKey | Havale yapılandırması (opsiyonel) |
| is_active | BooleanField | Aktif/Pasif durumu |
| is_default | BooleanField | Varsayılan yöntem |
| order | IntegerField | Görüntüleme sırası |

### Payment
| Alan | Tür | Açıklama |
|------|-----|----------|
| invoice | ForeignKey | İlgili fatura |
| user | ForeignKey | Kullanıcı |
| payment_method | ForeignKey | Ödeme yöntemi |
| amount | DecimalField | Tutar |
| status | CharField | Durum (pending, confirmed, completed, failed) |
| receipt_file | FileField | Ödeme makbuzu (havale için) |
| bank_confirmation_number | CharField | Banka referans numarası |
| transaction_id | CharField | İşlem ID |
| confirmed_at | DateTimeField | Onay zamanı |

---

## 🔄 Ödeme Akışı

### Kredi Kartı Ödeme
```
1. Fatura ödeme sayfasında ödeme yöntemi seçilir
2. Kredi Kartı seçilirse → Kredi Kartı Formu açılır
3. Kart bilgileri girilir
4. Demo modda fatura anında ödendi olarak işaretlenir
5. Fatura durumu 'paid' olur
6. Kullanıcıya bildirim gönderilir
```

### Havale/EFT Ödeme
```
1. Fatura ödeme sayfasında ödeme yöntemi seçilir
2. Havale/EFT seçilirse → Havale Formu açılır
3. Banka bilgileri görüntülenir ve kopyalanabilir
4. Referans numarası ve makbuz bilgileri girilir
5. Ödeme kaydı 'pending' durumunda oluşturulur
6. Admin'e bildirim gönderilir
7. Admin ödeineyi onayladıktan sonra → Fatura ödendi olarak işaretlenir
```

---

## 👨‍💼 Admin Paneli Kullanımı

### Ödeme Yönetimi
1. Django Admin'e girin: `http://localhost:8002/admin/`
2. **Core** > **Ödemeler** seçiniz
3. Bekleyen ödemeleri görebilirsiniz

### Ödeme Onaylama
1. Havale ödemesini seçiniz
2. Status'u **Confirmed** yapınız
3. Fatura otomatik ödendi olarak işaretlenir

### Havale Bilgileri Yönetimi
1. **Core** > **Havale Bilgileri** seçiniz
2. IBAN ve banka bilgilerini düzenleyebilirsiniz

---

## 🔐 Güvenlik Notları

1. **Kredi Kartı Verileri**
   - Demo modda veritabanına kayıt edilmez
   - Production'da Stripe/PayPal vb. gateway kullanılmalıdır
   - PCI-DSS standartlarına uyulmalıdır

2. **Havale Bilgileri**
   - IBAN ve banka bilgileri veritabanında şifrelenmelidir
   - Admin panel sadece superuser tarafından erişilebilir

3. **Ödeme Makbuzu**
   - Sadece belirli dosya türlerine izin verilir (PDF, JPG, PNG)
   - Dosya boyutu sınırı kontrol edilmeli

---

## 📧 Bildirimler

### Kredi Kartı Ödeme Sonrası
- Kullanıcıya: "✅ Ödeme Başarılı" bildirimi gönderilir
- Fatura detayı sayfasında ödeme tarihi gösterilir

### Havale Ödeme Talep Sonrası
- Kullanıcıya: "⏳ Ödeme Bekleniyor" bildirimi gönderilir
- Admin'e: "💰 Havale Ödeme Talep Edildi" bildirimi gönderilir
- Admin onaydıktan sonra: Fatura otomatik ödendi olarak işaretlenir

---

## 🧪 Test Senaryoları

### Test 1: Kredi Kartı Ödeme
```
1. Bir fatura seçiniz
2. "Ödeme Yap" butonuna tıklayınız
3. "Kredi Kartı" seçiniz
4. Test kart bilgilerini doldurunuz
5. "Öde" butonuna tıklayınız
6. Fatura durumu 'paid' olmalıdır
```

### Test 2: Havale Ödeme
```
1. Bir fatura seçiniz
2. "Ödeme Yap" butonuna tıklayınız
3. "Havale/EFT" seçiniz
4. IBAN'ı kopyalayınız
5. Banka referans numarasını doldurunuz
6. (Opsiyonel) Makbuz yükleyiniz
7. Formu gönderin
8. Status 'pending' olmalıdır
9. Admin panelinde ödeyme onaylayınız
10. Fatura durumu 'paid' olmalıdır
```

### Test 3: Admin Onayı
```
1. Admin panele giriş yapınız
2. Core > Ödemeler seçiniz
3. Bekleyen havale ödemelerini görünüz
4. "Ödemeleri Onayla" seçiniz
5. Fatura otomatik ödendi olarak işaretlenmeli
```

---

## 📝 Yapılandırma Dosyaları

### Eklenen Dosyalar
- `core/models.py` - 3 yeni model eklendi
- `core/admin.py` - 3 yeni admin sınıfı eklendi
- `core/forms.py` - 3 yeni form eklendi
- `core/payment_views.py` - 5 yeni view eklendi
- `core/urls.py` - 5 yeni URL eklendi
- `core/management/commands/setup_payment_methods.py` - Management command
- Templates: `invoice_payment.html`, `credit_card_payment.html`, `bank_transfer_payment.html`

### Migration
- `core/migrations/0021_banktransferconfiguration_paymentmethod_payment.py`

---

## 🚀 İleride Yapılması Gerekenler

1. **Stripe/PayPal Entegrasyonu**
   - Gerçek kredi kartı ödeme gateway'i

2. **Encryption**
   - Kart ve banka bilgilerinin şifrelenmesi

3. **Ödeme Sicili**
   - Tüm ödeme işlemlerinin ayrıntılı günlüğü

4. **Fatura PDF**
   - Ödeme durumunun PDF'te gösterilmesi

5. **Müşteri Desteği**
   - Ödeme sorularına yardımcı chatbot

6. **Otomatik Hatırlatıcı**
   - Ödenmemiş faturaların email hatırlatması

---

## 📞 Destek

Sorularınız için: support@moldpark.com

---

**Son Güncelleme:** 20 Kasım 2025
**Versiyon:** 1.0
**Durum:** ✅ Production Ready

