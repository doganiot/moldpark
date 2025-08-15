from django.core.management.base import BaseCommand
from core.models import PricingPlan
from decimal import Decimal

class Command(BaseCommand):
    help = '6 aylık ücretsiz kullanım planı oluşturur'

    def handle(self, *args, **options):
        # 6 Aylık Ücretsiz Plan - İşitme Merkezleri için
        free_plan_center, created = PricingPlan.objects.get_or_create(
            name='6 Aylık Ücretsiz Kampanya',
            plan_type='trial',
            defaults={
                'description': '🎉 Yeni üyelere özel 6 ay boyunca tamamen ücretsiz kullanım!',
                'price_usd': Decimal('0.00'),
                'price_try': Decimal('0.00'),
                'monthly_model_limit': 100,  # Aylık 100 kalıp
                'is_monthly': True,
                'features': [
                    '✅ 6 Ay Boyunca Tamamen Ücretsiz',
                    '✅ Aylık 100 Kalıp Gönderme Hakkı',
                    '✅ Tüm Üretici Ağlarına Erişim',
                    '✅ 3D Model Desteği',
                    '✅ Revizyon Talep Hakkı',
                    '✅ 7/24 Destek',
                    '✅ Kredi Kartı Gerektirmez',
                    '✅ Otomatik Yenileme Yok'
                ],
                'is_active': True,
                'order': 0,  # En üstte göster
                'is_featured': True,
                'badge_text': '🔥 YENİ',
                'trial_days': 180  # 6 ay = 180 gün
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✅ 6 Aylık Ücretsiz Kampanya planı oluşturuldu!'))
        else:
            # Mevcut planı güncelle
            free_plan_center.description = '🎉 Yeni üyelere özel 6 ay boyunca tamamen ücretsiz kullanım!'
            free_plan_center.monthly_model_limit = 100
            free_plan_center.trial_days = 180
            free_plan_center.features = [
                '✅ 6 Ay Boyunca Tamamen Ücretsiz',
                '✅ Aylık 100 Kalıp Gönderme Hakkı',
                '✅ Tüm Üretici Ağlarına Erişim',
                '✅ 3D Model Desteği',
                '✅ Revizyon Talep Hakkı',
                '✅ 7/24 Destek',
                '✅ Kredi Kartı Gerektirmez',
                '✅ Otomatik Yenileme Yok'
            ]
            free_plan_center.badge_text = '🔥 YENİ'
            free_plan_center.is_featured = True
            free_plan_center.save()
            self.stdout.write(self.style.WARNING('⚠️ Mevcut 6 Aylık Ücretsiz Kampanya planı güncellendi!'))
        
        # 6 Aylık Ücretsiz Plan - Üretici Merkezler için
        free_plan_producer, created = PricingPlan.objects.get_or_create(
            name='Üretici - 6 Aylık Ücretsiz',
            plan_type='producer_trial',
            defaults={
                'description': '🏭 Üretici merkezlere özel 6 ay ücretsiz kullanım!',
                'price_usd': Decimal('0.00'),
                'price_try': Decimal('0.00'),
                'monthly_model_limit': 200,  # Aylık 200 sipariş alabilir
                'is_monthly': True,
                'features': [
                    '✅ 6 Ay Boyunca Tamamen Ücretsiz',
                    '✅ Aylık 200 Sipariş Alma Hakkı',
                    '✅ İşitme Merkezlerine Erişim',
                    '✅ Otomatik Sipariş Eşleştirme',
                    '✅ 3D Model İndirme',
                    '✅ Revizyon Yönetimi',
                    '✅ Detaylı Raporlama',
                    '✅ 7/24 Teknik Destek'
                ],
                'is_active': True,
                'order': 1,
                'is_featured': True,
                'badge_text': '🏭 ÜRETİCİ',
                'trial_days': 180  # 6 ay
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Üretici - 6 Aylık Ücretsiz planı oluşturuldu!'))
        else:
            # Mevcut planı güncelle
            free_plan_producer.description = '🏭 Üretici merkezlere özel 6 ay ücretsiz kullanım!'
            free_plan_producer.monthly_model_limit = 200
            free_plan_producer.trial_days = 180
            free_plan_producer.features = [
                '✅ 6 Ay Boyunca Tamamen Ücretsiz',
                '✅ Aylık 200 Sipariş Alma Hakkı',
                '✅ İşitme Merkezlerine Erişim',
                '✅ Otomatik Sipariş Eşleştirme',
                '✅ 3D Model İndirme',
                '✅ Revizyon Yönetimi',
                '✅ Detaylı Raporlama',
                '✅ 7/24 Teknik Destek'
            ]
            free_plan_producer.badge_text = '🏭 ÜRETİCİ'
            free_plan_producer.is_featured = True
            free_plan_producer.save()
            self.stdout.write(self.style.WARNING('⚠️ Mevcut Üretici 6 Aylık Ücretsiz planı güncellendi!'))
        
        self.stdout.write(self.style.SUCCESS('\n📊 Plan Detayları:'))
        self.stdout.write(f'   - İşitme Merkezleri: 6 ay ücretsiz, aylık 100 kalıp')
        self.stdout.write(f'   - Üretici Merkezler: 6 ay ücretsiz, aylık 200 sipariş')
        self.stdout.write(self.style.SUCCESS('\n✅ 6 Aylık Ücretsiz Kampanya başarıyla oluşturuldu!'))
