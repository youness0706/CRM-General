from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from trainers.models import *
from django.utils import timezone
from django.utils.html import format_html

class OrganizationFilter(admin.SimpleListFilter):
    """Filter by organization for superusers"""
    title = 'Organization'
    parameter_name = 'organization'

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return [(org.id, org.name) for org in OrganizationInfo.objects.all()]
        return []

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(organization_id=self.value())
        return queryset


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'subscription_tier', 'created_at']
    list_filter = ['is_active', 'subscription_tier']
    search_fields = ['name', 'slug', 'email']
    prepopulated_fields = {'slug': ('name',)}
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Regular staff can only see their organization
        try:
            staff = Staff.objects.get(user=request.user)
            return qs.filter(id=staff.organization.id)
        except Staff.DoesNotExist:
            return qs.none()


class BaseOrganizationAdmin(admin.ModelAdmin):
    """Base admin for models with organization field"""
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            staff = Staff.objects.get(user=request.user)
            return qs.filter(organization=staff.organization)
        except Staff.DoesNotExist:
            return qs.none()
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set organization on creation
            try:
                staff = Staff.objects.get(user=request.user)
                obj.organization = staff.organization
            except Staff.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)
    
    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if request.user.is_superuser:
            filters.insert(0, OrganizationFilter)
        return filters


class TrainerAdmin(BaseOrganizationAdmin):
    list_display = ['full_name', 'category', 'belt_degree', 'age', 'is_active', 'started_day']
    list_filter = ['is_active', 'category', 'male_female', 'belt_degree']
    search_fields = ['first_name', 'last_name', 'email', 'CIN']
    readonly_fields = ['age']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'birth_day', 'age', 'male_female', 'image')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'phone_parent', 'address', 'CIN')
        }),
        ('Training Information', {
            'fields': ('category', 'belt_degree', 'Degree', 'tall', 'weight', 'started_day', 'is_active')
        }),
    )


class PaymentsAdmin(BaseOrganizationAdmin):
    list_display = ['trainer', 'paymentCategry', 'paymentAmount', 'paymentdate']
    list_filter = ['paymentCategry', 'paymentdate']
    search_fields = ['trainer__first_name', 'trainer__last_name']
    date_hierarchy = 'paymentdate'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('trainer', 'organization')


class ArticleAdmin(BaseOrganizationAdmin):
    list_display = ['title', 'category', 'area', 'date', 'costs', 'participetion_price']
    list_filter = ['category', 'area', 'date']
    search_fields = ['title', 'location']
    filter_horizontal = ['trainees']
    date_hierarchy = 'date'


class CostsAdmin(BaseOrganizationAdmin):
    list_display = ['cost', 'amount', 'date', 'is_recurring']
    list_filter = ['is_recurring', 'date']
    search_fields = ['cost', 'desc']
    date_hierarchy = 'date'


class AddedpayAdmin(BaseOrganizationAdmin):
    list_display = ['title', 'amount', 'date']
    list_filter = ['date']
    search_fields = ['title', 'desc']
    date_hierarchy = 'date'


class StaffAdmin(BaseOrganizationAdmin):
    list_display = ['user', 'organization', 'role', 'is_admin', 'salary', 'started']
    list_filter = ['is_admin', 'started']
    search_fields = ['user__username', 'user__email', 'role']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'organization')


class EmailedAdmin(BaseOrganizationAdmin):
    list_display = ['user', 'category', 'datetime', 'sent_successfully']
    list_filter = ['category', 'sent_successfully', 'datetime']
    search_fields = ['user__first_name', 'user__last_name', 'email']
    date_hierarchy = 'datetime'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'organization')

