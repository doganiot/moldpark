# Generated manually for updating monthly_limit values

from django.db import migrations

def update_monthly_limits(apps, schema_editor):
    """Mevcut merkezlerin monthly_limit değerlerini güncelle"""
    Center = apps.get_model('center', 'Center')
    
    # Tüm merkezleri al
    centers = Center.objects.all()
    
    for center in centers:
        # Eğer monthly_limit varsayılan değerde (50) ise, mold_limit değerini kopyala
        if center.monthly_limit == 50:  # varsayılan değer
            # mold_limit değerini monthly_limit'e kopyala
            center.monthly_limit = center.mold_limit * 5  # Aylık için 5 katı yapalım
            center.save()
            print(f"Merkez '{center.name}' monthly_limit güncellendi: {center.monthly_limit}")

def reverse_update_monthly_limits(apps, schema_editor):
    """Geri alma işlemi - monthly_limit'i varsayılan değere döndür"""
    Center = apps.get_model('center', 'Center')
    
    centers = Center.objects.all()
    for center in centers:
        center.monthly_limit = 50  # varsayılan değere döndür
        center.save()

class Migration(migrations.Migration):

    dependencies = [
        ('center', '0004_center_monthly_limit'),
    ]

    operations = [
        migrations.RunPython(
            update_monthly_limits,
            reverse_update_monthly_limits,
        ),
    ] 