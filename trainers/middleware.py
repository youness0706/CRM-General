from django.shortcuts import redirect, render
from django.urls import reverse
from .models import Staff
from functools import wraps
from django.contrib import messages
from django.utils import timezone

class OrganizationMiddleware:
    """
    Middleware to attach organization and staff to request based on logged-in user
    NOW WITH SUBSCRIPTION EXPIRATION CHECKING
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.staff = None
        request.subscription_status = None  # NEW
        
        if request.user.is_authenticated:
            try:
                # Get staff record for user
                staff = Staff.objects.select_related('organization').get(user=request.user)
                request.organization = staff.organization
                request.staff = staff
                
                # Check subscription status
                organization = staff.organization
                
                # Update organization status if expired
                organization.check_and_update_status()
                
                # Get detailed subscription status
                request.subscription_status = organization.get_subscription_status_display()
                days_left = organization.days_until_expiration()
                
                # Allowed URLs even when expired
                allowed_urls = [
                    reverse('login'),
                    reverse('logout'),
                    '/admin/',
                    reverse('subscription_expired'),  # Add this view
                    reverse('edit_organization'),  # Allow org owner to see info
                ]
                
                # Check if we should allow access
                is_allowed_path = any(request.path.startswith(url) for url in allowed_urls)
                
                # If organization is expired (past grace period)
                if organization.is_expired() and not is_allowed_path:
                    return render(request, 'pages/subscription_expired.html', {
                        'organization': organization,
                        'days_overdue': abs(days_left) if days_left else 0,
                        'subscription_status': request.subscription_status
                    })
                
                # If subscription expiring soon, show warning (but allow access)
                if days_left is not None and 0 < days_left <= 7 and staff.is_admin:
                    messages.warning(
                        request,
                        f'⚠️ تحذير: اشتراك الجمعية سينتهي خلال {days_left} يوم!'
                    )
                
                # If in grace period, show error (but allow access)
                if organization.is_in_grace_period() and staff.is_admin:
                    messages.error(
                        request,
                        f'🚨 تنبيه: اشتراك الجمعية منتهي منذ {abs(days_left)} يوم. يرجى التجديد قريباً!'
                    )
                        
            except Staff.DoesNotExist:
                # User has no organization
                print(f"DEBUG: Staff.DoesNotExist for user: {request.user.username}, ID: {request.user.id}")
                
                if not request.user.is_superuser:
                    # Skip check for certain URLs
                    allowed_urls = [
                        reverse('login'),
                        reverse('logout'),
                        reverse('setup_organization'),
                        '/admin/',
                        '/ajax/check_username/',
                        '/ajax/check_slug/',
                    ]
                    
                    # Allow access to public-facing org pages
                    if request.path.startswith('/org/'):
                         pass
                    elif not any(request.path.startswith(url) for url in allowed_urls):
                        return redirect('setup_organization')

        response = self.get_response(request)
        return response


def get_organization(request):
    """Get organization from request"""
    return getattr(request, 'organization', None)


def require_organization(view_func):
    """Decorator to ensure user has organization"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if organization was set by middleware
        if not hasattr(request, 'organization') or request.organization is None:
            print(f"DEBUG: require_organization failed for user: {request.user.username}")
            
            if request.user.is_authenticated and not request.user.is_superuser:
                messages.error(request, 'يجب أن تكون مرتبطاً بجمعية للوصول إلى هذه الصفحة')
                return redirect('setup_organization')
            elif request.user.is_superuser:
                messages.warning(request, 'يرجى إنشاء جمعية أو ربط حسابك بجمعية')
                return redirect('setup_organization')
            else:
                return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper
