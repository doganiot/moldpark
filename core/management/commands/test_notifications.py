from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.utils import send_notification, send_success_notification, send_warning_notification, send_error_notification


class Command(BaseCommand):
    help = 'Test bildirimleri oluşturur'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, help='Kullanıcı adı (yoksa tüm kullanıcılara gönderir)')
        parser.add_argument('--count', type=int, default=5, help='Gönderilecek bildirim sayısı')

    def handle(self, *args, **options):
        username = options.get('user')
        count = options.get('count', 5)
        
        if username:
            try:
                users = [User.objects.get(username=username)]
                self.stdout.write(f"Sadece {username} kullanıcısına bildirim gönderiliyor...")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Kullanıcı bulunamadı: {username}"))
                return
        else:
            users = User.objects.filter(is_active=True)[:10]  # İlk 10 aktif kullanıcı
            self.stdout.write(f"{users.count()} kullanıcıya bildirim gönderiliyor...")
        
        test_notifications = [
            {
                'func': send_success_notification,
                'title': 'Hoş Geldiniz!',
                'message': 'MoldPark basit bildirim sistemi başarıyla kuruldu. Bu bir test bildirimidir.',
                'related_url': '/notifications/'
            },
            {
                'func': send_notification,
                'title': 'Yeni Özellik',
                'message': 'Artık bildirimlerinizi kolayca takip edebilirsiniz.',
                'notification_type': 'info'
            },
            {
                'func': send_warning_notification,
                'title': 'Uyarı',
                'message': 'Bu bir test uyarı bildirimidir.'
            },
            {
                'func': send_error_notification,
                'title': 'Test Hatası',
                'message': 'Bu bir test hata bildirimidir. Gerçek bir hata değildir.'
            },
            {
                'func': send_notification,
                'title': 'Sipariş Bildirimi',
                'message': 'Test sipariş bildirimi - bu gerçek bir sipariş değildir.',
                'notification_type': 'order'
            }
        ]
        
        for user in users:
            self.stdout.write(f"  → {user.username} için bildirimler oluşturuluyor...")
            
            for i in range(count):
                notification_data = test_notifications[i % len(test_notifications)]
                func = notification_data.pop('func')
                
                try:
                    notification = func(user, **notification_data)
                    if notification:
                        self.stdout.write(f"    ✓ {notification.title}")
                    else:
                        self.stdout.write(self.style.ERROR(f"    ✗ Bildirim oluşturulamadı"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ✗ Hata: {e}"))
                
                # func'ı geri ekle (döngü için)
                notification_data['func'] = func
        
        self.stdout.write(self.style.SUCCESS(f"Test bildirimleri başarıyla oluşturuldu!"))
        self.stdout.write("Bildirimleri görmek için: /notifications/ sayfasını ziyaret edin") 