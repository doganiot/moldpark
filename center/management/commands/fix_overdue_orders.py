from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from producer.models import ProducerOrder


class Command(BaseCommand):
    help = 'Gecikmiş siparişleri kontrol eder ve düzeltir'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Gecikmiş siparişleri otomatik düzelt',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece analiz yap, değişiklik yapma',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Gecikmiş Siparişler Analizi Başlatılıyor...'))
        
        current_time = timezone.now()
        
        # 1. Tüm siparişleri kontrol et
        all_orders = ProducerOrder.objects.all()
        self.stdout.write(f"📊 Toplam sipariş sayısı: {all_orders.count()}")
        
        # 2. estimated_delivery NULL olanları bul
        null_delivery_orders = ProducerOrder.objects.filter(estimated_delivery__isnull=True)
        self.stdout.write(f"⚠️  Tahmini teslimat tarihi NULL olan siparişler: {null_delivery_orders.count()}")
        
        # 3. Gerçekten gecikmiş olanları bul
        truly_overdue = ProducerOrder.objects.filter(
            estimated_delivery__isnull=False,
            estimated_delivery__lt=current_time,
            status__in=['received', 'designing', 'production', 'quality_check']
        )
        
        self.stdout.write(f"⏰ Gerçekten gecikmiş siparişler: {truly_overdue.count()}")
        
        if truly_overdue.exists():
            self.stdout.write("📋 Gecikmiş Sipariş Detayları:")
            for order in truly_overdue:
                delay_days = (current_time.date() - order.estimated_delivery).days
                self.stdout.write(
                    f"  ID: {order.id} | Status: {order.status} | "
                    f"Hasta: {order.ear_mold.patient_name} | "
                    f"Gecikme: {delay_days} gün | "
                    f"Tahmini: {order.estimated_delivery} | "
                    f"Üretici: {order.producer.company_name if order.producer else 'N/A'}"
                )
        
        # 4. Teslim edilmiş ancak status'u güncellenmemiş olanları bul
        completed_but_wrong_status = ProducerOrder.objects.filter(
            status__in=['received', 'designing', 'production', 'quality_check'],
            ear_mold__status='delivered'  # Kalıp teslim edilmiş ama sipariş status'u güncellenmemiş
        )
        
        self.stdout.write(f"🔄 Teslim edilmiş ama status güncel olmayan siparişler: {completed_but_wrong_status.count()}")
        
        # 5. Düzeltme işlemleri
        if options['fix'] and not options['dry_run']:
            self.stdout.write(self.style.WARNING('🔧 Otomatik düzeltme başlatılıyor...'))
            
            # NULL delivery tarihlerini güncelle
            fixed_count = 0
            for order in null_delivery_orders:
                # Oluşturulma tarihinden 7 gün sonra tahmin et
                estimated = order.created_at + timedelta(days=7)
                order.estimated_delivery = estimated.date()
                order.save()
                fixed_count += 1
            
            self.stdout.write(f"✅ {fixed_count} adet NULL delivery tarihi düzeltildi")
            
            # Teslim edilmiş siparişlerin status'unu güncelle
            updated_count = completed_but_wrong_status.update(status='delivered')
            self.stdout.write(f"✅ {updated_count} adet sipariş status'u 'delivered' olarak güncellendi")
            
        elif options['dry_run']:
            self.stdout.write(self.style.WARNING('🧪 DRY RUN - Hiçbir değişiklik yapılmadı'))
            
        # 6. Güncel durum raporu
        self.stdout.write("\n" + "="*50)
        self.stdout.write("📈 GÜNCEL DURUM RAPORU:")
        
        status_counts = {}
        for order in all_orders:
            status = order.status
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts[status] = 1
        
        for status, count in status_counts.items():
            self.stdout.write(f"  {status}: {count} adet")
        
        self.stdout.write("="*50)
        self.stdout.write(self.style.SUCCESS('✅ Analiz tamamlandı!'))
        
        if not options['fix'] and not options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    "\n💡 Sorunları düzeltmek için: python manage.py fix_overdue_orders --fix"
                )
            ) 