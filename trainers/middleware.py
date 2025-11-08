from django.shortcuts import redirect, render
from django.urls import reverse
from .models import Staff
from functools import wraps
from django.contrib import messages

class OrganizationMiddleware:
    """
    Middleware to attach organization and staff to request based on logged-in user
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.staff = None  # <-- ADDED
        
        if request.user.is_authenticated:
            try:
                # Get staff record for user
                staff = Staff.objects.select_related('organization').get(user=request.user)
                request.organization = staff.organization
                request.staff = staff  # <-- ADDED
                
                # Check if organization is active
                if not staff.organization.is_active:
                    # Skip check for certain URLs
                    allowed_urls = [
                        reverse('login'),
                        reverse('logout'),
                        '/admin/',
                    ]
                    
                    if not any(request.path.startswith(url) for url in allowed_urls):
                        # Redirect to subscription/payment page
                        return render(request, 'pages/subscription_expired.html')
                        
            except Staff.DoesNotExist:
                # User has no organization
                print(f"DEBUG: Staff.DoesNotExist for user: {request.user.username}, ID: {request.user.id}")
                print(f"DEBUG: Staff records in DB: {Staff.objects.filter(user_id=request.user.id).exists()}")
                
                if not request.user.is_superuser:
                    # Skip check for certain URLs
                    allowed_urls = [
                        reverse('login'),
                        reverse('logout'),
                        reverse('setup_organization'), # This now points to signup
                        '/admin/',
                        # Add any other public URLs (e.g., signup AJAX checks)
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
            
            # This check might be redundant if middleware handles redirection
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

# --- NEW DECORATOR ---
def admin_required(view_func):
    """
    Decorator to ensure user is an admin.
    Assumes @login_required and @require_organization have already run.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'staff') or not request.staff:
            # Fallback in case middleware didn't attach staff
            try:
                staff = Staff.objects.get(user=request.user)
                request.staff = staff
            except Staff.DoesNotExist:
                messages.error(request, 'حساب الموظف غير موجود.')
                return redirect('login')
        
        if not request.staff.is_admin:
            messages.error(request, 'ليس لديك صلاحيات المدير للوصول لهذه الصفحة.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper