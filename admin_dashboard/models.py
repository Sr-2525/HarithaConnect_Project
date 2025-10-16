from django.db import models
from workers.models import WorkerProfile

class HKSWardAssignment(models.Model):
    """
    Model to statically assign one or two workers to a specific HKS Ward.
    This is an admin-configured model.
    """
    ward_id = models.CharField(max_length=20, unique=True, primary_key=True, help_text="e.g., HKS-W05")
    worker1 = models.ForeignKey(WorkerProfile, on_delete=models.SET_NULL, null=True, related_name='primary_ward_assignments')
    worker2 = models.ForeignKey(WorkerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='secondary_ward_assignments', help_text="Optional second worker for the ward")

    def __str__(self):
        worker2_name = f", {self.worker2.user.username}" if self.worker2 else ""
        return f"Ward {self.ward_id}: Assigned to {self.worker1.user.username}{worker2_name}"