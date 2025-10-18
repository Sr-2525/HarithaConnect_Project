# residents/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication paths
    # When user visits /residents/login/ run the views.resident_login function
    path('login/', views.resident_login, name='resident_login'),
    path('logout/', views.resident_logout, name='resident_logout'),

    # Dashboard and Core Resident Pages
    path('dashboard/', views.resident_dashboard, name='resident_dashboard'),

    # Use Case 1: Alert Bin Full
    path('alert-bin-full/', views.alert_bin_full, name='alert_bin_full'),

    # Use Case 2: Pay Waste Collection Fee
    path('pay-fee/', views.pay_waste_fee, name='pay_waste_fee'),

    # Use Case 3: Raise Complaint (We'll implement the logic next)
    path('raise-complaint/', views.raise_complaint, name='raise_complaint'),

    # History
    path('history/', views.resident_history, name='resident_history'),

    path('no-collection/', views.no_collection_request, name='no_collection_request'), # <-- NEW PATH
]