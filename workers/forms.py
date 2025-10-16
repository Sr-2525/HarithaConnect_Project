# workers/forms.py
from django import forms
from .models import CollectionAssignment, WorkerComplaint
from django.utils import timezone

class CollectionUpdateForm(forms.ModelForm):
    # We only want the worker to upload the photo proof
    class Meta:
        model = CollectionAssignment
        fields = ['photo_proof']
        widgets = {
            'photo_proof': forms.FileInput(attrs={'accept': 'image/*'}),
        }

# ------------------------------------------------------------------
# NEW: Form for Worker Raising Complaint (Use Case 6)
# ------------------------------------------------------------------
class WorkerComplaintForm(forms.ModelForm):
    class Meta:
        model = WorkerComplaint
        fields = ['issue_type', 'details', 'proof_file']
        widgets = {
            'details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the field issue...'}),
            'proof_file': forms.FileInput(attrs={'accept': 'image/*,video/*'}),
        }