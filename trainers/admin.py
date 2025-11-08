from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from trainers.models import *


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


# Register models
admin.site.register(OrganizationInfo, OrganizationAdmin)
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