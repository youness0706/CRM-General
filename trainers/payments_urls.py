    
from django.urls import path
from .payments_views import *

urlpatterns = [
    path('payments_history/', payments_history, name='payments_history'),
    path('api/payments-list/', api_payments_list, name='api_payments_list'),
    path('api/bulk-delete-payments/', api_bulk_delete_payments, name='api_bulk_delete_payments'),
    path('api/trainers-for-payment/', api_trainers_for_payment, name='api_trainers_for_payment'),
    path('add_payment', add_payment, name='add_payment'),
    path('api/financial-report/', api_financial_report, name='api_financial_report'),
    path('finantial_status/',finantial_status,name='finantial_status'),



]