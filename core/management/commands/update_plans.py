from django.core.management.base import BaseCommand
from core.models import PricingPlan

class Command(BaseCommand):
    help = 'Fiyatlandırma planlarını günceller'

    def handle(self, *args, **options):
        self.stdout.write('📝 Planlar güncelleniyor...\n')
        
        # PREMIUM PLAN'I GÜNCELLE
        try:
            premium_plan = PricingPlan.objects.get(plan_type='premium')
            old_limit = premium_plan.monthly_model_limit
            premium_plan.monthly_model_limit = 350
            
            # Features'ı da güncelle
            premium_plan.features = [
                '350 kalıp/ay',
                'Tüm üretici ağı + Premium ağ',
                '7/24 destek',
                'Özel hesap yöneticisi',
                'Gelişmiş analitik',
                'API erişimi',
                'Özel entegrasyonlar',
                'White-label çözümler'
            ]
            premium_plan.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Premium Plan güncellendi: {old_limit} → {premium_plan.monthly_model_limit} kalıp/ay')
            )
        except PricingPlan.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('❌ Premium Plan bulunamadı!')
            )
        
        # KURUMSAL PLAN'I GÜNCELLE
        try:
            enterprise_plan = PricingPlan.objects.get(plan_type='enterprise')
            
            # Kurumsal plan için özel açıklama
            enterprise_plan.description = 'Zincir işitme merkezleri ve büyük organizasyonlar için. Özel fiyatlandırma için iletişime geçin.'
            
            # Features'ı güncelle
            enterprise_plan.features = [
                'Sınırsız kalıp',
                'Özel üretici ağı',
                'Dedicated hesap yöneticisi',
                'Özel SLA',
                'Kurumsal analitik',
                'Multi-location yönetim',
                'Özel geliştirmeler',
                'On-premise deployment seçeneği',
                'Özel fiyatlandırma'
            ]
            
            # Özel monthly_model_limit işareti (-1 = iletişim gerekli)
            enterprise_plan.monthly_model_limit = -1
            enterprise_plan.save()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Kurumsal Plan güncellendi: İletişim merkeziyle görüşme gerekli')
            )
        except PricingPlan.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('❌ Kurumsal Plan bulunamadı!')
            )
        
        # GÜNCEL PLANLAR LİSTESİ
        all_plans = PricingPlan.objects.filter(is_active=True).order_by('price_usd')
        self.stdout.write(
            self.style.SUCCESS(f'\n📊 Güncel Planlar:')
        )
        
        for plan in all_plans:
            if plan.plan_type == 'trial':
                continue
            
            if plan.plan_type == 'enterprise':
                limit_text = "İletişim Gerekli"
            else:
                limit_text = f"{plan.monthly_model_limit} kalıp/ay"
            
            self.stdout.write(f'   • {plan.name} - ${plan.price_usd}/ay - {limit_text}')
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Plan güncellemeleri tamamlandı!')
        ) 