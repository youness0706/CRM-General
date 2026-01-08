from django.urls import path
from .trainees_views import *

urlpatterns = [
    # Trainees List APIs
    path('api/trainees-list/', api_trainees_list, name='api_trainees_list'),
    path('api/bulk-delete-trainers/', api_bulk_delete_trainers, name='api_bulk_delete_trainers'),
    path('olders/<str:category>', trainees, name='trainees'),
    path('non_active_trainees/', non_active_trainees, name='non_active_trainees'),
    path('bulk-activate-trainers/', bulk_activate_trainers, name='bulk_activate_trainers'),

]   