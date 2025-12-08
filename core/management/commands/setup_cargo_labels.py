"""
Kargo etiket şablonları kurulum komutu
Varsayılan etiket şablonlarını oluşturur
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.cargo_label_service import CargoLabelManager


class Command(BaseCommand):
    help = 'Kargo etiket şablonlarını oluşturur'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Mevcut etiket şablonlarını sıfırla ve yeniden oluştur',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🏷️ Kargo Etiket Sistemi Kurulumu Başlatılıyor...\n')
        )

        if options['reset']:
            from core.models import CargoLabel
            self.stdout.write('🔄 Mevcut etiket şablonları temizleniyor...')
            CargoLabel.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Temizlik tamamlandı.\n'))

        # Varsayılan etiket şablonlarını oluştur
        CargoLabelManager.create_default_templates()

        # Test mesajı
        self.stdout.write(
            self.style.SUCCESS(
                '\n🎉 Kargo etiket sistemi kurulumu başarıyla tamamlandı!\n'
                '📋 Oluşturulan şablonlar:\n'
                '   • Standart PDF Etiket (10x15 cm)\n'
                '   • Termal Etiket Küçük (4x6 cm)\n'
                '   • Termal Etiket Büyük (8x12 cm)\n\n'
                '💡 Admin panelinden şablonları özelleştirebilirsiniz.'
            )
        )

