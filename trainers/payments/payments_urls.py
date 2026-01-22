from django.urls import path
from .payments_views import *
from .invoice_views import *

urlpatterns = [
    path('payments_history/', payments_history, name='payments_history'),
    path('api/payments-list/', api_payments_list, name='api_payments_list'),
    path('api/bulk-delete-payments/', api_bulk_delete_payments, name='api_bulk_delete_payments'),
    path('api/trainers-for-payment/', api_trainers_for_payment, name='api_trainers_for_payment'),
    path('add_payment', add_payment, name='add_payment'),
    path('api/financial-report/', api_financial_report, name='api_financial_report'),
    path('api/monthly-breakdown/', api_monthly_breakdown, name='api_monthly_breakdown'),  
    path('api/daily-breakdown/', api_daily_breakdown, name='api_daily_breakdown'),
    path('finantial_status/',finantial_status,name='finantial_status'),


    path(
        'payment/<int:payment_id>/invoice/',
        download_payment_invoice,
        name='download_payment_invoice'
    ),
    
    # Preview route (optional - for development/debugging)
    path(
        'payment/<int:payment_id>/invoice/preview/',
        download_payment_invoice,
        name='preview_payment_invoice'
    ),
]