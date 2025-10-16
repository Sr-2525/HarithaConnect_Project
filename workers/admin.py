# workers/admin.py

from django.contrib import admin, messages
from django import forms
from django.utils import timezone
from django.urls import reverse # NEW IMPORT: To get the URL for redirection
from django.http import HttpResponseRedirect # NEW IMPORT: For redirection
from .models import WorkerProfile, CollectionAssignment, WorkerComplaint, SupervisorProfile, HKSWardAssignment


# Define a custom form for the Admin to easily input multiple household IDs
class CollectionAssignmentForm(forms.ModelForm):
    household_ids = forms.CharField(
        widget=forms.Textarea, 
        label="Household IDs to Assign (One per line)",
        help_text="Enter the Household IDs (e.g., HRC-001) for today's collection, separated by a new line."
    )

    class Meta:
        model = CollectionAssignment
        fields = ['worker', 'assignment_date'] 

# --- WorkerProfileAdmin ---
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ('worker_id', 'user', 'get_assigned_wards')
    search_fields = ('worker_id', 'user__username')

    def get_assigned_wards(self, obj):
        return ", ".join(obj.assigned_wards)
    get_assigned_wards.short_description = 'Assigned Wards'
# -------------------------


# --- Customizing CollectionAssignment Admin (FIXED) ---
class CollectionAssignmentAdmin(admin.ModelAdmin):
    list_display = ('worker', 'household_id', 'assignment_date', 'is_collected', 'collection_time')
    list_filter = ('assignment_date', 'is_collected', 'worker')
    search_fields = ('worker__worker_id', 'household_id')

    form = CollectionAssignmentForm 

    def save_model(self, request, obj, form, change):
        # 1. Get the list of IDs from the Textarea, splitting by new line
        household_ids = form.cleaned_data['household_ids'].split('\n')

        # 2. Extract common data
        worker = form.cleaned_data['worker']
        assignment_date = form.cleaned_data['assignment_date']

        # 3. Create a CollectionAssignment object for EACH household ID
        new_assignments_count = 0
        for hid in household_ids:
            hid = hid.strip() # Remove any leading/trailing whitespace
            if hid:
                try:
                    # Check if this exact assignment already exists for the day
                    CollectionAssignment.objects.get(
                        worker=worker, 
                        assignment_date=assignment_date, 
                        household_id=hid
                    )
                except CollectionAssignment.DoesNotExist:
                    # If it doesn't exist, create it
                    CollectionAssignment.objects.create(
                        worker=worker,
                        assignment_date=assignment_date,
                        household_id=hid,
                        is_collected=False
                    )
                    new_assignments_count += 1

        if new_assignments_count > 0:
            messages.success(request, f"Successfully created {new_assignments_count} new assignments for {worker.worker_id}.")
        else:
            messages.warning(request, "No new assignments were created (they may already exist).")
            
        # *** CRUCIAL FIX: RETURN REDIRECT ***
        # Redirect the Admin back to the CollectionAssignment list page
        url = reverse('admin:workers_collectionassignment_changelist')
        return HttpResponseRedirect(url)


# --- Customizing Worker Complaint Admin ---
class WorkerComplaintAdmin(admin.ModelAdmin):
    list_display = ('worker', 'issue_type', 'status', 'submission_time')
    list_filter = ('status', 'issue_type')
    search_fields = ('worker__worker_id', 'details')

    readonly_fields = ('worker', 'issue_type', 'details', 'proof_file', 'submission_time')
    fields = ('worker', 'issue_type', 'details', 'proof_file', 'submission_time', 'status')

# --- Customizing Supervisor Profile Admin ---
class SupervisorProfileAdmin(admin.ModelAdmin):
    list_display = ('supervisor_id', 'user', 'lsgi_area')
    search_fields = ('supervisor_id', 'user__username')

# --- Customizing HKS Ward Assignment Admin ---
class HKSWardAssignmentAdmin(admin.ModelAdmin):
    list_display = ('ward_id', 'worker1', 'worker2', 'supervisor')
    list_filter = ('supervisor',)
    search_fields = ('ward_id', 'worker1__worker_id', 'worker2__worker_id', 'supervisor__supervisor_id')
    raw_id_fields = ('worker1', 'worker2', 'supervisor') # Makes selecting workers/supervisors easier


# --- Customizing Collection Assignment Admin (Read-Only) ---
# Note: I am renaming this class to avoid conflict since the one above is the final one
# I will use the final CollectionAssignmentAdmin defined above for registration.
# However, if you are using this class, ensure the readonly_fields are correct:

# If you were trying to use this version, ensure the readonly fields are correctly applied
# and then register the class above instead.


# --- Registration (Ensure these lines are updated/at the bottom) ---
admin.site.register(WorkerProfile, WorkerProfileAdmin)
admin.site.register(CollectionAssignment, CollectionAssignmentAdmin) 
admin.site.register(WorkerComplaint, WorkerComplaintAdmin)
admin.site.register(SupervisorProfile, SupervisorProfileAdmin)
admin.site.register(HKSWardAssignment, HKSWardAssignmentAdmin)
