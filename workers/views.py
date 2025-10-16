
# workers/views.py (at the top)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
# ADD THIS LINE:
from django.utils import timezone  # <-- This is the fix!
from .models import WorkerProfile, CollectionAssignment, WorkerComplaint
from .forms import CollectionUpdateForm, WorkerComplaintForm # <-- NEW IMPORT
from residents.models import BinFullAlert, ResidentComplaint, Payment

# --- Helper Function for Worker Check ---
# This prevents regular users from accessing worker paths
def is_worker(user):
    # The user must be logged in AND have an associated WorkerProfile
    return WorkerProfile.objects.filter(user=user).exists()

# --- 1. Authentication Views ---

# workers/views.py (UPDATED worker_login function)
def worker_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            try:
                # **CRUCIAL CHECK:** Only allow login if WorkerProfile exists
                profile = user.workerprofile 
                login(request, user)
                messages.success(request, f"Welcome, {user.username} (Worker ID: {profile.worker_id})")
                return redirect('worker_dashboard')
            except WorkerProfile.DoesNotExist:
                # Fail authentication if profile type does not match
                messages.error(request, "Access Denied. Your account is not registered as a Field Worker.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'workers/login.html')

@login_required(login_url='worker_login')
def worker_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('worker_login')

# --- 2. Dashboard View (Use Case 5: See daily assignment) ---
# workers/views.py (CORRECTED worker_dashboard function)
@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def worker_dashboard(request):
    worker_profile = request.user.workerprofile

    # Fetch the assignments for today
    today = timezone.localdate()
    daily_assignments = CollectionAssignment.objects.filter(
        worker=worker_profile,
        assignment_date=today
    ).order_by('household_id')

    # Get pending Bin Full Alerts in their area
    priority_alerts = BinFullAlert.objects.filter(
    worker_assigned=worker_profile # Filter only for jobs assigned to the current worker
    ).exclude(status='CLEARED') # Exclude any job that the worker has already finished


    # FIX 2: Fetch the count for the dashboard card
    unconfirmed_payments_count = Payment.objects.filter(
        is_paid_online=False, 
        worker_who_received_cash__isnull=True
    ).count()

    # FIX 3: Fetch the count for open worker complaints
    open_worker_complaints = WorkerComplaint.objects.filter(worker=worker_profile, status='PENDING').count()


    context = {
        'worker_profile': worker_profile,
        'today': today,
        'assignments': daily_assignments,
        'priority_alerts': priority_alerts,
        # FINAL CONTEXT VARIABLES
        'unconfirmed_payments_count': unconfirmed_payments_count,
        'open_worker_complaints': open_worker_complaints,
    }
    return render(request, 'workers/dashboard.html', context)

# --- 3. Collection Status & Complaint Stubs (To be implemented later) ---

# workers/views.py (Complete update_collection_status function)
@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def update_collection_status(request, assignment_id):
    # 1. Get the specific assignment or return a 404 error
    assignment = get_object_or_404(CollectionAssignment, id=assignment_id)
    worker_profile = request.user.workerprofile

    # Security Check: Ensure the assignment belongs to the logged-in worker
    if assignment.worker != worker_profile:
        messages.error(request, "Access denied. This assignment is not yours.")
        return redirect('worker_dashboard')

    if request.method == 'POST':
        form = CollectionUpdateForm(request.POST, request.FILES, instance=assignment)

        if form.is_valid():
            # 2. Save the photo proof and update status fields
            updated_assignment = form.save(commit=False)
            updated_assignment.is_collected = True
            updated_assignment.collection_time = timezone.now() # Record the exact time of collection
            updated_assignment.save()

            # 3. Notification to Resident (We mock this for now)
            # In a real app, this is where you would send a push/email notification.
            # Resident User Story: "I want to get notified when waste is collected."
            messages.success(request, f"Collection for Household {assignment.household_id} marked complete with photo proof. Resident notified!")

            return redirect('worker_dashboard')
        else:
            messages.error(request, "Please submit the photo proof to complete the collection.")

    else:
        # 4. GET request: If already collected, redirect to dashboard
        if assignment.is_collected:
            messages.warning(request, f"Collection for {assignment.household_id} is already complete.")
            return redirect('worker_dashboard')

        form = CollectionUpdateForm(instance=assignment)

    context = {
        'assignment': assignment,
        'form': form,
        'household_id': assignment.household_id
    }
    return render(request, 'workers/update_collection.html', context)



# workers/views.py (Add the new function)

@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def alert_detail_action(request, alert_id):
    worker_profile = request.user.workerprofile

    # Get the alert object, ensuring it's assigned to THIS worker
    alert = get_object_or_404(
        BinFullAlert, 
        id=alert_id, 
        worker_assigned=worker_profile
    )

    if request.method == 'POST':
        # 1. Action: Worker is confirming the bin is clear
        if alert.status != 'CLEARED':
            alert.status = 'CLEARED'
            alert.save()
            messages.success(request, f"Bin alert from {alert.resident.household_id} marked as CLEARED.")
        else:
            messages.warning(request, "This alert was already cleared.")

        return redirect('worker_dashboard')

    context = {
        'alert': alert,
    }
    return render(request, 'workers/alert_detail.html', context)


# workers/views.py (Complete raise_field_issue function)
@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def raise_field_issue(request):
    worker_profile = request.user.workerprofile

    if request.method == 'POST':
        form = WorkerComplaintForm(request.POST, request.FILES)

        if form.is_valid():
            complaint = form.save(commit=False)

            # Manually assign the worker and set status
            complaint.worker = worker_profile
            complaint.status = 'PENDING'
            complaint.save()

            messages.success(request, "Field issue reported successfully! Admin has been notified.")
            return redirect('worker_dashboard')
        else:
            messages.error(request, "Please correct the errors in the form.")

    else:
        form = WorkerComplaintForm()

    context = {
        'form': form,
        'open_complaints': WorkerComplaint.objects.filter(worker=worker_profile, status='PENDING')
    }
    return render(request, 'workers/raise_issue.html', context)

# workers/views.py (CORRECTED confirm_offline_payment function)
@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def confirm_offline_payment(request):
    worker_profile = request.user.workerprofile

    # 1. Fetch all reported offline payments that are NOT yet confirmed by a worker
    unconfirmed_payments = Payment.objects.filter(
        is_paid_online=False, 
        worker_who_received_cash__isnull=True
    ).order_by('-payment_date')

    if request.method == 'POST':
        # This block handles the submission of a single payment confirmation
        payment_id = request.POST.get('payment_id')

        try:
            payment = get_object_or_404(Payment, id=payment_id)

            if not payment.is_paid_online and payment.worker_who_received_cash is None:
                payment.worker_who_received_cash = worker_profile
                payment.save()

                # We redirect to the same page (GET request) to reload the list
                messages.success(request, f"Confirmed cash payment of ₹{payment.amount} from Household {payment.resident.household_id}.")
            else:
                messages.error(request, "This payment is either already confirmed or was paid online.")

        except Payment.DoesNotExist:
            messages.error(request, "Payment record not found.")

        return redirect('confirm_offline_payment') # <-- Redirect back to GET request

    # 2. This is the GET request part - it renders the list
    context = {
        'unconfirmed_payments': unconfirmed_payments
    }
    return render(request, 'workers/confirm_payment.html', context)

# workers/views.py (Add the new function)

@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def worker_history(request):
    worker_profile = request.user.workerprofile

    # 1. Collection History (All completed assignments)
    collection_history = CollectionAssignment.objects.filter(
        worker=worker_profile,
        is_collected=True
    ).order_by('-collection_time')

    # 2. Payment Confirmation History (Payments confirmed by this worker)
    payment_history = Payment.objects.filter(
        worker_who_received_cash=worker_profile
    ).order_by('-payment_date')

    # 3. Worker Complaint History (All complaints raised by this worker)
    complaint_history = WorkerComplaint.objects.filter(
        worker=worker_profile
    ).order_by('-submission_time')

    context = {
        'collection_history': collection_history,
        'payment_history': payment_history,
        'complaint_history': complaint_history,
    }
    return render(request, 'workers/history.html', context)