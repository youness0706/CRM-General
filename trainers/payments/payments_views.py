from datetime import datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Value, Sum, Count
from django.db.models.functions import Concat, TruncMonth
from django.core.paginator import Paginator
from django.core.cache import cache
from django.utils import timezone
from django.utils.timezone import make_aware
import json
from ..middleware import require_organization
from ..models import Payments, Staff, Trainer, Costs, Article, Addedpay
from calendar import monthrange


# ==================== PAYMENTS HISTORY ====================

@login_required
@require_organization
def payments_history(request):
    """
    Shell view - Returns minimal HTML template
    Data loaded via AJAX
    """
    context = {
        'organization_slug': request.organization.slug,
    }
    return render(request, "pages/payments_history.html", context)


@login_required
@require_organization
@require_http_methods(["GET"])
def api_payments_list(request):
    """
    JSON API: Get paginated payments list with search
    Optimized with select_related
    """
    organization = request.organization
    
    # Get search query
    search_query = request.GET.get('search', '').strip()
    
    # Base queryset with optimization
    payments = Payments.objects.select_related('trainer').filter(
        organization=organization
    ).only(
        'id', 'paymentCategry', 'paymentAmount', 'paymentdate',
        'trainer__first_name', 'trainer__last_name'
    )
    
    # Apply search filter
    if search_query:
        payments = payments.annotate(
            trainer_full_name=Concat(
                'trainer__first_name',
                Value(' '),
                'trainer__last_name'
            )
        ).filter(
            Q(trainer__first_name__icontains=search_query) |
            Q(trainer__last_name__icontains=search_query) |
            Q(trainer_full_name__icontains=search_query) |
            Q(paymentCategry__icontains=search_query)
        )
    
    # Order by most recent
    payments = payments.order_by('-paymentdate', '-id')
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    
    paginator = Paginator(payments, per_page)
    page_obj = paginator.get_page(page)
    
    # Payment category choices
    PAYMENT_CATEGORY_CHOICES = {
        "month": "شهرية",
        "subscription": "انخراط",
        "assurance": "التأمين",
        "jawaz": "جواز",
    }
    
    # Build response data
    payments_data = []
    for payment in page_obj:
        payments_data.append({
            'id': payment.id,
            'category': PAYMENT_CATEGORY_CHOICES.get(
                payment.paymentCategry, 
                payment.paymentCategry
            ),
            'trainer_name': f"{payment.trainer.first_name} {payment.trainer.last_name}",
            'amount': float(payment.paymentAmount),
            'date': payment.paymentdate.isoformat(),
        })
    
    return JsonResponse({
        'payments': payments_data,
        'total_count': paginator.count,
        'page': page_obj.number,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'search_query': search_query,
    })


