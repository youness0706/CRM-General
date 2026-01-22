from django.urls import path
from .trainees_views import *

urlpatterns = [
    # Trainees List APIs
    path('api/trainees-list/', api_trainees_list, name='api_trainees_list'),
    path('api/bulk-delete-trainers/', api_bulk_delete_trainers, name='api_bulk_delete_trainers'),
    path('olders/<str:category>', trainees, name='trainees'),
    path('non_active_trainees/', non_active_trainees, name='non_active_trainees'),
    path('bulk-activate-trainers/', bulk_activate_trainers, name='bulk_activate_trainers'),
        # Trainer Profile
    path('profile/<int:id>/', trainee_profile, name='profile'),

    # Profile APIs (if doing full refactor)
    path('api/trainer/<int:id>/data/', api_trainer_profile_data, name='api_trainer_profile_data'),
    path('api/trainer/<int:id>/add-payment/', api_add_payment_profile, name='api_add_payment_profile'),
    path('api/trainer/<int:id>/upload-document/', api_upload_document, name='api_upload_document'),
    path('api/trainer/<int:id>/delete-document/', api_delete_document, name='api_delete_document'),
]   