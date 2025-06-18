"""
MoldPark Template Tags
Dashboard widget'ları ve yardımcı fonksiyonlar
"""

from django import template
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.contrib.auth.models import User
from center.models import Center
from producer.models import Producer, ProducerOrder, ProducerNetwork
from mold.models import EarMold
from datetime import datetime, timedelta
import json

register = template.Library()


@register.inclusion_tag('core/widgets/system_stats.html')
def system_stats():
    """Sistem genel istatistikleri widget'ı"""
    now = timezone.now()
    today = now.date()
    this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'total_users': User.objects.count(),
        'total_centers': Center.objects.count(),
        'total_producers': Producer.objects.count(),
        'active_producers': Producer.objects.filter(is_active=True, is_verified=True).count(),
        'total_molds': EarMold.objects.count(),
        'molds_this_month': EarMold.objects.filter(created_at__gte=this_month).count(),
        'active_orders': ProducerOrder.objects.filter(
            status__in=['received', 'designing', 'production', 'quality_check']
        ).count(),
        'completed_orders': ProducerOrder.objects.filter(status='delivered').count(),
    }
    
    return {'stats': stats}


@register.inclusion_tag('core/widgets/production_pipeline.html')
def production_pipeline():
    """Üretim hattı durumu widget'ı"""
    pipeline_stats = []
    
    stages = [
        ('received', 'Alınan Siparişler', 'primary'),
        ('designing', '3D Tasarım', 'info'),
        ('production', 'Üretimde', 'warning'),
        ('quality_check', 'Kalite Kontrol', 'secondary'),
        ('packaging', 'Paketleme', 'success'),
        ('shipping', 'Kargoda', 'dark'),
    ]
    
    for stage_code, stage_name, color in stages:
        count = ProducerOrder.objects.filter(status=stage_code).count()
        pipeline_stats.append({
            'stage': stage_name,
            'count': count,
            'color': color,
            'percentage': 0  # Hesaplanacak
        })
    
    # Yüzde hesaplama
    total = sum(stat['count'] for stat in pipeline_stats)
    if total > 0:
        for stat in pipeline_stats:
            stat['percentage'] = round((stat['count'] / total) * 100, 1)
    
    return {'pipeline_stats': pipeline_stats}


@register.inclusion_tag('core/widgets/performance_metrics.html')
def performance_metrics():
    """Performans metrikleri widget'ı"""
    now = timezone.now()
    last_30_days = now - timedelta(days=30)
    
    # Ortalama teslimat süresi
    completed_orders = ProducerOrder.objects.filter(
        status='delivered',
        created_at__gte=last_30_days,
        actual_delivery__isnull=False
    )
    
    avg_delivery_time = 0
    if completed_orders.exists():
        total_time = sum([
            (order.actual_delivery - order.created_at).days 
            for order in completed_orders
        ])
        avg_delivery_time = round(total_time / completed_orders.count(), 1)
    
    # Kalite skorları
    quality_scores = EarMold.objects.filter(
        quality_score__isnull=False,
        created_at__gte=last_30_days
    ).aggregate(avg_quality=Avg('quality_score'))
    
    avg_quality = round(quality_scores['avg_quality'] or 0, 1)
    
    # Üretici performansı
    top_producers = Producer.objects.filter(
        orders__created_at__gte=last_30_days
    ).annotate(
        order_count=Count('orders'),
        completed_count=Count('orders', filter=Q(orders__status='delivered'))
    ).filter(order_count__gt=0).order_by('-completed_count')[:5]
    
    metrics = {
        'avg_delivery_time': avg_delivery_time,
        'avg_quality_score': avg_quality,
        'total_orders_30d': ProducerOrder.objects.filter(created_at__gte=last_30_days).count(),
        'completed_orders_30d': completed_orders.count(),
        'top_producers': top_producers,
    }
    
    return {'metrics': metrics}


@register.inclusion_tag('core/widgets/network_health.html')
def network_health():
    """Ağ sağlığı widget'ı"""
    networks = ProducerNetwork.objects.all()
    
    network_stats = {
        'total': networks.count(),
        'active': networks.filter(status='active').count(),
        'pending': networks.filter(status='pending').count(),
        'suspended': networks.filter(status='suspended').count(),
        'terminated': networks.filter(status='terminated').count(),
    }
    
    # Sağlık skoru hesaplama
    if network_stats['total'] > 0:
        health_score = round(
            (network_stats['active'] / network_stats['total']) * 100, 1
        )
    else:
        health_score = 0
    
    network_stats['health_score'] = health_score
    
    return {'network_stats': network_stats}


@register.simple_tag
def get_mold_status_color(status):
    """Kalıp durumu için renk döndürür"""
    color_map = {
        'waiting': 'warning',
        'processing': 'info',
        'completed': 'success',
        'revision': 'danger',
        'shipping': 'primary',
        'delivered': 'secondary',
    }
    return color_map.get(status, 'light')


@register.simple_tag
def get_order_priority_color(priority):
    """Sipariş önceliği için renk döndürür"""
    color_map = {
        'low': 'secondary',
        'normal': 'info',
        'high': 'warning',
        'urgent': 'danger',
    }
    return color_map.get(priority, 'info')


