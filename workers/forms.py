# workers/forms.py
from django import forms
from .models import CollectionAssignment, WorkerComplaint
from django.utils import timezone
from django.core.exceptions import ValidationError # <-- NEW IMPORT

MAX_UPLOAD_SIZE = 5242880

class CollectionUpdateForm(forms.ModelForm):
    # We only want the worker to upload the photo proof
    class Meta:
        model = CollectionAssignment
        fields = ['photo_proof']
        widgets = {
            'photo_proof': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def clean_photo_proof(self):
        photo = self.cleaned_data.get('photo_proof')
        if photo and photo.size > MAX_UPLOAD_SIZE:
            raise ValidationError(
                f"File size exceeds 5 MB limit. Actual size: {round(photo.size / 1048576, 2)} MB."
            )
        return photo
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['photo_proof'].required = True

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

    def clean_proof_file(self):
        proof = self.cleaned_data.get('proof_file')
        if proof:
            if proof.size > MAX_UPLOAD_SIZE:
                raise ValidationError(
                    f"File size exceeds 5 MB limit. Actual size: {round(proof.size / 1048576, 2)} MB."
                )
        return proof