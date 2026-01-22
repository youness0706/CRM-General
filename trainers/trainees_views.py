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
from .models import *
from datetime import datetime



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


# ==================== Trainee Profile View ====================
"""
Refactored Trainer Profile Views
High-performance with AJAX operations

"""
from django.shortcuts import render, get_object_or_404

@login_required
def trainee_profile(request, id):
    """
    Shell view - Returns minimal HTML template
    Data loaded via AJAX for better performance
    """
    organization = request.organization
    trainer = get_object_or_404(Trainer, pk=id, organization=organization)
    
    context = {
        'trainer': trainer,
        'trainer_id': id,
        'organization_slug': organization.slug,
    }
    return render(request, "pages/profile.html", context)


@login_required
@require_http_methods(["GET"])
def api_trainer_profile_data(request, id):
    """
    JSON API: Get all trainer profile data
    Optimized with select_related and prefetch_related
    """
    organization = request.organization
    
    try:
        # Get trainer with optimized query
        trainer = Trainer.objects.select_related('organization').get(
            pk=id, 
            organization=organization
        )
        
        # Get payments (optimized)
        payments = Payments.objects.filter(
            organization=organization,
            trainer_id=id
        ).order_by('paymentdate').values(
            'id', 'paymentdate', 'paymentCategry', 'paymentAmount'
        )
        
        # Get articles
        articles = Article.objects.filter(
            organization=organization,
            trainees=trainer
        ).values('id', 'title', 'date', 'location')
        
        # Get documents
        docs = TrainerDocument.objects.filter(
            trainer_id=id
        ).order_by('-uploaded_at').values(
            'id', 'document_type', 'uploaded_at', 'file'
        )
        
        # Calculate payment status
        payment_status = calculate_payment_status(payments)
        
        # Separate payments by category
        jawaz_payments = [p for p in payments if p['paymentCategry'] == 'jawaz']
        assurance_payments = [p for p in payments if p['paymentCategry'] == 'assurance']
        subscription_payments = [p for p in payments if p['paymentCategry'] == 'subscription']
        
        # Build response
        response_data = {
            'trainer': {
                'id': trainer.id,
                'first_name': trainer.first_name,
                'last_name': trainer.last_name,
                'cin': trainer.CIN,
                'birth_day': trainer.birth_day.isoformat() if trainer.birth_day else None,
                'age': trainer.age,
                'email': trainer.email,
                'phone': trainer.phone,
                'phone_parent': trainer.phone_parent,
                'address': trainer.address,
                'degree': trainer.Degree,
                'tall': float(trainer.tall) if trainer.tall else None,
                'weight': float(trainer.weight) if trainer.weight else None,
                'started_day': trainer.started_day.isoformat() if trainer.started_day else None,
                'category': trainer.get_category_display(),
                'belt_degree': trainer.belt_degree,
                'is_active': trainer.is_active,
                'image_url': trainer.image.url if trainer.image else None,
            },
            'payments': {
                'jawaz': [
                    {
                        'id': p['id'],
                        'date': p['paymentdate'].isoformat(),
                        'amount': float(p['paymentAmount'])
                    }
                    for p in jawaz_payments
                ],
                'assurance': [
                    {
                        'id': p['id'],
                        'date': p['paymentdate'].isoformat(),
                        'amount': float(p['paymentAmount'])
                    }
                    for p in assurance_payments
                ],
                'subscription': [
                    {
                        'id': p['id'],
                        'date': p['paymentdate'].isoformat(),
                        'amount': float(p['paymentAmount'])
                    }
                    for p in subscription_payments
                ],
                'monthly_status': payment_status
            },
            'articles': [
                {
                    'id': article['id'],
                    'title': article['title'],
                    'date': article['date'].isoformat(),
                    'location': article['location']
                }
                for article in articles
            ],
            'documents': [
                {
                    'id': doc['id'],
                    'type': doc['document_type'],
                    'uploaded_at': doc['uploaded_at'].isoformat(),
                    'file_url': doc['file']
                }
                for doc in docs
            ]
        }
        
        return JsonResponse(response_data)
        
    except Trainer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'المتدرب غير موجود'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def calculate_payment_status(payments):
    """Calculate monthly payment status"""
    payments_list = list(payments)
    
    if not payments_list:
        start_month = datetime(datetime.now().year, datetime.now().month, 1)
    else:
        first_payment = min(payments_list, key=lambda x: x['paymentdate'])
        first_date = first_payment['paymentdate']
        start_month = datetime(first_date.year, first_date.month, 1)
    
    # Generate months from first payment to current month
    current_month = datetime.now()
    months = []
    temp_month = start_month
    
    while temp_month <= current_month:
        months.append(temp_month.strftime("%Y-%m"))
        if temp_month.month == 12:
            temp_month = datetime(temp_month.year + 1, 1, 1)
        else:
            temp_month = datetime(temp_month.year, temp_month.month + 1, 1)
    
    # Track paid months
    paid_months = {
        p['paymentdate'].strftime("%Y-%m") 
        for p in payments_list 
        if p['paymentCategry'] == 'month'
    }
    
    # Prepare status list
    payment_status = [
        {
            "month": month, 
            "status": "paid" if month in paid_months else "unpaid"
        }
        for month in months
    ]
    
    return payment_status


