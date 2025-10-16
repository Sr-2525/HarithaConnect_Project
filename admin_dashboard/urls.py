

# admin_dashboard/urls.py (Verify/Update)
from django.urls import path
from . import views

urlpatterns = [
    # Main Monitoring Dashboard
    path('', views.admin_monitoring_dashboard, name='admin_monitoring_dashboard'),
    
    # Task Generation/Scheduling
    path('generate-schedule/', views.generate_monthly_schedule, name='generate_monthly_schedule'), 
    
    # CRITICAL FIX: Ward and Assignment Management Interface
    # Ensure this line is present with the correct name:
    path('ward-management/', views.ward_assignment_management, name='ward_assignment_management'), 
    
    # User Creation Interface
    path('user-onboard/', views.user_onboarding, name='user_onboarding'),
    
    # Custom Action Pages
    path('priority-pickup/', views.priority_pickup_management, name='priority_pickup_management'),
    path('complaint-resolution/', views.complaint_resolution, name='complaint_resolution'),
    path('assign-daily/', views.assign_daily_task, name='assign_daily_task'),
]