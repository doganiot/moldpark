from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.signals import notify

class ContactMessage(models.Model):
    name = models.CharField('Ad Soyad', max_length=100)
    email = models.EmailField('E-posta')
    subject = models.CharField('Konu', max_length=200)
    message = models.TextField('Mesaj')
    created_at = models.DateTimeField('Gönderilme Tarihi', auto_now_add=True)

    class Meta:
        verbose_name = 'İletişim Mesajı'
        verbose_name_plural = 'İletişim Mesajları'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.subject}'

@receiver(post_save, sender=ContactMessage)
def notify_admin_new_contact(sender, instance, created, **kwargs):
    if created:
        admin_users = User.objects.filter(is_superuser=True)
        for admin in admin_users:
            notify.send(
                sender=instance,
                recipient=admin,
                verb='yeni bir iletişim mesajı gönderdi',
                action_object=instance,
                description=instance.message[:100] + '...' if len(instance.message) > 100 else instance.message
            )
