from django.urls import path
from . import views

# Namespace for URL patterns (Usage: {% url 'elog:name' %})
app_name = 'elog'

urlpatterns = [
    # 1. Dashboard (Entry Point)
    # URL: /e-logbook/
    path('', views.logbook_dashboard, name='logbook_dashboard'),

    # 2. Logbook Management
    # URL: /e-logbook/new-logbook/
    path('new-logbook/', views.logbook_create, name='logbook_create'),

    # 3. Log List (Inside a specific logbook)
    # URL: /e-logbook/1/
    path('<int:logbook_id>/', views.log_list, name='log_list'),

    # 4. Log Operations (Create, Edit, Delete)
    # URL: /e-logbook/1/create/
    path('<int:logbook_id>/create/', views.log_create, name='log_create'),
    
    # URL: /e-logbook/1/edit/10/
    path('<int:logbook_id>/edit/<int:log_id>/', views.log_edit, name='log_edit'),
    
    # URL: /e-logbook/1/delete/10/
    path('<int:logbook_id>/delete/<int:log_id>/', views.log_delete, name='log_delete'),

    # 5. Interaction & Export
    # URL: /e-logbook/1/comment/10/
    path('<int:logbook_id>/comment/<int:log_id>/', views.log_comment, name='log_comment'),
    
    # URL: /e-logbook/1/export/pdf/?date=2024-01-01
    path('<int:logbook_id>/export/pdf/', views.export_logs_pdf, name='export_logs_pdf'),

    path('signup/', views.signup, name='signup'),
]