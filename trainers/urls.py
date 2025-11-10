from django.urls import path,include
from . import views

urlpatterns = [ 
    path('', views.Home, name='home'),
    #Trainees
    path('olders/<str:category>', views.trainees, name='trainees'),
    path('profile/<int:id>', views.trainee_profile, name='profile'),
    path('add_trainee', views.add_trainee, name='add_trainee'),
    path('register/<slug:org_slug>/', views.addme, name='addme'),
    path('register/<slug:org_slug>/done/', views.addmedone, name='done'),
    path('add_women', views.add_trainee, name='add_women'),
    path('edit_trainee/<int:id>', views.edit_trainee, name='edit_trainee'),
    path("delete_trainer/<int:id>/", views.delete_trainer_view, name="delete_trainer"),
    #payments
    path('add_payment', views.add_payment, name='add_payment'),
    path('added_payment/', views.added_payment, name='added_payment'),
    path('added_payments_history/', views.added_payments_history, name='added_payments_history'),
    path('delete_pay/<int:id>', views.delete_pay, name='delete_pay'),
    path('payments_history/', views.payments_history, name='payments_history'),
    path('payments_del/<int:id>', views.payments_del, name='delete_payment'),
    path('payment_edit/<int:id>', views.payment_edit, name='edit_payment'),
    #JAWAZ
    path('add_article', views.add_article, name='add_article'),
    path('articles/<str:category>', views.articles, name='articles'),
    path('article/<int:id>', views.article_details, name='article_detail'),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('edit_article/<int:id>', views.edit_article, name='edit_article'),
    path('delete_article/<int:id>', views.remove_article, name='delete_article'),
    #Financial
    path('finantial_status/',views.finantial_status,name='finantial_status'),
    path('add_expenses/',views.add_expenses,name='add_expenses'),
    path('expenses_history/',views.expenses_history,name='expenses_history'),
    path('expenses_del/<int:id>',views.delete_expense,name='delete_cost'),
    path('add_payments/',views.add_payments,name='add_payments'),
    #Staff managing
    path("add_staff/",views.add_staff,name="add_staff") ,
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/edit/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('staff/delete/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('organization/edit/', views.edit_organization, name='edit_organization'),
    #login
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    #emails
    path('emails/', views.emails, name='emails'),
    #success
    path('success/', views.success, name='success'),
    #DATA Download
    path('export_data/<str:category>', views.export_data, name='export_data'),
    #Data upload
    path('upload_data/', views.upload_trainers_excel, name='upload_data'),
    path('upload_payments',views.upload_payments_excel, name='upload_payments'),
    path('unpaid_trainees/', views.unpaid_trainees, name='unpaid_trainees'),
    #Download reports,
    path('trainees_report/', views.download_documents, name='trainees_report'),
    path("export-xls/", views.export_xls, name="export_xls"),
    # Add this new URL pattern for bulk deactivation
    path('bulk-deactivate-trainers/', views.bulk_deactivate_trainers, name='bulk_deactivate_trainers'),

    path('setup_organization/', views.signup, name='setup_organization'),
    
]
