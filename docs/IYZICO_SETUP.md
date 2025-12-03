# İyzico Ödeme Gateway Kurulumu

Bu dokümantasyon, MoldPark sistemine İyzico ödeme gateway entegrasyonunun nasıl kurulacağını açıklar.

## 1. İyzico Hesabı Oluşturma

1. [İyzico](https://www.iyzico.com/) web sitesine gidin
2. "Kayıt Ol" butonuna tıklayın
3. Hesap bilgilerinizi doldurun ve hesabınızı oluşturun
4. E-posta doğrulamasını tamamlayın

## 2. Test API Anahtarlarını Alma

1. İyzico panelinize giriş yapın
2. **Ayarlar > API Bilgileri** bölümüne gidin
3. **Test API Bilgileri** sekmesine tıklayın
4. Aşağıdaki bilgileri kopyalayın:
   - **API Key** (Örnek: `sandbox-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
   - **Secret Key** (Örnek: `sandbox-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

## 3. Ortam Değişkenlerini Ayarlama

`.env` dosyanıza aşağıdaki satırları ekleyin:

```env
# İyzico Test API Bilgileri
IYZICO_API_KEY=sandbox-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
IYZICO_SECRET_KEY=sandbox-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
IYZICO_BASE_URL=https://sandbox-api.iyzipay.com
IYZICO_TEST_MODE=True
```

## 4. Paket Kurulumu

```bash
pip install -r requirements.txt
```

Bu komut `iyzipay==1.0.50` paketini yükleyecektir.

## 5. Migration Çalıştırma

```bash
python manage.py migrate
```

Bu komut Payment model'ine İyzico alanlarını ekleyecektir.

## 6. Test Kartları

İyzico test ortamında aşağıdaki kartları kullanabilirsiniz:

### Başarılı Ödeme
- **Kart No:** `5528 7900 0000 0000`
- **Son Kullanma:** `12/30`
- **CVV:** `123`
- **Kart Sahibi:** Herhangi bir isim

### Başarısız Ödeme
- **Kart No:** `5528 7900 0000 0001`
- **Son Kullanma:** `12/30`
- **CVV:** `123`
- **Kart Sahibi:** Herhangi bir isim

## 7. Production'a Geçiş

Production ortamına geçerken:

1. İyzico panelinden **Canlı API Bilgileri** alın
2. `.env` dosyasını güncelleyin:
   ```env
   IYZICO_API_KEY=live-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   IYZICO_SECRET_KEY=live-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   IYZICO_BASE_URL=https://api.iyzipay.com
   IYZICO_TEST_MODE=False
   ```
3. Sisteminizi yeniden başlatın

## 8. Özellikler

- ✅ Test ve Production modları
- ✅ Güvenli ödeme işleme
- ✅ Ödeme doğrulama
- ✅ Otomatik fatura güncelleme
- ✅ Bildirim sistemi entegrasyonu
- ✅ Detaylı ödeme kayıtları

## 9. Sorun Giderme

### Ödeme formu oluşturulamıyor
- API anahtarlarınızın doğru olduğundan emin olun
- `.env` dosyasının doğru yüklendiğini kontrol edin
- İyzico panelinden API anahtarlarınızın aktif olduğunu doğrulayın

### Ödeme doğrulanamıyor
- Callback URL'in doğru yapılandırıldığından emin olun
- Token'ın geçerli olduğunu kontrol edin
- İyzico loglarını kontrol edin

## 10. Destek

İyzico desteği için:
- [İyzico Dokümantasyonu](https://dev.iyzipay.com/tr)
- [İyzico Destek](https://www.iyzipay.com/iletisim)

