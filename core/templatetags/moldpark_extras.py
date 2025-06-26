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


@register.inclusion_tag('core/widgets/system_health_widget.html')
def system_health_widget():
    """Sistem sağlık widget'ı"""
    try:
        from django.db import connection
        from django.conf import settings
        import shutil
        
        # Temel sağlık skoru hesaplama
        health_score = 100
        
        # Database kontrolü
        database_status = 'healthy'
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            database_status = 'unhealthy'
            health_score -= 30
        
        # Cache kontrolü
        cache_status = 'healthy'
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 60)
            if cache.get('health_check') != 'ok':
                cache_status = 'warning'
                health_score -= 10
        except Exception:
            cache_status = 'warning'
            health_score -= 5
        
        # Disk kullanımı
        disk_usage = 0
        try:
            total, used, free = shutil.disk_usage(settings.BASE_DIR)
            disk_usage = (used / total) * 100
            
            if disk_usage > 90:
                health_score -= 20
            elif disk_usage > 80:
                health_score -= 10
        except Exception:
            disk_usage = 0
        
        # Ağ sağlığı
        from producer.models import ProducerNetwork
        active_networks = ProducerNetwork.objects.filter(status='active').count()
        total_networks = ProducerNetwork.objects.count()
        
        network_status = 'healthy'
        if total_networks > 0:
            network_health = (active_networks / total_networks) * 100
            if network_health < 50:
                network_status = 'warning'
                health_score -= 15
            elif network_health < 70:
                health_score -= 5
        
        # Kritik uyarılar
        critical_alerts = []
        
        # Geciken siparişler
        from producer.models import ProducerOrder
        overdue_orders = ProducerOrder.objects.filter(
            estimated_delivery__lt=timezone.now(),
            status__in=['received', 'designing', 'production', 'quality_check']
        ).count()
        
        if overdue_orders > 10:
            critical_alerts.append({
                'message': f'{overdue_orders} sipariş gecikmiş',
                'type': 'overdue_orders'
            })
            health_score -= 10
        
        # Güvenlik riskleri
        from producer.models import Producer
        risky_producers = Producer.objects.filter(
            user__is_staff=True
        ) | Producer.objects.filter(
            user__is_superuser=True
        )
        
        if risky_producers.exists():
            critical_alerts.append({
                'message': f'{risky_producers.count()} üretici hesabının admin yetkisi var',
                'type': 'security_risk'
            })
            health_score -= 25
        
        health_status = {
            'score': max(0, health_score),
            'database': database_status,
            'cache': cache_status,
            'disk_usage': round(disk_usage, 1),
            'network': network_status,
            'active_networks': active_networks,
            'total_networks': total_networks,
            'critical_alerts': critical_alerts,
            'last_check': timezone.now()
        }
        
        return {'health_status': health_status}
        
    except Exception as e:
        # Hata durumunda minimal widget göster
        return {
            'health_status': {
                'score': 0,
                'database': 'unknown',
                'cache': 'unknown',
                'disk_usage': 0,
                'network': 'unknown',
                'active_networks': 0,
                'total_networks': 0,
                'critical_alerts': [{'message': f'Widget yüklenirken hata: {str(e)}', 'type': 'error'}],
                'last_check': timezone.now()
            }
        }


@register.inclusion_tag('core/widgets/smart_notification_summary.html')
def smart_notification_summary(user):
    """Akıllı bildirim özeti widget'ı"""
    try:
        last_24h = timezone.now() - timedelta(hours=24)
        
        # Kullanıcının son 24 saatteki bildirimleri
        recent_notifications = user.notifications.filter(
            timestamp__gte=last_24h
        )
        
        # Bildirim türleri analizi
        notification_types = {}
        for notification in recent_notifications:
            verb = notification.verb
            if verb not in notification_types:
                notification_types[verb] = 0
            notification_types[verb] += 1
        
        # Akıllı öneriler
        suggestions = []
        
        if hasattr(user, 'center'):
            center = user.center
            used_molds = center.molds.count()
            limit_percentage = (used_molds / center.mold_limit) * 100
            
            if limit_percentage > 80:
                suggestions.append({
                    'type': 'limit_warning',
                    'message': f'Kalıp limitinizin %{limit_percentage:.0f}\'ini kullandınız',
                    'priority': 'high' if limit_percentage > 90 else 'medium'
                })
            
            # Pasif merkez kontrolü
            last_activity = center.molds.order_by('-created_at').first()
            if last_activity:
                days_inactive = (timezone.now() - last_activity.created_at).days
                if days_inactive >= 7:
                    suggestions.append({
                        'type': 'inactive_warning',
                        'message': f'{days_inactive} gündür yeni sipariş vermiyorsunuz',
                        'priority': 'medium'
                    })
        
        elif hasattr(user, 'producer'):
            producer = user.producer
            
            # Bekleyen siparişler
            pending_orders = producer.orders.filter(status='received').count()
            if pending_orders > 5:
                suggestions.append({
                    'type': 'pending_orders',
                    'message': f'{pending_orders} bekleyen sipariş var',
                    'priority': 'high'
                })
            
            # Kapasite uyarısı
            current_month_orders = producer.get_current_month_orders()
            capacity_percentage = (current_month_orders / producer.mold_limit) * 100
            if capacity_percentage > 90:
                suggestions.append({
                    'type': 'capacity_warning',
                    'message': f'Aylık kapasitenizin %{capacity_percentage:.0f}\'ini kullandınız',
                    'priority': 'high'
                })
        
        summary = {
            'total_notifications_24h': recent_notifications.count(),
            'unread_count': recent_notifications.unread().count(),
            'notification_types': notification_types,
            'suggestions': suggestions,
            'last_update': timezone.now()
        }
        
        return {'notification_summary': summary}
        
    except Exception as e:
        return {
            'notification_summary': {
                'total_notifications_24h': 0,
                'unread_count': 0,
                'notification_types': {},
                'suggestions': [{'type': 'error', 'message': f'Widget hatası: {str(e)}', 'priority': 'low'}],
                'last_update': timezone.now()
            }
        }


@register.filter
def mul(value, arg):
    """Çarpma işlemi filtresi"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter 
def div(value, arg):
    """Bölme işlemi filtresi"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0 