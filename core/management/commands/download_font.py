"""
DejaVuSans fontunu indir ve static/fonts klasörüne kaydet
Türkçe karakter desteği için gerekli
"""
import os
import urllib.request
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'DejaVuSans fontunu indir ve static/fonts klasörüne kaydet'

    def handle(self, *args, **options):
        # Font klasörünü oluştur
        fonts_dir = os.path.join(settings.BASE_DIR, 'static', 'fonts')
        os.makedirs(fonts_dir, exist_ok=True)
        
        # Font URL'leri (alternatif kaynaklar)
        font_urls = {
            'DejaVuSans.ttf': [
                'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf',
                'https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf',
            ],
            'DejaVuSans-Bold.ttf': [
                'https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf',
                'https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans-Bold.ttf',
            ],
        }
        
        for font_name, font_urls_list in font_urls.items():
            font_path = os.path.join(fonts_dir, font_name)
            
            if os.path.exists(font_path):
                self.stdout.write(self.style.WARNING(f'{font_name} zaten mevcut, atlanıyor...'))
                continue
            
            downloaded = False
            for font_url in font_urls_list:
                try:
                    self.stdout.write(f'{font_name} indiriliyor ({font_url})...')
                    urllib.request.urlretrieve(font_url, font_path)
                    self.stdout.write(self.style.SUCCESS(f'{font_name} başarıyla indirildi: {font_path}'))
                    downloaded = True
                    break
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'URL başarısız: {str(e)}'))
                    continue
            
            if not downloaded:
                self.stdout.write(self.style.ERROR(f'{font_name} hiçbir kaynaktan indirilemedi. Windows sistem fontlarını kullanın.'))
        
        self.stdout.write(self.style.SUCCESS('\nFont indirme işlemi tamamlandı!'))