@register.filter
def percentage(value, total):
    """Yüzde hesaplama filtresi"""
    if not total or total == 0:
        return 0
    return round((value / total) * 100, 1)


@register.filter
def days_since(date):
    """Tarihten bu yana geçen gün sayısı"""
    if not date:
        return 0
    now = timezone.now()
    if timezone.is_aware(date):
        delta = now - date
    else:
        delta = now.replace(tzinfo=None) - date
    return delta.days


@register.filter
def format_duration(minutes):
    """Dakika cinsinden süreyi okunabilir formata çevirir"""
    if not minutes:
        return "0 dk"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours > 0:
        return f"{hours}s {remaining_minutes}dk"
    else:
        return f"{minutes}dk"


@register.inclusion_tag('core/widgets/recent_activities.html')
def recent_activities(limit=10):
    """Son aktiviteler widget'ı"""
    activities = []
    
    # Son kalıplar
    recent_molds = EarMold.objects.select_related(
        'center'
    ).order_by('-created_at')[:limit//2]
    
    for mold in recent_molds:
        activities.append({
            'type': 'mold',
            'icon': 'fas fa-ear-listen',
            'title': f'Yeni kalıp: {mold.patient_name} {mold.patient_surname}',
            'subtitle': f'{mold.center.name} - {mold.get_mold_type_display()}',
            'time': mold.created_at,
            'color': get_mold_status_color(mold.status),
        })
    
    # Son siparişler
    recent_orders = ProducerOrder.objects.select_related(
        'producer', 'center'
    ).order_by('-created_at')[:limit//2]
    
    for order in recent_orders:
        activities.append({
            'type': 'order',
            'icon': 'fas fa-shopping-cart',
            'title': f'Sipariş: {order.order_number}',
            'subtitle': f'{order.producer.company_name} → {order.center.name}',
            'time': order.created_at,
            'color': get_order_priority_color(order.priority),
        })
    
    # Zamana göre sırala
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return {'activities': activities[:limit]}


@register.inclusion_tag('core/widgets/system_alerts.html')
def system_alerts():
    """Sistem uyarıları widget'ı"""
    alerts = []
    
    # Bekleyen siparişler
    overdue_orders = ProducerOrder.objects.filter(
        estimated_delivery__lt=timezone.now(),
        status__in=['received', 'designing', 'production', 'quality_check']
    ).count()
    
    if overdue_orders > 0:
        alerts.append({
            'type': 'warning',
            'icon': 'fas fa-clock',
            'title': 'Geciken Siparişler',
            'message': f'{overdue_orders} sipariş tahmini teslimat tarihini geçti',
            'action_url': '/admin/producer/producerorder/?status__in=received,designing,production,quality_check',
            'action_text': 'Kontrol Et'
        })
    
    # Askıya alınmış ağlar
    suspended_networks = ProducerNetwork.objects.filter(status='suspended').count()
    if suspended_networks > 0:
        alerts.append({
            'type': 'danger',
            'icon': 'fas fa-network-wired',
            'title': 'Askıya Alınmış Ağlar',
            'message': f'{suspended_networks} üretici ağı askıya alınmış durumda',
            'action_url': '/admin/producer/producernetwork/?status=suspended',
            'action_text': 'İncele'
        })
    
    # Doğrulanmamış üreticiler
    unverified_producers = Producer.objects.filter(
        is_active=True, 
        is_verified=False
    ).count()
    
    if unverified_producers > 0:
        alerts.append({
            'type': 'info',
            'icon': 'fas fa-user-check',
            'title': 'Doğrulama Bekleyen Üreticiler',
            'message': f'{unverified_producers} üretici doğrulama bekliyor',
            'action_url': '/admin/producer/producer/?is_verified=False',
            'action_text': 'Doğrula'
        })
    
    return {'alerts': alerts}


@register.simple_tag
def moldpark_version():
    """MoldPark versiyonu"""
    from django.conf import settings
    return getattr(settings, 'MOLDPARK_VERSION', '2.0.0')


# Mesajlaşma sistemi için filter'lar
@register.filter
def basename(value):
    """Dosya yolundan sadece dosya adını döndürür"""
    import os
    if value:
        return os.path.basename(str(value))
    return value


@register.filter
def file_size(value):
    """Dosya boyutunu human-readable format'ta döndürür"""
    if not value:
        return "0 B"
    
    try:
        size = value.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except:
        return "Bilinmiyor"


@register.filter
def message_type_icon(message_type):
    """Mesaj türüne göre ikon döndürür"""
    icons = {
        'center_to_admin': 'fas fa-building',
        'producer_to_admin': 'fas fa-industry', 
        'admin_to_center': 'fas fa-crown',
        'admin_to_producer': 'fas fa-crown',
        'admin_broadcast': 'fas fa-bullhorn',
    }
    return icons.get(message_type, 'fas fa-envelope')


@register.filter
def priority_color(priority):
    """Öncelik seviyesine göre renk döndürür"""
    colors = {
        'urgent': 'danger',
        'high': 'warning',
        'normal': 'info',
        'low': 'secondary',
    }
    return colors.get(priority, 'info') 