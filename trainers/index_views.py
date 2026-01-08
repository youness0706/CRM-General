"""
Refactored Django Views - Optimized for Performance
Hybrid architecture: Server-side processing + Client-side rendering
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Prefetch
from django.core.cache import cache
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import json
from .middleware import require_organization
from .models import Staff, Trainer, Payments

# Payment category choices for display
PAYMENT_CATEGORY_CHOICES = {
    "month": "شهرية",
    "subscription": "انخراط",
    "assurance": "التأمين",
    "jawaz": "جواز",
}

@require_organization
@login_required
def Home(request):
    """
    Shell view - Returns minimal HTML template
    All data loading happens via AJAX endpoints
    """
    staff = Staff.objects.select_related('user').get(user=request.user)
    
    if not staff.is_admin:
        return redirect('dashboard')
    
    # Return shell template only - no heavy processing here
    context = {
        'organization_slug': request.organization.slug,
    }
    return render(request, "pages/index.html", context)


@login_required
@require_http_methods(["GET"])
def api_financial_summary(request):
    """
    JSON API: Financial summary data
    Cached for 5 minutes to reduce DB load
    """
    organization = request.organization
    cache_key = f'financial_summary_{organization.id}_{timezone.now().date()}'
    
    # Try cache first
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    now = timezone.now()
    today = now.date()
    
    # Optimized single query with conditional aggregation
    payments = Payments.objects.filter(organization=organization)
    
    summary = payments.aggregate(
        total_yearly_income=Sum(
            'paymentAmount',
            filter=Q(paymentdate__year=today.year)
        ),
        monthly_income=Sum(
            'paymentAmount',
            filter=Q(paymentdate__year=today.year, paymentdate__month=today.month)
        ),
        today_income=Sum(
            'paymentAmount',
            filter=Q(paymentdate=today)
        )
    )
    
    data = {
        'total_yearly_income': float(summary['total_yearly_income'] or 0),
        'monthly_income': float(summary['monthly_income'] or 0),
        'today_income': float(summary['today_income'] or 0)
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, data, 300)
    
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def api_chart_data(request):
    """
    JSON API: Chart data for income by category
    Returns monthly breakdown for current year
    """
    organization = request.organization
    cache_key = f'chart_data_{organization.id}_{timezone.now().date()}'
    
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    today = timezone.now().date()
    
    # Optimized query with aggregation
    payment_categories = ['month', 'subscription', 'assurance', 'jawaz']
    chart_data = {category: [0] * 12 for category in payment_categories}
    
    for category in payment_categories:
        category_income = Payments.objects.filter(
            organization=organization,
            paymentCategry=category,
            paymentdate__year=today.year
        ).values('paymentdate__month').annotate(
            total_income=Sum('paymentAmount')
        )
        
        for entry in category_income:
            month = entry['paymentdate__month'] - 1
            chart_data[category][month] = float(entry['total_income'] or 0)
    
    data = {
        'chart_labels': [str(m) for m in range(1, 13)],
        'chart_data': chart_data
    }
    
    cache.set(cache_key, data, 300)
    
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def api_payment_status(request):
    """
    JSON API: Unpaid trainers by category
    Optimized with prefetch_related to avoid N+1 queries
    """
    organization = request.organization
    today = timezone.now().date()
    
    payment_categories = {
        'month': {
            'label': 'شهرية', 
            'frequency': 'monthly', 
            'grace_days': 0
        },
        'subscription': {
            'label': 'انخراط', 
            'frequency': 'yearly', 
            'grace_days': 0
        },
        'assurance': {
            'label': 'التأمين', 
            'frequency': 'yearly', 
            'grace_days': 0
        },
        'jawaz': {
            'label': 'جواز', 
            'frequency': 'yearly', 
            'grace_days': 0
        }
    }
    
    payment_status = {}
    
    # Prefetch all payments for active trainers to avoid N+1
    trainers = Trainer.objects.filter(
        is_active=True, 
        organization=organization
    ).prefetch_related(
        Prefetch(
            'payments',  # Correct related_name from model
            queryset=Payments.objects.filter(
                organization=organization
            ).order_by('-paymentdate'),
            to_attr='all_payments'
        )
    )
    
    for category, category_info in payment_categories.items():
        unpaid_trainers = []
        
        for trainer in trainers:
            # Filter payments in memory (already prefetched)
            category_payments = [
                p for p in trainer.all_payments 
                if p.paymentCategry == category
            ]
            
            if category_payments:
                last_payment = category_payments[0]  # Already ordered by date
                payment_due_date = None
                
                if category_info['frequency'] == 'monthly':
                    payment_due_date = last_payment.paymentdate + relativedelta(months=1)
                elif category_info['frequency'] == 'yearly':
                    payment_due_date = last_payment.paymentdate.replace(
                        year=last_payment.paymentdate.year + 1
                    ) + timedelta(days=category_info['grace_days'])
                
                if today >= payment_due_date:
                    unpaid_trainers.append({
                        'trainer_id': trainer.id,
                        'trainer_name': f"{trainer.first_name} {trainer.last_name}",
                        'last_payment_date': last_payment.paymentdate.isoformat()
                    })
            else:
                # Never paid in this category
                unpaid_trainers.append({
                    'trainer_id': trainer.id,
                    'trainer_name': f"{trainer.first_name} {trainer.last_name}",
                    'last_payment_date': None
                })
        
        payment_status[category] = {
            'label': category_info['label'],
            'unpaid_trainers': unpaid_trainers,
            'total_unpaid_trainers': len(unpaid_trainers)
        }
    
    return JsonResponse({'payment_status': payment_status})


@login_required
@require_http_methods(["GET"])
def api_paid_today(request):
    """
    JSON API: Trainers who paid today
    Optimized with select_related
    """
    organization = request.organization
    today = timezone.now().date()
    
    # Optimized query with select_related to join trainer data
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
    )
    
    paid_today = [
        {
            "trainer_id": payment['trainer__id'],
            "trainer_name": f"{payment['trainer__first_name']} {payment['trainer__last_name']}",
            "payment_date": payment['paymentdate'].isoformat(),
            "payment_category": PAYMENT_CATEGORY_CHOICES.get(
                payment['paymentCategry'], 
                payment['paymentCategry']
            ),
            "payment_amount": float(payment['paymentAmount'])
        }
        for payment in payments
    ]
    
    return JsonResponse({'paid_today': paid_today})


@login_required
@require_http_methods(["POST"])
def bulk_deactivate_trainers(request):
    """
    JSON API: Bulk deactivate trainers
    Returns success/error status
    """
    try:
        data = json.loads(request.body)
        trainer_ids = data.get('trainer_ids', [])
        
        if not trainer_ids:
            return JsonResponse({
                'success': False,
                'error': 'لم يتم تحديد أي متدربين'
            }, status=400)
        
        # Bulk update - single query
        updated_count = Trainer.objects.filter(
            id__in=trainer_ids,
            organization=request.organization
        ).update(is_active=False)
        
        # Clear relevant caches
        cache_keys = [
            f'financial_summary_{request.organization.id}_{timezone.now().date()}',
            f'chart_data_{request.organization.id}_{timezone.now().date()}'
        ]
        cache.delete_many(cache_keys)
        
        return JsonResponse({
            'success': True,
            'message': f'تم إلغاء تفعيل {updated_count} متدرب بنجاح',
            'count': updated_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'بيانات غير صالحة'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)