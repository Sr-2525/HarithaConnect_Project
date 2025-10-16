# residents/admin.py
from django.contrib import admin
from .models import ResidentProfile, BinFullAlert, ResidentComplaint, Payment, BillingDue

# --- Customizing ResidentProfile Admin ---
class ResidentProfileAdmin(admin.ModelAdmin):
    list_display = ('household_id', 'user', 'ward_number')
    search_fields = ('household_id', 'user__username', 'ward_number')
    list_filter = ('ward_number',)

# --- Customizing BinFullAlert Admin ---
class BinFullAlertAdmin(admin.ModelAdmin):
    list_display = ('resident', 'status', 'alert_time', 'worker_assigned')
    list_filter = ('status', 'alert_time')
    search_fields = ('resident__household_id', 'location_detail')

    # Fields that the Admin CANNOT change after submission
    readonly_fields = ('resident', 'alert_time', 'photo_proof', 'location_detail') 
    
    # Fields that the Admin CAN change (for resolution)
    fields = ('resident', 'alert_time', 'photo_proof', 'location_detail', 'status', 'worker_assigned')


    actions = ['mark_as_cleared']
    def mark_as_cleared(self, request, queryset):
        queryset.update(status='CLEARED')
    mark_as_cleared.short_description = "Mark selected alerts as Cleared"


# --- Customizing ResidentComplaint Admin ---
class ResidentComplaintAdmin(admin.ModelAdmin):
    list_display = ('resident', 'complaint_type', 'status', 'submission_time')
    list_filter = ('status', 'complaint_type')
    search_fields = ('resident__household_id', 'details')
    
    # Fields the Admin CANNOT change (Resident's original submission)
    readonly_fields = ('resident', 'complaint_type', 'details', 'proof_file', 'submission_time')
    
    # Fields the Admin CAN change (for resolution)
    fieldsets = (
        ('Resident Submission Details (Read-Only)', {
            'fields': ('resident', 'complaint_type', 'details', 'proof_file', 'submission_time')
        }),
        ('Resolution and Tracking', {
            'fields': ('status', 'resolution_notes') # Admin updates status and adds notes
        }),
    )
    


# residents/admin.py (Add the admin class)

class BillingDueAdmin(admin.ModelAdmin):
    list_display = ('resident', 'amount_due', 'billed_date', 'due_date', 'is_paid')
    list_filter = ('is_paid', 'billed_date')
    search_fields = ('resident__household_id',)


# --- Customizing Payment Admin ---
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('resident', 'amount', 'is_paid_online', 'payment_date', 'receipt_number', 'worker_who_received_cash')
    list_filter = ('is_paid_online', 'payment_date')
    search_fields = ('resident__household_id', 'receipt_number')

    # Fields the Admin CANNOT change (Record of the transaction)
    readonly_fields = ('resident', 'amount', 'payment_date', 'receipt_number', 'is_paid_online')
    
    # Fields the Admin CAN change (Only who received the cash)
    fields = ('resident', 'amount', 'payment_date', 'receipt_number', 'is_paid_online', 'worker_who_received_cash')


# --- Re-register the Models with the Custom Admin Classes ---

# Ensure these lines are at the end of residents/admin.py
admin.site.register(ResidentProfile, ResidentProfileAdmin)
admin.site.register(BinFullAlert, BinFullAlertAdmin)
# Update registration to use the new custom classes
admin.site.register(ResidentComplaint, ResidentComplaintAdmin) 
admin.site.register(Payment, PaymentAdmin)
admin.site.register(BillingDue, BillingDueAdmin)
