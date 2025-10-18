from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import WorkerProfile, CollectionAssignment, WorkerComplaint
from .forms import CollectionUpdateForm, WorkerComplaintForm
from residents.models import BinFullAlert, ResidentComplaint, Payment, NoCollectionRequest # Added NoCollectionRequest

# --- Helper Function for Worker Check ---
def is_worker(user):
    return WorkerProfile.objects.filter(user=user).exists()

# --- 1. Authentication Views ---

def worker_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            try:
                # CRUCIAL CHECK: Only allow login if WorkerProfile exists
                profile = user.workerprofile 
                login(request, user)
                messages.success(request, f"Welcome, {user.username} (Worker ID: {profile.worker_id})")
                return redirect('worker_dashboard')
            except WorkerProfile.DoesNotExist:
                messages.error(request, "Access Denied. Your account is not registered as a Field Worker.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'workers/login.html')

@login_required(login_url='worker_login')
def worker_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('worker_login')

# --- 2. Dashboard View ---

@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def worker_dashboard(request):
    worker_profile = request.user.workerprofile
    today = timezone.localdate()
    
    current_month = today.month
    current_year = today.year

    # --- Task Filtering Logic ---
    # 1. Get list of households the resident requested to SKIP
    households_to_skip = NoCollectionRequest.objects.filter(
        collection_month=current_month,
        collection_year=current_year
    ).values_list('resident__household_id', flat=True)
    
    # 2. Fetch Daily Assignments, excluding skipped households
    daily_assignments = CollectionAssignment.objects.filter(
        worker=worker_profile,
        assignment_date=today
    ).exclude(household_id__in=households_to_skip).order_by('household_id') 

    # 3. Get pending Bin Full Alerts (assigned to this worker and not cleared)
    priority_alerts = BinFullAlert.objects.filter(
        worker_assigned=worker_profile
    ).exclude(status='CLEARED') 

    # 4. Counts for Dashboard Cards
    unconfirmed_payments_count = Payment.objects.filter(
        is_paid_online=False, 
        worker_who_received_cash__isnull=True
    ).count()

    open_worker_complaints = WorkerComplaint.objects.filter(worker=worker_profile, status='PENDING').count()
    
    context = {
        'worker_profile': worker_profile,
        'today': today,
        'assignments': daily_assignments,
        'priority_alerts': priority_alerts,
        'unconfirmed_payments_count': unconfirmed_payments_count,
        'open_worker_complaints': open_worker_complaints,
    }
    return render(request, 'workers/dashboard.html', context)


# --- 3. Collection Status Update ---

@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def update_collection_status(request, assignment_id):
    assignment = get_object_or_404(CollectionAssignment, id=assignment_id)
    worker_profile = request.user.workerprofile

    if assignment.worker != worker_profile:
        messages.error(request, "Access denied. This assignment is not yours.")
        return redirect('worker_dashboard')

    if request.method == 'POST':
        form = CollectionUpdateForm(request.POST, request.FILES, instance=assignment)

        if form.is_valid():
            updated_assignment = form.save(commit=False)
            updated_assignment.is_collected = True
            updated_assignment.collection_time = timezone.now()
            updated_assignment.save()

            messages.success(request, f"Collection for Household {assignment.household_id} marked complete with photo proof.")
            return redirect('worker_dashboard')
        else:
            messages.error(request, "Please submit the photo proof to complete the collection.")

    else:
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


# --- 4. Alert Detail/Action (Priority Pickup Clear) ---

@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def alert_detail_action(request, alert_id):
    worker_profile = request.user.workerprofile

    alert = get_object_or_404(
        BinFullAlert, 
        id=alert_id, 
        worker_assigned=worker_profile
    )

    if request.method == 'POST':
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


# --- 5. Worker Complaint ---

@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def raise_field_issue(request):
    worker_profile = request.user.workerprofile

    if request.method == 'POST':
        form = WorkerComplaintForm(request.POST, request.FILES)

        if form.is_valid():
            complaint = form.save(commit=False)
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

# --- 6. Payment Confirmation ---

@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def confirm_offline_payment(request):
    worker_profile = request.user.workerprofile

    unconfirmed_payments = Payment.objects.filter(
        is_paid_online=False, 
        worker_who_received_cash__isnull=True
    ).order_by('-payment_date')

    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')

        try:
            payment = get_object_or_404(Payment, id=payment_id)

            if not payment.is_paid_online and payment.worker_who_received_cash is None:
                payment.worker_who_received_cash = worker_profile
                payment.save()

                messages.success(request, f"Confirmed cash payment of ₹{payment.amount} from Household {payment.resident.household_id}.")
            else:
                messages.error(request, "This payment is already confirmed.")

        except Payment.DoesNotExist:
            messages.error(request, "Payment record not found.")

        return redirect('confirm_offline_payment')

    context = {
        'unconfirmed_payments': unconfirmed_payments
    }
    return render(request, 'workers/confirm_payment.html', context)


# --- 7. History View ---

@login_required(login_url='worker_login')
@user_passes_test(is_worker, login_url='worker_login')
def worker_history(request):
    worker_profile = request.user.worker_profile
    
    # --- Date Filter Logic ---
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Base queries
    collection_query = CollectionAssignment.objects.filter(worker=worker_profile, is_collected=True)
    payment_query = Payment.objects.filter(worker_who_received_cash=worker_profile)
    complaint_query = WorkerComplaint.objects.filter(worker=worker_profile)

    # Apply date filters
    if start_date_str:
        collection_query = collection_query.filter(collection_time__gte=start_date_str)
        payment_query = payment_query.filter(payment_date__gte=start_date_str)
        complaint_query = complaint_query.filter(submission_time__gte=start_date_str)
    
    if end_date_str:
        collection_query = collection_query.filter(collection_time__lte=end_date_str)
        payment_query = payment_query.filter(payment_date__lte=end_date_str)
        complaint_query = complaint_query.filter(submission_time__lte=end_date_str)

    collection_history = collection_query.order_by('-collection_time')
    payment_history = payment_query.order_by('-payment_date')
    complaint_history = complaint_query.order_by('-submission_time')
    
    context = {
        'collection_history': collection_history,
        'payment_history': payment_history,
        'complaint_history': complaint_history,
        'start_date': start_date_str,
        'end_date': end_date_str,
    }
    return render(request, 'workers/history.html', context)