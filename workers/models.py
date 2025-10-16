from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import JSONField # Required for assigned_wards

# ----------------------------------------------------------------------
# 1. Worker Profile (Links the Django User to the Worker's details)
# ----------------------------------------------------------------------
class WorkerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    worker_id = models.CharField(max_length=50, unique=True)
    assigned_wards = JSONField(default=list) 

    def __str__(self):
        return self.worker_id

    class Meta:
        verbose_name_plural = "Worker Profiles"

# ----------------------------------------------------------------------
# 2. Supervisor Profile
# ----------------------------------------------------------------------
class SupervisorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    supervisor_id = models.CharField(max_length=50, unique=True)
    lsgi_area = models.CharField(max_length=100, default="LSGI Central") 

    def __str__(self):
        return f"Supervisor {self.supervisor_id} ({self.user.username})"

    class Meta:
        verbose_name_plural = "Supervisor Profiles"

# ----------------------------------------------------------------------
# 3. HKS Ward Assignment (The Core Mapping Table)
# ----------------------------------------------------------------------
class HKSWardAssignment(models.Model):
    ward_id = models.CharField(max_length=50, unique=True, help_text="The unique geographic ID of the Ward (e.g., LSGI-W05)")
    service_points_count = models.IntegerField(default=500, help_text="Number of households/service points in the ward.")
    
    # Foreign Keys link to the profiles
    worker1 = models.ForeignKey(
        WorkerProfile, 
        on_delete=models.RESTRICT, 
        related_name='primary_wards',
        help_text="Primary HKS member assigned to this ward."
    )
    
    worker2 = models.ForeignKey(
        WorkerProfile, 
        on_delete=models.RESTRICT, 
        related_name='secondary_wards',
        null=True, blank=True, 
        help_text="Secondary HKS member assigned to this ward."
    )

    supervisor = models.ForeignKey(
        SupervisorProfile, 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )

    def __str__(self):
        return f"Assignment for Ward {self.ward_id}"
        
    class Meta:
        verbose_name_plural = "HKS Ward Assignments"

# ----------------------------------------------------------------------
# 4. Collection Assignment and Status Update
# ----------------------------------------------------------------------
class CollectionAssignment(models.Model):
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE)
    assignment_date = models.DateField(default=timezone.now)
    collection_cycle_day = models.IntegerField(default=1, help_text="Day of the month's collection cycle (1-10).")
    household_id = models.CharField(max_length=50) 

    is_collected = models.BooleanField(default=False)
    collection_time = models.DateTimeField(null=True, blank=True)
    photo_proof = models.ImageField(upload_to='collection_proofs/', null=True, blank=True)

    def __str__(self):
        return f"Task for {self.household_id} by {self.worker.worker_id} on {self.assignment_date}"

    class Meta:
        unique_together = ('assignment_date', 'household_id')

# ----------------------------------------------------------------------
# 5. Worker Raises Complaint
# ----------------------------------------------------------------------
class WorkerComplaint(models.Model):
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE)

    ISSUE_CHOICES = [ 
        ('VEHICLE', 'Vehicle/Truck Breakdown'),
        ('ACCESS', 'Access/Lockout Issue'),
        ('SAFETY', 'Safety/Hazardous Waste'),
        ('ROUTE', 'Route/Mapping Problem'),
        ('OTHER', 'Other Field Issue'),
    ]

    issue_type = models.CharField(max_length=50, choices=ISSUE_CHOICES) 
    details = models.TextField()
    proof_file = models.FileField(upload_to='worker_complaint_proofs/', null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Pending Review'),
        ('RESOLVED', 'Resolved')
    ])
    submission_time = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Worker Complaint by {self.worker.worker_id} - {self.get_issue_type_display()}"