@login_required
@require_organization
@require_http_methods(["POST"])
def api_bulk_delete_payments(request):
    """
    JSON API: Bulk delete payments
    Permanently deletes payments (not soft delete)
    """
    try:
        data = json.loads(request.body)
        payment_ids = data.get('payment_ids', [])
        
        if not payment_ids:
            return JsonResponse({
                'success': False,
                'error': 'لم يتم تحديد أي دفعات'
            }, status=400)
        
        # Delete payments
        deleted_count, _ = Payments.objects.filter(
            id__in=payment_ids,
            organization=request.organization
        ).delete()
        
        # Clear cache
        today = timezone.now().date()
        cache_keys = [
            f'financial_summary_{request.organization.id}_{today}',
            f'chart_data_{request.organization.id}_{today}',
        ]
        cache.delete_many(cache_keys)
        
        return JsonResponse({
            'success': True,
            'message': f'تم حذف {deleted_count} دفعة بنجاح',
            'count': deleted_count
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


# ==================== ADD PAYMENT ====================

@login_required
@require_organization
def add_payment(request):
    """
    Shell view for add payment form
    Trainers loaded via AJAX for better performance
    """
    if request.method == 'POST':
        return handle_add_payment_post(request)
    
    context = {
        'organization_slug': request.organization.slug,
    }
    return render(request, 'pages/add_payment.html', context)


@login_required
@require_organization
def handle_add_payment_post(request):
    """Handle payment creation"""
    organization = request.organization
    
    try:
        trainer_id = request.POST.get('trainer')
        paymentdate = request.POST.get('paymentdate')
        paymentCategry = request.POST.get('paymentCategry')
        paymentAmount = request.POST.get('paymentAmount')
        
        # Validate required fields
        if not all([trainer_id, paymentdate, paymentCategry, paymentAmount]):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'جميع الحقول مطلوبة'
                }, status=400)
            return redirect('add_payment')
        
        # Validate trainer exists
        try:
            trainer = Trainer.objects.get(
                id=trainer_id, 
                organization=organization
            )
        except Trainer.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'المتدرب غير موجود'
                }, status=404)
            return redirect('add_payment')
        
        # Validate payment amount
        try:
            amount = Decimal(paymentAmount)
            if amount < 0:
                raise ValueError('المبلغ يجب أن يكون موجباً')
        except (ValueError, Decimal.InvalidOperation) as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'مبلغ الدفع غير صالح'
                }, status=400)
            return redirect('add_payment')
        
        # Create payment
        payment = Payments(
            organization=organization,
            trainer=trainer,
            paymentdate=paymentdate,
            paymentCategry=paymentCategry,
            paymentAmount=amount
        )
        payment.save()
        
        # Clear financial cache
        today = timezone.now().date()
        cache_keys = [
            f'financial_summary_{organization.id}_{today}',
            f'chart_data_{organization.id}_{today}',
        ]
        cache.delete_many(cache_keys)
        
        # Return success
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'payment_id': payment.id,
                'message': 'تم إضافة الدفع بنجاح'
            })
        
        # Redirect to payments history
        return redirect('payments_history')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ: {str(e)}'
            }, status=500)
        return redirect('add_payment')


@login_required
@require_organization
@require_http_methods(["GET"])
def api_trainers_for_payment(request):
    """
    JSON API: Select2 trainers search (FAST)
    - No COUNT() (expensive)
    - Uses slice per_page+1 to know if more
    - Caches results briefly
    """
    try:
        organization = request.organization
        search = (request.GET.get('search') or '').strip()
        page = int(request.GET.get('page', 1))
        per_page = 30  # خففها شوية باش يكون سريع

        # Optional: avoid huge strings
        if len(search) > 50:
            search = search[:50]

        cache_key = f"trainers_select2:{organization.id}:{search}:{page}:{per_page}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse(cached)

        qs = Trainer.objects.filter(
            organization=organization,
            is_active=True
        )

        # IMPORTANT: search strategy
        # istartswith أسرع من icontains بزاف
        if search:
            qs = qs.filter(
                Q(first_name__istartswith=search) |
                Q(last_name__istartswith=search)
            )
        else:
            # إلا ماكاينش search، متجيبش بزاف (أو رجّع خاوي باش يجبر المستخدم يكتب)
            # خيار 1: رجّع خاوي
            return JsonResponse({'results': [], 'pagination': {'more': False}})

        qs = qs.order_by('first_name', 'last_name').values('id', 'first_name', 'last_name')

        start = (page - 1) * per_page
        end = start + per_page + 1  # +1 باش نعرفو واش كاين المزيد بلا count()

        rows = list(qs[start:end])
        more = len(rows) > per_page
        rows = rows[:per_page]

        data = {
            'results': [{'id': r['id'], 'text': f"{r['first_name']} {r['last_name']}"} for r in rows],
            'pagination': {'more': more},
        }

        cache.set(cache_key, data, 60)  # 60s كافية
        return JsonResponse(data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'results': [],
            'pagination': {'more': False},
            'error': str(e)
        }, status=500)


# ==================== FINANCIAL STATUS ====================

@login_required
@require_organization
def finantial_status(request):
    """
    Shell view - Returns minimal HTML template
    Financial data loaded via AJAX
    """
    context = {
        'organization_slug': request.organization.slug,
    }
    return render(request, 'pages/finantial_status.html', context)


