from django.apps import AppConfig


class MoldConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mold'
    
    def ready(self):
        # Signal'ları yükle - import işlemi sırasında signal'lar kayıt edilir
        try:
            from mold import signals  # noqa
            from django.db.models.signals import post_save
            from mold.models import EarMold
            # Signal'ı kaydet - sadece bir kez kaydedilmesi için disconnect önce çağrılır
            post_save.disconnect(signals.create_invoice_on_mold_completion, sender=EarMold)
            post_save.connect(signals.create_invoice_on_mold_completion, sender=EarMold)
        except (Exception, ValueError) as e:
            # İlk çalışmada disconnect hata verebilir, bu normal
            import logging
            logger = logging.getLogger(__name__)
            try:
                from django.db.models.signals import post_save
                from mold.models import EarMold
                post_save.connect(signals.create_invoice_on_mold_completion, sender=EarMold)
            except Exception as e2:
                logger.error(f"Signal yükleme hatası: {e2}", exc_info=True)