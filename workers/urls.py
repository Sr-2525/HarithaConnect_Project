# workers/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication paths
    path('login/', views.worker_login, name='worker_login'),
    path('logout/', views.worker_logout, name='worker_logout'),

    # Dashboard and Core Worker Pages
    path('dashboard/', views.worker_dashboard, name='worker_dashboard'),

    # Use Case 4: Update Collection Status (Clearing an assignment)
    path('update-collection/<int:assignment_id>/', views.update_collection_status, name='update_collection_status'),

    # Use Case 6: Worker Raises Complaint
    path('raise-field-issue/', views.raise_field_issue, name='raise_field_issue'),

    # Confirmation of offline payments (from Resident Use Case 2)
    path('confirm-payment/', views.confirm_offline_payment, name='confirm_offline_payment'),

    path('history/', views.worker_history, name='worker_history'),

    path('alert-detail/<int:alert_id>/', views.alert_detail_action, name='alert_detail_action'), # <-- NEW PATH

]