@admin.register(OrganizationPayment)
class OrganizationPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'organization',
        'payment_date',
        'amount_display',
        'duration_months',
        'subscription_period',
        'payment_method',
        'processed_by'
    ]
    list_filter = [
        'payment_date',
        'payment_method',
        'duration_months',
        'organization'
    ]
    search_fields = [
        'organization__name',
        'notes'
    ]
    readonly_fields = [
        'subscription_start',
        'subscription_end',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('معلومات الدفع', {
            'fields': (
                'organization',
                'payment_date',
                'amount',
                'duration_months',
                'payment_method',
            )
        }),
        ('تفاصيل الاشتراك (تلقائي)', {
            'fields': (
                'subscription_start',
                'subscription_end',
            ),
            'classes': ('collapse',)
        }),
        ('معلومات إضافية', {
            'fields': (
                'notes',
                'processed_by',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def amount_display(self, obj):
        return f"{obj.amount} ريال"
    amount_display.short_description = "المبلغ"
    
    def subscription_period(self, obj):
        if obj.subscription_start and obj.subscription_end:
            return f"{obj.subscription_start} → {obj.subscription_end}"
        return "-"
    subscription_period.short_description = "فترة الاشتراك"
    
    def save_model(self, request, obj, form, change):
        if not obj.processed_by:
            obj.processed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(OrganizationInfo)
class OrganizationInfoAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'slug',
        'subscription_status_display',
        'days_remaining_display',
        'subscription_period_display',
        'trainer_count',
        'is_active'
    ]
    list_filter = [
        'is_active',
        'subscription_tier',
        'subscription_end_date'
    ]
    search_fields = [
        'name',
        'slug',
        'email'
    ]
    readonly_fields = [
        'subscription_status_display',
        'days_remaining_display',
        'created_at'
    ]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': (
                'name',
                'slug',
                'description',
                'email',
                'phone_number',
                'location',
            )
        }),
        ('معلومات الاشتراك', {
            'fields': (
                'subscription_tier',
                'subscription_start_date',
                'subscription_end_date',
                'grace_period_days',
                'is_active',
                'subscription_status_display',
                'days_remaining_display',
            )
        }),
        ('إعدادات', {
            'fields': (
                'max_trainers',
                'rent_amount',
                'datepay',
            )
        }),
        ('معلومات إضافية', {
            'fields': (
                'established_date',
                'created_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_organizations', 'deactivate_organizations', 'check_expiration']
    
    def subscription_status_display(self, obj):
        status = obj.get_subscription_status_display()
        colors = {
            'success': '#28a745',
            'info': '#17a2b8',
            'warning': '#ffc107',
            'danger': '#dc3545'
        }
        color = colors.get(status['class'], '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            status['text']
        )
    subscription_status_display.short_description = "حالة الاشتراك"
    
    def days_remaining_display(self, obj):
        days = obj.days_until_expiration
        if days is None:
            return "-"
        elif days > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{} يوم</span>',
                days
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">متأخر {} يوم</span>',
                abs(days)
            )
    days_remaining_display.short_description = "الأيام المتبقية"
    
    def subscription_period_display(self, obj):
        if obj.subscription_start_date and obj.subscription_end_date:
            return f"{obj.subscription_start_date} → {obj.subscription_end_date}"
        return "-"
    subscription_period_display.short_description = "فترة الاشتراك"
    
    def trainer_count(self, obj):
        count = obj.trainers.filter(is_active=True).count()
        return f"{count} / {obj.max_trainers}"
    trainer_count.short_description = "عدد المتدربين"
    
    def activate_organizations(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"تم تفعيل {updated} جمعية")
    activate_organizations.short_description = "تفعيل الجمعيات المختارة"
    
    def deactivate_organizations(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"تم إلغاء تفعيل {updated} جمعية")
    deactivate_organizations.short_description = "إلغاء تفعيل الجمعيات المختارة"
    
    def check_expiration(self, request, queryset):
        expired_count = 0
        for org in queryset:
            if org.is_expired():
                org.is_active = False
                org.save()
                expired_count += 1
        
        self.message_user(
            request,
            f"تم فحص {queryset.count()} جمعية. تم إلغاء تفعيل {expired_count} جمعية منتهية"
        )
    check_expiration.short_description = "فحص الاشتراكات المنتهية"


# Custom Admin Dashboard
class SubscriptionAdminSite(admin.AdminSite):
    site_header = "إدارة اشتراكات الجمعيات"
    site_title = "إدارة الاشتراكات"
    index_title = "لوحة تحكم الاشتراكات"
    
    def index(self, request, extra_context=None):
        from django.db.models import Count, Sum, Q
        from datetime import timedelta
        
        today = timezone.now().date()
        
        # Statistics
        total_orgs = OrganizationInfo.objects.count()
        active_orgs = OrganizationInfo.objects.filter(is_active=True).count()
        
        # Expiring soon (next 30 days)
        expiring_soon = OrganizationInfo.objects.filter(
            subscription_end_date__lte=today + timedelta(days=30),
            subscription_end_date__gte=today
        ).count()
        
        # Expired
        expired = OrganizationInfo.objects.filter(
            subscription_end_date__lt=today
        ).count()
        
        # Recent payments (last 30 days)
        recent_payments = OrganizationPayment.objects.filter(
            payment_date__gte=today - timedelta(days=30)
        )
        
        total_revenue = recent_payments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Organizations needing attention
        needs_attention = OrganizationInfo.objects.filter(
            Q(subscription_end_date__lte=today + timedelta(days=7)) |
            Q(subscription_end_date__lt=today)
        ).order_by('subscription_end_date')[:10]
        
        extra_context = extra_context or {}
        extra_context.update({
            'total_orgs': total_orgs,
            'active_orgs': active_orgs,
            'expiring_soon': expiring_soon,
            'expired': expired,
            'total_revenue': total_revenue,
            'needs_attention': needs_attention,
        })
        
        return super().index(request, extra_context)


# Register models
admin.site.register(Trainer, TrainerAdmin)
admin.site.register(Payments, PaymentsAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(Costs, CostsAdmin)
admin.site.register(Addedpay, AddedpayAdmin)
admin.site.register(Staff, StaffAdmin)
admin.site.register(Emailed, EmailedAdmin)

# Customize admin site
admin.site.site_header = 'نجوم أركانة - إدارة النظام'
admin.site.site_title = 'إدارة النظام'
admin.site.index_title = 'لوحة التحكم'