# ==================== HELPER FUNCTIONS ====================

def calculate_rent(organization, start_date, end_date, today):
    """Calculate rent expenses within date range"""
    if not organization.datepay or not organization.rent_amount:
        return {'expected': 0, 'paid': 0, 'remaining': 0}
    
    expected_rent = Decimal('0.0')
    rent_date = organization.datepay
    
    while rent_date <= end_date:
        if rent_date >= start_date:
            expected_rent += organization.rent_amount
        # Move to next month
        days_in_month = monthrange(rent_date.year, rent_date.month)[1]
        rent_date += timedelta(days=days_in_month)
    
    # Costs tagged as rent (if you have such a field)
    # For now, we'll assume all rent is expected but not tracked separately
    paid_rent = Decimal('0.0')
    
    return {
        'expected': float(expected_rent),
        'paid': float(paid_rent),
        'remaining': float(expected_rent - paid_rent)
    }


def calculate_staff_salaries(organization, start_date, end_date, today):
    """Calculate staff salary expenses within date range"""
    staff_members = Staff.objects.filter(organization=organization)
    
    expected_salaries = Decimal('0.0')
    
    for staff in staff_members:
        salary_date = staff.started.replace(day=1) if hasattr(staff.started, 'replace') else staff.started
        
        while salary_date <= end_date:
            if salary_date >= start_date:
                expected_salaries += staff.salary
            # Move to next month
            if salary_date.month == 12:
                salary_date = salary_date.replace(year=salary_date.year + 1, month=1)
            else:
                salary_date = salary_date.replace(month=salary_date.month + 1)
    
    # Assume salaries are expected but tracking paid separately would require a Costs entry
    paid_salaries = Decimal('0.0')
    
    return {
        'expected': float(expected_salaries),
        'paid': float(paid_salaries),
        'remaining': float(expected_salaries - paid_salaries)
    }


def get_payments_summary(organization, start_date, end_date):
    """Get payments summary within date range"""
    payments = Payments.objects.filter(
        organization=organization,
        paymentdate__range=[start_date, end_date]
    ).aggregate(
        total=Sum('paymentAmount'),
        count=Count('id')
    )
    
    return {
        'total': float(payments['total'] or 0),
        'count': payments['count'] or 0
    }


def get_costs_summary(organization, start_datetime, end_datetime):
    """Get costs summary within date range"""
    costs = Costs.objects.filter(
        organization=organization,
        date__range=[start_datetime, end_datetime]
    ).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    return {
        'total': float(costs['total'] or 0),
        'count': costs['count'] or 0
    }