@login_required
@require_http_methods(["POST"])
def api_add_payment_profile(request, id):
    """
    JSON API: Add payment(s) from profile page
    Supports multiple payment categories at once
    """
    organization = request.organization
    
    try:
        data = json.loads(request.body)
        payment_categories = data.get('categories', [])
        payment_date = data.get('date')
        
        if not payment_categories or not payment_date:
            return JsonResponse({
                'success': False,
                'error': 'الرجاء تحديد الفئات والتاريخ'
            }, status=400)
        
        # Get trainer
        trainer = Trainer.objects.get(pk=id, organization=organization)
        
        # Payment amounts by category
        PAYMENT_AMOUNTS = {
            'jawaz': 150,
            'assurance': 100,
            'subscription': 50,
            'month': 100
        }
        
        # Create payments
        created_payments = []
        for category in payment_categories:
            if category not in PAYMENT_AMOUNTS:
                continue
                
            payment = Payments.objects.create(
                organization=organization,
                trainer=trainer,
                paymentCategry=category,
                paymentAmount=PAYMENT_AMOUNTS[category],
                paymentdate=payment_date
            )
            
            created_payments.append({
                'id': payment.id,
                'category': category,
                'amount': float(payment.paymentAmount),
                'date': payment.paymentdate.isoformat()
            })
        
        # Clear cache
        today = timezone.now().date()
        cache_keys = [
            f'financial_summary_{organization.id}_{today}',
            f'chart_data_{organization.id}_{today}',
        ]
        cache.delete_many(cache_keys)
        
        return JsonResponse({
            'success': True,
            'message': f'تمت إضافة {len(created_payments)} دفعة بنجاح',
            'payments': created_payments
        })
        
    except Trainer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'المتدرب غير موجود'
        }, status=404)
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


@login_required
@require_http_methods(["POST"])
def api_upload_document(request, id):
    """
    JSON API: Upload trainer document
    """
    organization = request.organization
    
    try:
        trainer = Trainer.objects.get(pk=id, organization=organization)
        
        document_type = request.POST.get('document_type')
        document_file = request.FILES.get('document_file')
        
        if not document_type or not document_file:
            return JsonResponse({
                'success': False,
                'error': 'الرجاء اختيار نوع الوثيقة والملف'
            }, status=400)
        
        # Check file size (5MB max)
        if document_file.size > 5 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'error': 'حجم الملف يجب أن يكون أقل من 5MB'
            }, status=400)
        
        # Check if document type already exists
        existing_doc = TrainerDocument.objects.filter(
            trainer=trainer,
            document_type=document_type
        ).first()
        
        if existing_doc:
            # Update existing document
            existing_doc.file.delete()  # Delete old file
            existing_doc.file = document_file
            existing_doc.save()
            message = f'تم تحديث {document_type} بنجاح'
            doc_id = existing_doc.id
        else:
            # Create new document
            new_doc = TrainerDocument.objects.create(
                trainer=trainer,
                document_type=document_type,
                file=document_file
            )
            message = f'تم رفع {document_type} بنجاح'
            doc_id = new_doc.id
        
        return JsonResponse({
            'success': True,
            'message': message,
            'document': {
                'id': doc_id,
                'type': document_type,
                'file_url': request.build_absolute_uri(
                    TrainerDocument.objects.get(id=doc_id).file.url
                )
            }
        })
        
    except Trainer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'المتدرب غير موجود'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_delete_document(request, id):
    """
    JSON API: Delete trainer document
    """
    organization = request.organization
    
    try:
        data = json.loads(request.body)
        doc_id = data.get('doc_id')
        
        if not doc_id:
            return JsonResponse({
                'success': False,
                'error': 'معرف الوثيقة مطلوب'
            }, status=400)
        
        # Get trainer to verify organization
        trainer = Trainer.objects.get(pk=id, organization=organization)
        
        # Get and delete document
        doc = TrainerDocument.objects.get(id=doc_id, trainer=trainer)
        doc_type = doc.document_type
        
        # Delete file from storage
        doc.file.delete()
        # Delete database record
        doc.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'تم حذف {doc_type} بنجاح'
        })
        
    except Trainer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'المتدرب غير موجود'
        }, status=404)
    except TrainerDocument.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'الوثيقة غير موجودة'
        }, status=404)
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