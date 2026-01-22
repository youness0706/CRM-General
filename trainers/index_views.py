"""
Optimized Django Views - FIXED bulk_deactivate
Performance improvements: Query optimization, intelligent caching, progressive data loading
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Prefetch, Max
from django.core.cache import cache
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import timedelta, date
import json

from .middleware import require_organization
from .models import Staff, Trainer, Payments, OrganizationInfo as Organization

# Constants
PAYMENT_CATEGORIES = {
    "month": {"label": "شهرية", "frequency": "monthly"},
    "subscription": {"label": "انخراط", "frequency": "yearly"},
    "assurance": {"label": "التأمين", "frequency": "yearly"},
    "jawaz": {"label": "جواز", "frequency": "yearly"},
}

CACHE_TIMEOUT = 300  # 5 minutes


@require_organization
@login_required
def Home(request):
    """
    Minimal shell view - all data loaded via AJAX
    """
    staff = Staff.objects.select_related('user').get(user=request.user)
    
    if not staff.is_admin:
        return redirect('dashboard')
    
    context = {
        'organization_slug': request.organization.slug,
    }
    return render(request, "pages/index.html", context)


@login_required
@require_http_methods(["GET"])
def api_kpis(request):
    """
    JSON API: Dashboard KPIs with intelligent caching
    """
    organization = request.organization
    period = request.GET.get('period', 'today')
    
    cache_key = f'kpis_{organization.id}_{period}_{timezone.now().date()}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data)
    
    # Calculate date range based on period
    today = timezone.now().date()
    
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = today
    else:  # year
        start_date = today.replace(month=1, day=1)
        end_date = today
    
    # Optimized queries with aggregation
    payments_qs = Payments.objects.filter(
        organization=organization,
        paymentdate__range=[start_date, end_date]
    )
    
    income_data = payments_qs.aggregate(
        total=Sum('paymentAmount')
    )
    
    active_trainers = Trainer.objects.filter(
        organization=organization,
        is_active=True
    ).count()
    
    # Calculate unpaid trainers (simplified for performance)
    unpaid_count = calculate_unpaid_count(organization)
    
    # Subscriptions expiring soon (next 30 days)
    expiring_soon = Trainer.objects.filter(
        organization=organization,
        is_active=True,
        # Add your subscription_end_date field logic here
    ).count()
    
    data = {
        'income': {
            'value': float(income_data['total'] or 0),
            'change': None,  # Calculate from previous period if needed
            'trend': None
        },
        'active': {
            'value': active_trainers,
            'change': None,
            'trend': None
        },
        'unpaid': {
            'value': unpaid_count,
            'change': None,
            'trend': None
        },
        'expiring': {
            'value': expiring_soon,
            'change': None,
            'trend': None
        }
    }
    
    cache.set(cache_key, data, CACHE_TIMEOUT)
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def api_chart_data(request):
    """
    JSON API: Monthly income breakdown by category
    Optimized with single query and aggregation
    """
    organization = request.organization
    year = request.GET.get('year', timezone.now().year)
    
    cache_key = f'chart_data_{organization.id}_{year}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data)
    
    # Single optimized query with conditional aggregation
    monthly_data = Payments.objects.filter(
        organization=organization,
        paymentdate__year=year
    ).values('paymentdate__month', 'paymentCategry').annotate(
        total=Sum('paymentAmount')
    ).order_by('paymentdate__month')
    
    # Initialize data structure
    chart_data = {category: [0] * 12 for category in PAYMENT_CATEGORIES.keys()}
    
    # Populate data
    for entry in monthly_data:
        month = entry['paymentdate__month'] - 1
        category = entry['paymentCategry']
        if category in chart_data:
            chart_data[category][month] = float(entry['total'])
    
    data = {
        'chart_labels': [f'{m}' for m in range(1, 13)],
        'chart_data': chart_data
    }
    
    cache.set(cache_key, data, CACHE_TIMEOUT)
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def api_payment_status(request):
    """
    JSON API: Unpaid trainers by category
    Heavily optimized with prefetch and in-memory processing
    """
    organization = request.organization
    cache_key = f'payment_status_{organization.id}_{timezone.now().date()}'
    
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    today = timezone.now().date()
    
    # Prefetch all payments in one query
    trainers = Trainer.objects.filter(
        is_active=True,
        organization=organization
    ).prefetch_related(
        Prefetch(
            'payments',
            queryset=Payments.objects.select_related('trainer').order_by('-paymentdate'),
            to_attr='all_payments'
        )
    ).only('id', 'first_name', 'last_name')
    
    payment_status = {}
    
    for category, info in PAYMENT_CATEGORIES.items():
        unpaid_trainers = []
        
        for trainer in trainers:
            # Process in memory (already prefetched)
            category_payments = [p for p in trainer.all_payments if p.paymentCategry == category]
            
            is_unpaid = False
            last_payment_date = None
            
            if category_payments:
                last_payment = category_payments[0]
                last_payment_date = last_payment.paymentdate
                
                # Calculate due date based on frequency
                if info['frequency'] == 'monthly':
                    due_date = last_payment_date + relativedelta(months=1)
                else:  # yearly
                    due_date = last_payment_date.replace(year=last_payment_date.year + 1)
                
                is_unpaid = today >= due_date
            else:
                # Never paid
                is_unpaid = True
            
            if is_unpaid:
                unpaid_trainers.append({
                    'trainer_id': trainer.id,
                    'trainer_name': f"{trainer.first_name} {trainer.last_name}",
                    'last_payment_date': last_payment_date.isoformat() if last_payment_date else None
                })
        
        payment_status[category] = {
            'label': info['label'],
            'unpaid_trainers': unpaid_trainers[:20],  # Limit to 20 for performance
            'total_unpaid_trainers': len(unpaid_trainers)
        }
    
    data = {'payment_status': payment_status}
    cache.set(cache_key, data, CACHE_TIMEOUT)
    
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def api_paid_today(request):
    """
    JSON API: Today's payments
    Simple and fast query
    """
    organization = request.organization
    today = timezone.now().date()
    
    cache_key = f'paid_today_{organization.id}_{today}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data)
    
    payments = Payments.objects.filter(
        organization=organization,
        paymentdate=today
    ).select_related('trainer').values(
        'trainer__id',
        'trainer__first_name',
        'trainer__last_name',
        'paymentdate',
        'paymentCategry',
        'paymentAmount'
    )[:50]  # Limit to recent 50
    
    paid_today = [
        {
            "trainer_id": p['trainer__id'],
            "trainer_name": f"{p['trainer__first_name']} {p['trainer__last_name']}",
            "payment_date": p['paymentdate'].isoformat(),
            "payment_category": PAYMENT_CATEGORIES.get(p['paymentCategry'], {}).get('label', p['paymentCategry']),
            "payment_amount": float(p['paymentAmount'])
        }
        for p in payments
    ]
    
    data = {'paid_today': paid_today}
    cache.set(cache_key, data, CACHE_TIMEOUT)
    
    return JsonResponse(data)


@require_organization
@login_required
@require_http_methods(["POST"])
def bulk_deactivate_trainers(request):
    """
    JSON API: Bulk deactivate trainers
    FIXED: Avoids MySQL subquery limitation
    """
    try:
        data = json.loads(request.body)
        trainer_ids = data.get('trainer_ids', [])
        
        if not trainer_ids:
            return JsonResponse({
                'success': False,
                'error': 'لم يتم تحديد أي متدربين'
            }, status=400)
        
        # Convert to list of integers to avoid issues
        trainer_ids = [int(tid) for tid in trainer_ids]
        
        # FIXED: First get the valid IDs as a Python list to avoid subquery
        # This prevents the MySQL error about updating the table you're selecting from
        valid_trainers = list(
            Trainer.objects.filter(
                id__in=trainer_ids,
                organization=request.organization
            ).values_list('id', flat=True)
        )
        
        if not valid_trainers:
            return JsonResponse({
                'success': False,
                'error': 'لا توجد متدربين صالحين للتحديث'
            }, status=400)
        
        # Now do the bulk update using the Python list
        updated_count = Trainer.objects.filter(
            id__in=valid_trainers
        ).update(is_active=False)
        
        # Clear all related caches
        clear_organization_cache(request.organization.id)
        
        return JsonResponse({
            'success': True,
            'message': f'تم إلغاء تفعيل {updated_count} متدرب بنجاح',
            'count': updated_count
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': 'معرفات غير صالحة'
        }, status=400)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات غير صالحة'
        }, status=400)
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Bulk deactivate error: {str(e)}')
        
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ في الخادم: {str(e)}'
        }, status=500)


@require_organization
@login_required
def subscription_status(request):
    """
    Subscription status page with optimized queries
    """
    organization = request.organization
    
    # Calculate subscription status
    today = timezone.now().date()
    
    if organization.subscription_end_date:
        days_left = (organization.subscription_end_date - today).days
        
        if days_left > 30:
            status_class = 'success'
            status_text = 'الاشتراك نشط'
        elif days_left > 0:
            status_class = 'warning'
            status_text = f'الاشتراك ينتهي قريباً ({days_left} يوم)'
        else:
            status_class = 'danger'
            status_text = 'الاشتراك منتهي'
    else:
        days_left = None
        status_class = 'danger'
        status_text = 'لا يوجد اشتراك'
    
    # Get recent payments (optimized query)
    recent_payments = organization.subscription_payments.order_by('-payment_date')[:10]
    
    # Calculate total paid
    total_paid = organization.subscription_payments.aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Next payment date suggestion
    next_payment_date = None
    if organization.subscription_end_date:
        next_payment_date = organization.subscription_end_date - timedelta(days=7)
    
    context = {
        'organization': organization,
        'subscription_status': {
            'class': status_class,
            'text': status_text
        },
        'days_left': days_left,
        'recent_payments': recent_payments,
        'total_paid': total_paid,
        'next_payment_date': next_payment_date,
        'is_admin': request.user.staff.is_admin if hasattr(request.user, 'staff') else False
    }
    
    return render(request, 'pages/subscription_status.html', context)


# Helper functions
def calculate_unpaid_count(organization):
    """
    Calculate total unpaid trainers across all categories
    Cached for performance
    """
    cache_key = f'unpaid_count_{organization.id}_{timezone.now().date()}'
    cached = cache.get(cache_key)
    
    if cached is not None:
        return cached
    
    # Simplified calculation - customize based on your logic
    today = timezone.now().date()
    
    trainers = Trainer.objects.filter(
        organization=organization,
        is_active=True
    ).prefetch_related('payments')
    
    unpaid_count = 0
    
    for trainer in trainers:
        # Check if any payment category is overdue
        has_overdue = False
        for category, info in PAYMENT_CATEGORIES.items():
            payments = [p for p in trainer.payments.all() if p.paymentCategry == category]
            
            if not payments:
                has_overdue = True
                break
            
            last_payment = max(payments, key=lambda p: p.paymentdate)
            
            if info['frequency'] == 'monthly':
                due_date = last_payment.paymentdate + relativedelta(months=1)
            else:
                due_date = last_payment.paymentdate.replace(year=last_payment.paymentdate.year + 1)
            
            if today >= due_date:
                has_overdue = True
                break
        
        if has_overdue:
            unpaid_count += 1
    
    cache.set(cache_key, unpaid_count, CACHE_TIMEOUT)
    return unpaid_count


def clear_organization_cache(org_id):
    """
    Clear all cached data for an organization
    """
    today = timezone.now().date()
    
    # List of cache keys to clear
    cache_keys = [
        f'kpis_{org_id}_today_{today}',
        f'kpis_{org_id}_week_{today}',
        f'kpis_{org_id}_month_{today}',
        f'kpis_{org_id}_year_{today}',
        f'chart_data_{org_id}_{today.year}',
        f'payment_status_{org_id}_{today}',
        f'paid_today_{org_id}_{today}',
        f'unpaid_count_{org_id}_{today}',
    ]
    
    # Try to delete all cache keys
    try:
        cache.delete_many(cache_keys)
    except Exception as e:
        # If batch delete fails, delete one by one
        for key in cache_keys:
            try:
                cache.delete(key)
            except:
                pass