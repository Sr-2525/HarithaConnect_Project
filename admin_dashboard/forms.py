# admin_dashboard/forms.py (FINAL, CORRECTED VERSION)
from django import forms
# Note: models import must be outside class definitions if used statically, 
# but inside __init__ if used dynamically.
from workers.models import HKSWardAssignment 
from datetime import date
# from django.db.models import QuerySet # Removed unnecessary import

# ====================================================================
# A. Schedule Generation Form (For Monthly Route Automation)
# ====================================================================
class ScheduleGenerationForm(forms.Form):
    ward_id = forms.ChoiceField(
        choices=[],
        label="Select Ward to Schedule",
    )

    month = forms.IntegerField(
        label="Target Month (1-12)",
        min_value=1,
        max_value=12,
        initial=date.today().month,
    )

    year = forms.IntegerField(
        label="Target Year",
        min_value=2024,
        initial=date.today().year,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # FIX: Dynamic Query for Ward Choices
        # Fetch all configured wards from the HKS Assignment table
        ward_choices = [
            (a.ward_id, a.ward_id) 
            for a in HKSWardAssignment.objects.all().order_by('ward_id')
        ]
        
        # Add a default 'Select Ward' option at the start
        ward_choices.insert(0, ('', '--- Select a Ward ---'))
        
        self.fields['ward_id'].choices = ward_choices


# ====================================================================
# B. Daily Task Assignment Form (For One-Off Assignments)
# ====================================================================
class DailyTaskAssignmentForm(forms.Form):
    # Ward field is defined, choices are set dynamically in __init__
    ward = forms.ChoiceField(choices=[], label="Select Ward")
    
    target_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}), 
        label="Target Date"
    )

    house_start = forms.CharField(
        max_length=10, 
        label="Household Range Start (e.g., H1)"
    )
    house_end = forms.CharField(
        max_length=10, 
        label="Household Range End (e.g., H50)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # CRITICAL FIX: The logic was previously running statically; 
        # now it runs dynamically inside __init__.
        ward_choices = [
            (a.ward_id, a.ward_id) 
            for a in HKSWardAssignment.objects.all().order_by('ward_id')
        ]
        ward_choices.insert(0, ('', '--- Select Ward ---'))
        
        self.fields['ward'].choices = ward_choices


# ====================================================================
# C. User Onboarding Form (For Creating Workers/Supervisors)
# ====================================================================
# admin_dashboard/forms.py (Add this form)
# ... other forms ...

class UserOnboardingForm(forms.Form):
    # Django User fields
    username = forms.CharField(max_length=150, label="Username")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    email = forms.EmailField(required=False, label="Email")

    # Profile fields
    PROFILE_CHOICES = [
        ('WORKER', 'Field Worker'),
        ('SUPERVISOR', 'Supervisor'),
    ]
    profile_type = forms.ChoiceField(choices=PROFILE_CHOICES, label="Profile Type")
    
    # Worker/Supervisor Specific IDs
    profile_id = forms.CharField(max_length=50, required=True, label="Worker/Supervisor ID (e.g., WKR-101)")
    
    # Optional field for the worker's initial ward assignment
    ward_number = forms.CharField(max_length=10, required=False, label="Initial Ward Number (For Worker)")
    
    # Custom cleaning for profile_id to prevent duplicates across both tables
    def clean_profile_id(self):
        from workers.models import WorkerProfile, SupervisorProfile # Import inside method to avoid circular dependency

        profile_id = self.cleaned_data['profile_id']
        # Check if ID is already in use for either profile type
        if WorkerProfile.objects.filter(worker_id=profile_id).exists() or \
           SupervisorProfile.objects.filter(supervisor_id=profile_id).exists():
            raise forms.ValidationError("This Profile ID is already in use.")
        return profile_id











