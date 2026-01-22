from django.urls import path
from . import index_views as views

urlpatterns = [
    path('', views.Home, name='home'),
    path('api/kpis/', views.api_kpis, name='api_kpis'),
    path('api/chart-data/', views.api_chart_data, name='api_chart_data'),
    path('api/payment-status/', views.api_payment_status, name='api_payment_status'),
    path('api/paid-today/', views.api_paid_today, name='api_paid_today'),
    path('api/bulk-deactivate/', views.bulk_deactivate_trainers, name='bulk_deactivate'),
]