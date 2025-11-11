def staff_context(request):
    """
    Add staff information to template context
    This makes it easier to check permissions in templates
    """
    context = {
        'is_admin': False,
        'staff_member': None,
    }
    
    if request.user.is_authenticated:
        try:
            staff = request.user.staff
            context['is_admin'] = staff.is_admin
            context['staff_member'] = staff
        except:
            # User has no staff record
            pass
    
    return context