@login_required
@require_organization
@require_http_methods(["GET"])
def api_financial_report(request):
    """
    JSON API: Complete financial report data
    Optimized with selective queries and caching
    """
    organization = request.organization
    
    # Get date range from request
    start = request.GET.get('start', '2025-01-01')
    end = request.GET.get('end', '2025-12-31')
    
    # Check cache first
    cache_key = f'financial_report_{organization.id}_{start}_{end}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)
    
    try:
        # Convert to date objects
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
        
        # Create timezone-aware datetime objects for DateTimeField comparisons
        start_datetime = make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = make_aware(datetime.combine(end_date, datetime.max.time()))
        
        today = datetime.today().date()
        
        # Calculate rent
        rent_data = calculate_rent(organization, start_date, end_date, today)
        
        # Calculate staff salaries
        staff_data = calculate_staff_salaries(
            organization, start_date, end_date, today
        )
        
        # Get payments data (optimized query)
        payments_data = get_payments_summary(
            organization, start_date, end_date
        )
        
        # Get costs data
        costs_data = get_costs_summary(
            organization, start_datetime, end_datetime
        )
        
        # Get additional payments
        addedpay_data = Addedpay.objects.filter(
            organization=organization,
            date__range=[start_datetime, end_datetime]
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # Get articles data
        articles_data = Article.objects.filter(
            organization=organization,
            date__range=[start_date, end_date]
        ).aggregate(
            income=Sum('participetion_price'),
            costs=Sum('costs'),
            count=Count('id')
        )
        
        # Calculate totals
        total_income = (
            payments_data['total'] +
            float(addedpay_data['total'] or 0) +
            float(articles_data['income'] or 0)
        )
        
        total_expenses = (
            costs_data['total'] +
            float(articles_data['costs'] or 0) +
            rent_data['expected'] +
            staff_data['expected']
        )
        
        net_profit = total_income - total_expenses
        
        response_data = {
            'success': True,
            'summary': {
                'total_income': round(total_income, 2),
                'total_expenses': round(total_expenses, 2),
                'net_profit': round(net_profit, 2),
            },
            'income': {
                'payments': payments_data,
                'added_payments': {
                    'total': float(addedpay_data['total'] or 0),
                    'count': addedpay_data['count'] or 0
                },
                'articles': {
                    'total': float(articles_data['income'] or 0),
                    'count': articles_data['count'] or 0
                }
            },
            'expenses': {
                'costs': costs_data,
                'articles_costs': {
                    'total': float(articles_data['costs'] or 0),
                    'count': articles_data['count'] or 0
                },
                'rent': rent_data,
                'salaries': staff_data
            },
            'date_range': {
                'start': start,
                'end': end
            }
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@login_required
@require_organization
@require_http_methods(["GET"])
def api_monthly_breakdown(request):
    """
    JSON API: Get monthly breakdown of income and expenses
    Uses Django ORM aggregation for better performance
    """
    organization = request.organization
    
    # Get date range from request
    start = request.GET.get('start', '2025-01-01')
    end = request.GET.get('end', '2025-12-31')
    
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
        
        # Create timezone-aware datetime objects for DateTimeField comparisons
        start_datetime = make_aware(datetime.combine(start_date, datetime.min.time()))
        end_datetime = make_aware(datetime.combine(end_date, datetime.max.time()))
        
        # Income by month
        payments_by_month = Payments.objects.filter(
            organization=organization,
            paymentdate__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('paymentdate')
        ).values('month').annotate(
            total=Sum('paymentAmount')
        ).order_by('month')
        
        added_payments_by_month = Addedpay.objects.filter(
            organization=organization,
            date__range=[start_datetime, end_datetime]
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        articles_income_by_month = Article.objects.filter(
            organization=organization,
            date__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('participetion_price')
        ).order_by('month')
        
        # Expenses by month
        costs_by_month = Costs.objects.filter(
            organization=organization,
            date__range=[start_datetime, end_datetime]
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        articles_costs_by_month = Article.objects.filter(
            organization=organization,
            date__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('costs')
        ).order_by('month')
        
        # Convert to dictionaries for easy lookup
        def _month_key(m):
            # TruncMonth may return a date or datetime; normalize to a date with day=1
            if hasattr(m, "date"):
                m_date = m.date()
            else:
                m_date = m
            return m_date.replace(day=1)

        payments_dict = {_month_key(item['month']): float(item['total'] or 0) for item in payments_by_month}
        added_payments_dict = {_month_key(item['month']): float(item['total'] or 0) for item in added_payments_by_month}
        articles_income_dict = {_month_key(item['month']): float(item['total'] or 0) for item in articles_income_by_month}
        costs_dict = {_month_key(item['month']): float(item['total'] or 0) for item in costs_by_month}
        articles_costs_dict = {_month_key(item['month']): float(item['total'] or 0) for item in articles_costs_by_month}
        
        # Generate all months in range
        monthly_data = []
        current_date = start_date.replace(day=1)
        month_names = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                      'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
        
        while current_date <= end_date:
            # Get income for this month
            income = (
                payments_dict.get(current_date, 0.0) +
                added_payments_dict.get(current_date, 0.0) +
                articles_income_dict.get(current_date, 0.0)
            )
            
            # Get expenses for this month
            expenses = (
                costs_dict.get(current_date, 0.0) +
                articles_costs_dict.get(current_date, 0.0)
            )
            
            # Add rent if applicable
            if organization.datepay and organization.rent_amount:
                # Check if rent is due this month
                rent_date = organization.datepay
                while rent_date.replace(day=1) <= current_date:
                    if rent_date.replace(day=1) == current_date:
                        expenses += float(organization.rent_amount)
                        break
                    # Move to next month
                    days_in_month = monthrange(rent_date.year, rent_date.month)[1]
                    rent_date += timedelta(days=days_in_month)
                    if rent_date.replace(day=1) > current_date:
                        break
            
            # Add staff salaries if applicable
            staff_members = Staff.objects.filter(organization=organization)
            for staff in staff_members:
                # Check if salary is due this month
                salary_date = staff.started.replace(day=1) if hasattr(staff.started, 'replace') else staff.started
                while salary_date <= current_date:
                    if salary_date == current_date:
                        expenses += float(staff.salary)
                        break
                    # Move to next month
                    if salary_date.month == 12:
                        salary_date = salary_date.replace(year=salary_date.year + 1, month=1)
                    else:
                        salary_date = salary_date.replace(month=salary_date.month + 1)
                    if salary_date > current_date:
                        break
            
            monthly_data.append({
                'month': month_names[current_date.month - 1],
                'year': current_date.year,
                'income': income,
                'expenses': expenses,
                'net': round(income - expenses, 2),
            })
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return JsonResponse({
            'success': True,
            'monthly_data': monthly_data
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
    

@login_required
@require_organization
@require_http_methods(["GET"])
def api_daily_breakdown(request):
    """
    JSON API: Daily breakdown of income and expenses within a date range
    Intended mainly for single-month selection (day-by-day chart)
    """
    organization = request.organization

    start = request.GET.get('start')
    end = request.GET.get('end')

    if not start or not end:
        return JsonResponse({'success': False, 'error': 'Missing start/end'}, status=400)

    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()

        # timezone-aware for DateTimeField
        start_dt = make_aware(datetime.combine(start_date, datetime.min.time()))
        end_dt = make_aware(datetime.combine(end_date, datetime.max.time()))

        # --- INCOME ---
        # Payments: paymentdate is DateField
        payments = Payments.objects.filter(
            organization=organization,
            paymentdate__range=[start_date, end_date]
        ).values('paymentdate').annotate(total=Sum('paymentAmount'))

        payments_dict = {p['paymentdate']: float(p['total'] or 0) for p in payments}

        # Addedpay: date is DateTimeField
        added = Addedpay.objects.filter(
            organization=organization,
            date__range=[start_dt, end_dt]
        ).values('date__date').annotate(total=Sum('amount'))

        added_dict = {a['date__date']: float(a['total'] or 0) for a in added}

        # Articles income: date is DateField
        articles_income = Article.objects.filter(
            organization=organization,
            date__range=[start_date, end_date]
        ).values('date').annotate(total=Sum('participetion_price'))

        articles_income_dict = {x['date']: float(x['total'] or 0) for x in articles_income}

        # --- EXPENSES ---
        costs = Costs.objects.filter(
            organization=organization,
            date__range=[start_dt, end_dt]
        ).values('date__date').annotate(total=Sum('amount'))

        costs_dict = {c['date__date']: float(c['total'] or 0) for c in costs}

        articles_costs = Article.objects.filter(
            organization=organization,
            date__range=[start_date, end_date]
        ).values('date').annotate(total=Sum('costs'))

        articles_costs_dict = {x['date']: float(x['total'] or 0) for x in articles_costs}

        # Generate all days in range
        daily_data = []
        d = start_date
        while d <= end_date:
            income = (
                payments_dict.get(d, 0.0) +
                added_dict.get(d, 0.0) +
                articles_income_dict.get(d, 0.0)
            )
            expenses = (
                costs_dict.get(d, 0.0) +
                articles_costs_dict.get(d, 0.0)
            )

            daily_data.append({
                'date': d.strftime('%Y-%m-%d'),
                'day': d.day,
                'income': round(income, 2),
                'expenses': round(expenses, 2),
                'net': round(income - expenses, 2),
            })
            d += timedelta(days=1)

        return JsonResponse({'success': True, 'daily_data': daily_data})

    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)