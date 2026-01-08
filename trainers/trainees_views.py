"""
Refactored Views - Trainees List & Payments History
High-performance with bulk operations
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.cache import cache
from django.utils import timezone
import json
from .middleware import require_organization
from .models import Trainer


# ==================== TRAINEES LIST ====================

@login_required
@require_organization
def trainees(request, category):
    """
    Shell view - Returns minimal HTML template
    Data loaded via AJAX
    """
    organization = request.organization
    
    context = {
        'category': category,
        'organization_slug': organization.slug,
    }
    return render(request, 'pages/olders.html', context)


@login_required
@require_http_methods(["GET"])
def api_trainees_list(request):
    """
    JSON API: Get filtered/sorted trainees list
    Supports search, filtering, and sorting
    """
    organization = request.organization
    category = request.GET.get('category', 'all')
    
    # Base queryset with optimization
    trainers = Trainer.objects.filter(
        organization=organization,
        is_active=True
    ).only(
        'id', 'first_name', 'last_name', 'category', 
        'belt_degree', 'birth_day', 'image', 'male_female'
    )
    
    # Category filter
    if category != "all":
        trainers = trainers.filter(category=category)
    else:
        trainers = trainers.exclude(category="women")
    
    # Gender filter
    gender = request.GET.get('gender', '').strip()
    if gender:
        trainers = trainers.filter(male_female=gender)
    
    # Search filter
    search = request.GET.get('search', '').strip()
    if search:
        trainers = trainers.filter(
            Q(first_name__icontains=search) | 
            Q(last_name__icontains=search)
        )
    
    # Sorting
    order = request.GET.get('order', '')
    if order == 'first_first':
        trainers = trainers.order_by('-started_day')
    elif order == 'last_first':
        trainers = trainers.order_by('started_day')
    elif order == 'first_name':
        trainers = trainers.order_by('first_name', 'last_name')
    else:
        trainers = trainers.order_by('-started_day')  # Default
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    
    paginator = Paginator(trainers, per_page)
    page_obj = paginator.get_page(page)
    
    # Build response data
    trainers_data = []
    for trainer in page_obj:
        trainers_data.append({
            'id': trainer.id,
            'first_name': trainer.first_name,
            'last_name': trainer.last_name,
            'full_name': f"{trainer.first_name} {trainer.last_name}",
            'category': trainer.get_category_display(),
            'belt_degree': trainer.belt_degree,
            'age': trainer.age,
            'image_url': trainer.image.url if trainer.image else None,
        })
    
    return JsonResponse({
        'trainers': trainers_data,
        'total_count': paginator.count,
        'page': page_obj.number,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })


@login_required
@require_http_methods(["POST"])
def api_bulk_delete_trainers(request):
    """
    JSON API: Bulk delete (deactivate) trainers
    Actually sets is_active=False instead of deleting
    """
    try:
        data = json.loads(request.body)
        trainer_ids = data.get('trainer_ids', [])
        
        if not trainer_ids:
            return JsonResponse({
                'success': False,
                'error': 'لم يتم تحديد أي متدربين'
            }, status=400)
        
        # Soft delete - set is_active=False
        deleted_count = Trainer.objects.filter(
            id__in=trainer_ids,
            organization=request.organization
        ).update(is_active=False)
        
        # Clear cache
        today = timezone.now().date()
        cache_keys = [
            f'financial_summary_{request.organization.id}_{today}',
            f'chart_data_{request.organization.id}_{today}',
        ]
        cache.delete_many(cache_keys)
        
        return JsonResponse({
            'success': True,
            'message': f'تم حذف {deleted_count} متدرب بنجاح',
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
    

# ==================== NON-ACTIVE TRAINEES VIEW ====================

@login_required(login_url='/login/')
def non_active_trainees(request):
    trainers = Trainer.objects.filter(is_active=False, organization=request.organization)
    
    return render(request, 'pages/non_active_trainees.html', {'trainers':trainers,'number':trainers.count()})

@csrf_exempt
@require_POST
def bulk_activate_trainers(request):
    """
    View to handle bulk activation of trainers
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        trainer_ids = data.get('trainer_ids', [])

        if not trainer_ids:
            return JsonResponse({'success': False, 'error': 'No trainers selected'})

        # Update trainers to active
        updated_count = Trainer.objects.filter(
            id__in=trainer_ids,
            is_active=False
        ).update(is_active=True)

        return JsonResponse({
            'success': True,
            'message': f'تم تفعيل {updated_count} متدرب بنجاح',
            'activated_count': updated_count
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


