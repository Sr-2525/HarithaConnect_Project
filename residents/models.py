# residents/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings # Used to reference the built-in User model

# ----------------------------------------------------------------------
# 1. Resident Profile (Links the Django User to the Resident's details)
# ----------------------------------------------------------------------
class ResidentProfile(models.Model):
    # A one-to-one link to Django's built-in User model for login/auth
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ward_number = models.CharField(max_length=10, help_text="The waste collection ward assigned by the Admin.")
    household_id = models.CharField(max_length=50, unique=True, help_text="Unique identifier for the household (e.g., Door No.)")
    address = models.TextField()

    def __str__(self):
        return f"Resident {self.household_id} ({self.user.username})"

    class Meta:
        verbose_name_plural = "Resident Profiles"

# ----------------------------------------------------------------------
# 2. Use Case 1: Bin Full Alert
# ----------------------------------------------------------------------
class BinFullAlert(models.Model):
    resident = models.ForeignKey(ResidentProfile, on_delete=models.CASCADE)
    alert_time = models.DateTimeField(default=timezone.now)
    # Storing the photo in the 'media/alert_proofs/' folder
    photo_proof = models.ImageField(upload_to='alert_proofs/', help_text="Upload photo proof (Max size: 5 MB).") 
    location_detail = models.CharField(max_length=100, default='Household Bin')
   
    STATUS_CHOICES = [
        ('PENDING', 'Pending Pickup'),
        ('ASSIGNED', 'Worker Assigned'),
        ('CLEARED', 'Bin Cleared')
    ]
    status = models.CharField(max_length=20, default='PENDING', choices=STATUS_CHOICES)

    # We will link this to the WorkerProfile model in the workers app later
    worker_assigned = models.ForeignKey('workers.WorkerProfile', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Alert from {self.resident.household_id} - Status: {self.status}"

# ----------------------------------------------------------------------
# 3. Use Case 3: Resident Complaint
# ----------------------------------------------------------------------
class ResidentComplaint(models.Model):
    resident = models.ForeignKey(ResidentProfile, on_delete=models.CASCADE)

    COMPLAINT_TYPES = [
        ('MISSED', 'Missed Collection'),
        ('BEHAVIOR', 'Rude Behaviour'),
        ('DELAY', 'Collection Delay'),
        ('OTHER', 'Other Issue')
    ]
    complaint_type = models.CharField(max_length=50, choices=COMPLAINT_TYPES)
    details = models.TextField()
    # Allows optional file upload (photo/video proof)
    proof_file = models.FileField(upload_to='complaint_proofs/', null=True, blank=True) 
    submission_time = models.DateTimeField(default=timezone.now)

    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved')
    ]
    status = models.CharField(max_length=20, default='PENDING', choices=STATUS_CHOICES)
    resolution_notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Complaint {self.id} - Type: {self.get_complaint_type_display()}"


# ----------------------------------------------------------------------
# 4. Use Case 2: Payment
# ----------------------------------------------------------------------
# residents/models.py (UPDATED Payment Model)
class Payment(models.Model):
    resident = models.ForeignKey(ResidentProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2) 
    payment_date = models.DateTimeField(default=timezone.now)
    is_paid_online = models.BooleanField(default=True, help_text="True for digital payment, False for cash.")

    # Receipt Number is no longer unique, as multiple workers might use similar manual receipts
    receipt_number = models.CharField(max_length=100, help_text="Transaction ID or Manual Receipt Number.")

    # NEW: Field for the photo proof of the receipt (required for offline payments)
    receipt_photo = models.ImageField(
        upload_to='payment_receipts/', 
        null=True, # Allow null initially
        help_text="Upload photo proof of the receipt (Max size: 5 MB).",
        blank=True # Allow blank initially, required in form only for offline
    )

    # This is the worker who CONFIRMED the transaction (either via a digital report or cash)
    worker_who_received_cash = models.ForeignKey(
        'workers.WorkerProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Worker who confirmed receipt of cash payment."
    )

    def __str__(self):
        return f"Payment by {self.resident.household_id} - ${self.amount}"

    def get_payment_status(self):
        # ... (keep this method as is) ...
        if self.is_paid_online:
            return 'Completed (Online)'
        elif self.worker_who_received_cash:
            return 'Completed (Cash Confirmed)'
        else:
            return 'Pending Worker Confirmation'

# ----------------------------------------------------------------------
# 5. Billing Dues (What the resident OWES)
# ----------------------------------------------------------------------
class BillingDue(models.Model):
    resident = models.ForeignKey(ResidentProfile, on_delete=models.CASCADE)
    amount_due = models.DecimalField(max_digits=6, decimal_places=2)
    billed_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Due for {self.resident.household_id} ({self.billed_date.month}/{self.billed_date.year})"

    class Meta:
        # Ensures a resident is only billed once for a given month/year
        unique_together = ('resident', 'billed_date')


# residents/models.py (Add this new model, preferably near BillingDue)

# --- No Collection Needed ---
class NoCollectionRequest(models.Model):
    resident = models.ForeignKey(ResidentProfile, on_delete=models.CASCADE)
    collection_month = models.IntegerField()
    collection_year = models.IntegerField()
    reason = models.CharField(
        max_length=100, 
        choices=[('VACATION', 'Away/Vacation'), ('LOW', 'Low Waste Volume'), ('OTHER', 'Other')],
        default='LOW'
    )
    submission_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"No Collection for {self.resident.household_id} ({self.collection_month}/{self.collection_year})"

    class Meta:
        # Crucial: Prevent double submissions for the same month
        unique_together = ('resident', 'collection_month', 'collection_year')