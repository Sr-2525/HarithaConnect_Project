

from django.urls import path
from . import views

urlpatterns = [
    # 1. AUTHENTICATION ENTRY POINT (Must be first for clean flow)

    path('login/', views.admin_login, name='admin_login'),
    # 2. MAIN MONITORING DASHBOARD (The root of the app: /dashboard-admin/)
    path('', views.admin_monitoring_dashboard, name='admin_monitoring_dashboard'),
    
    # 3. MANAGEMENT WORKFLOWS
    path('ward-management/', views.ward_assignment_management, name='ward_assignment_management'), 
    path('generate-schedule/', views.generate_monthly_schedule, name='generate_monthly_schedule'), 
    path('assign-daily/', views.assign_daily_task, name='assign_daily_task'),
    
    # 4. RESOLUTION & FINANCIAL ACTIONS
    path('priority-pickup/', views.priority_pickup_management, name='priority_pickup_management'),
    path('complaint-resolution/', views.complaint_resolution, name='complaint_resolution'),
    path('unconfirmed-payments/', views.unconfirmed_payments_manager, name='unconfirmed_payments_manager'), 
    path('overdue-bills-manager/', views.overdue_bills_manager, name='overdue_bills_manager'), 
    path('monthly-report/', views.monthly_report, name='monthly_report'),
]