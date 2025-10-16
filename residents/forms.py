
    # residents/forms.py
from django import forms
from .models import BinFullAlert, ResidentComplaint, Payment

# Form for Use Case 1: Alert Bin is Full (Keep this one)
class BinFullAlertForm(forms.ModelForm):
    bin_location = forms.CharField(
        max_length=100, 
        label="Bin Location Detail",
        help_text="e.g., House Front, Backyard, Community Bin next to gate.",
        required=True
    )

    class Meta:
        model = BinFullAlert
        fields = ['photo_proof'] # 'bin_location' is a form-only field, not a model field
        widgets = {
            'photo_proof': forms.FileInput(attrs={'accept': 'image/*'}),
        }

# ------------------------------------------------------------------
# NEW: Form for Use Case 3: Raise Complaint
# ------------------------------------------------------------------
class ResidentComplaintForm(forms.ModelForm):
    class Meta:
        model = ResidentComplaint
        # Fields the resident needs to fill out
        fields = ['complaint_type', 'details', 'proof_file'] 
        widgets = {
            'details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the issue in detail...'}),
            # Accept images or videos for proof
            'proof_file': forms.FileInput(attrs={'accept': 'image/*,video/*'}),
        }

# ------------------------------------------------------------------
# NEW: Form for Offline Payment Reporting (Resident marks it)
# ------------------------------------------------------------------

class OfflinePaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        # List all fields that the resident submits
        fields = ['amount', 'receipt_number', 'receipt_photo'] 
        widgets = {
            'receipt_photo': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    # CRUCIAL: Use __init__ to explicitly enforce mandatory status on fields
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # These two lines ensure Django's validation throws an error if empty
        self.fields['receipt_photo'].required = True 
        self.fields['receipt_number'].required = True 