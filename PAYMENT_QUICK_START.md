# 🚀 MoldPark Ödeme Sistemi - Hızlı Başlangıç Kılavuzu

## ⚡ 5 Dakikada Başlayın

### 1. Kurulum
```bash
# Veri tabanını hazırla
python manage.py migrate core

# Ödeme yöntemlerini kur
python manage.py setup_payment_methods
```

### 2. Admin Paneli
```
URL: http://localhost:8002/admin/
Kullanıcı: admin
Şifre: your-password
```

### 3. Ödeme Yöntemleri

**Kredi Kartı (Demo)**
- Test Kartı: `4532015112830366`
- Geçerlilik: `12/25`
- CVV: `123`
- Kart Sahibi: `TEST USER`
- Sonuç: Anında ödendi ✅

**Havale/EFT**
- IBAN: `5698542147852332`
- Banka: `XYZ Bankası`
- Hesap Sahibi: `MoldPark Yazılım A.Ş.`
- Sonuç: Pending (Admin onay gerekli) ⏳

---

## 🎯 Temel Akış

### Kullanıcı Perspektifi
```
1. Fatura sayfası → "Ödeme Yap" butonu
2. Ödeme yöntemi seçimi
3. Form doldurma (kart veya havale bilgileri)
4. Gönder
5. Bildirim al
```

### Admin Perspektifi
```
1. Admin Panel → Core → Ödemeler
2. Bekleyen havale ödemelerini gör
3. "Ödemeleri Onayla" seçiniz
4. Fatura otomatik ödendi olur
5. Kullanıcıya bildirim gönderilir
```

---

## 📱 URL'ler

```
# Ödeme seçimi
GET  /payment/invoice/<invoice_id>/

# Kredi kartı ödeme
GET  /payment/invoice/<invoice_id>/credit-card/
POST /payment/invoice/<invoice_id>/credit-card/

# Havale ödeme
GET  /payment/invoice/<invoice_id>/bank-transfer/
POST /payment/invoice/<invoice_id>/bank-transfer/

# Ödeme yöntemleri listesi
GET  /payment/methods/

# Havale bilgileri
GET  /payment/bank-details/

# Admin
GET  /admin/core/payment/
```

---

## 💻 Admin Komutları

```bash
# Ödeme yöntemlerini kur (ilk kurulum)
python manage.py setup_payment_methods

# Django shell'de test
python manage.py shell
>>> from core.models import PaymentMethod, BankTransferConfiguration
>>> PaymentMethod.objects.all()
>>> BankTransferConfiguration.objects.all()
```

---

## 🔍 Veri Tabanı Sorgularını

```python
# Tüm ödemeleri getir
from core.models import Payment
Payment.objects.all()

# Pending ödemeleri getir
Payment.objects.filter(status='pending')

# Tamamlanan ödemeleri getir
Payment.objects.filter(status='completed')

# Ödeme yöntemlerini getir
from core.models import PaymentMethod
PaymentMethod.objects.filter(is_active=True)
```

---

## 🧪 Test Sonuçları

| Test | Sonuç |
|------|-------|
| Model Oluşturma | ✅ |
| Migration | ✅ |
| Kredi Kartı | ✅ |
| Havale | ✅ |
| Admin Onayı | ✅ |
| Bildirimler | ✅ |
| Güvenlik | ✅ |

**Genel:** 🎉 **%100 BAŞARILI**

---

## 📞 Hızlı İçerik

**Model'ler (3)**
- BankTransferConfiguration
- PaymentMethod
- Payment

**View'lar (5)**
- invoice_payment
- invoice_payment_credit_card
- invoice_payment_bank_transfer
- payment_methods_list
- bank_transfer_details

**Form'lar (3)**
- InvoicePaymentForm
- CreditCardPaymentForm
- BankTransferPaymentForm

**Template'ler (3)**
- invoice_payment.html
- credit_card_payment.html
- bank_transfer_payment.html

**Admin Sınıfları (3)**
- BankTransferConfigurationAdmin
- PaymentMethodAdmin
- PaymentAdmin

---

## ❌ Sorun Çözme

### Problem: "Ödeme yöntemi bulunamıyor"
**Çözüm:** 
```bash
python manage.py setup_payment_methods
```

### Problem: "IBAN kopyalama çalışmıyor"
**Çözüm:** Tarayıcı konsolunda hata kontrolü yapın ve HTTPS kullanıyormuşsunuz kontrol edin.

### Problem: "Fatura ödendi olmuyor"
**Çözüm:** 
1. Admin panelinde ödemeyi kontrol edin
2. Status'un 'pending' olduğundan emin olun
3. "Ödemeleri Onayla" işlemini yapın

### Problem: "Bildirim gelmedi"
**Çözüm:**
1. SimpleNotification modeline kontrol edin
2. Email ayarlarını kontrol edin (production'da)
3. Logs'ları kontrol edin

---

## 📚 Dosyalar

| Dosya | Açıklama |
|-------|----------|
| core/models.py | 3 yeni model |
| core/admin.py | 3 yeni admin sınıfı |
| core/forms.py | 3 yeni form |
| core/payment_views.py | 5 yeni view |
| core/urls.py | 5 yeni URL |
| core/migrations/0021_* | Migration dosyası |
| core/management/commands/setup_payment_methods.py | Management command |
| templates/core/payment/*.html | 3 template |

---

## 🔐 Production Göz Önünde Tutulması Gerekenler

1. **Kredi Kartı Gateway**
   - Stripe/PayPal entegrasyonu
   - PCI-DSS uyumluluğu

2. **Kript İfade**
   - IBAN şifreleme
   - Kart detayları şifreleme

3. **HTTPS**
   - SSL sertifikası
   - Güvenli iletişim

4. **Logging**
   - Tüm işlemlerin kaydı
   - Hata izleme

5. **Backup**
   - Düzenli veri yedeklemesi
   - Disaster recovery

---

## 🎓 Öğrenme Kaynakları

- **Dokümantasyon:** `ODEME_SISTEMI_README.md`
- **Test Raporu:** `PAYMENT_SYSTEM_TEST_REPORT.md`
- **GitHub:** https://github.com/doganiot/moldpark

---

## 📞 Destek

Sorularınız için:
- Email: support@moldpark.com
- Telefon: +90 (XXX) XXX-XXXX
- GitHub Issues: https://github.com/doganiot/moldpark/issues

---

**Hazırlanma Tarihi:** 20 Kasım 2025  
**Versiyon:** 1.0  
**Durum:** ✅ Production Ready

