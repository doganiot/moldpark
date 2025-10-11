# Generated manually for VAT implementation
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_update_invoice_and_transaction_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='subtotal_without_vat',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name='KDV Hariç Tutar',
                help_text='KDV hesaplanmadan önceki tutar'
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='vat_rate',
            field=models.DecimalField(
                decimal_places=2,
                default=20.00,
                max_digits=5,
                verbose_name='KDV Oranı (%)',
                help_text='Uygulanan KDV oranı (varsayılan %20)'
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='vat_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name='KDV Tutarı',
                help_text='Hesaplanan KDV tutarı'
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='total_with_vat',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name='KDV Dahil Toplam',
                help_text='KDV dahil toplam tutar'
            ),
        ),
    ]

