from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages 
from django.utils import timezone
from django.db import models as db_models
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from datetime import timedelta, date
from decimal import Decimal
from django.db.models import Q

# Import all forms and models
from .forms import ScheduleGenerationForm, DailyTaskAssignmentForm, UserOnboardingForm, MonthlyReportForm
from residents.models import BinFullAlert, ResidentComplaint, Payment, BillingDue 
from workers.models import WorkerProfile, CollectionAssignment, WorkerComplaint, HKSWardAssignment, SupervisorProfile


# --- Helper Function for Admin Check ---
def is_superuser(user):
    return user.is_superuser

# --- 1. Custom Admin Login ---

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome, Admin {user.username}.")
                return redirect('admin_monitoring_dashboard')
            else:
                messages.error(request, "Access Denied. Only Superusers can access the Admin Portal.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'admin_dashboard/admin_login.html')


# --- 2. Admin Monitoring Dashboard (KPIs and Overview) ---

@login_required(login_url='admin_login')
@user_passes_test(is_superuser, login_url='admin_login')
def admin_monitoring_dashboard(request):
    today = timezone.localdate()

    # Workflow Monitoring (KPIs)
    pending_alerts = BinFullAlert.objects.filter(status='PENDING').count()
    pending_complaints_res = ResidentComplaint.objects.filter(status='PENDING').count()
    pending_complaints_wkr = WorkerComplaint.objects.filter(status='PENDING').count()
    unconfirmed_payments = Payment.objects.filter(is_paid_online=False, worker_who_received_cash__isnull=True).count()
    overdue_bills = BillingDue.objects.filter(is_paid=False, due_date__lt=today).count()

    # Collection Progress Today
    total_assignments_today = CollectionAssignment.objects.filter(assignment_date=today).count()
    collected_assignments_today = CollectionAssignment.objects.filter(assignment_date=today, is_collected=True).count()

    if total_assignments_today > 0:
        collection_progress = (collected_assignments_today / total_assignments_today) * 100
    else:
        collection_progress = 0

    context = {
        'pending_alerts': pending_alerts,
        'pending_complaints_res': pending_complaints_res,
        'pending_complaints_wkr': pending_complaints_wkr,
        'unconfirmed_payments': unconfirmed_payments,
        'overdue_bills': overdue_bills,
        'total_assignments_today': total_assignments_today,
        'collected_assignments_today': collected_assignments_today,
        'collection_progress': round(collection_progress, 1),
        'today': today,
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


# --- 3. Generate Monthly Schedule (Route Automation) ---

@login_required(login_url='admin_login')
@user_passes_test(is_superuser, login_url='admin_login')
def generate_monthly_schedule(request):
    form = ScheduleGenerationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        ward_id = form.cleaned_data['ward_id']
        month = form.cleaned_data['month']
        year = form.cleaned_data['year']

        try:
            assignment_config = HKSWardAssignment.objects.get(ward_id=ward_id)
        except HKSWardAssignment.DoesNotExist:
            messages.error(request, f"Ward {ward_id} configuration not found. Assign workers first.")
            return redirect('admin_monitoring_dashboard')

        workers = [w for w in [assignment_config.worker1, assignment_config.worker2] if w is not None]

        HOUSEHOLDS_IN_WARD = 500 
        COLLECTION_DAYS = 10
        DAILY_TEAM_TARGET = HOUSEHOLDS_IN_WARD // COLLECTION_DAYS
        DAILY_INDIVIDUAL_TARGET = DAILY_TEAM_TARGET // 2 if len(workers) == 2 else DAILY_TEAM_TARGET 
        
        try:
            start_date = date(year, month, 5) 
        except ValueError:
            messages.error(request, "Invalid month/year combination.")
            return redirect('admin_monitoring_dashboard')

        households_list = [f"{ward_id}-H{i+1}" for i in range(HOUSEHOLDS_IN_WARD)]
        tasks_to_create = []

        for day in range(COLLECTION_DAYS): 
            current_date = start_date + timedelta(days=day)
            
            start_index = day * DAILY_TEAM_TARGET
            end_index = (day + 1) * DAILY_TEAM_TARGET
            daily_households = households_list[start_index:end_index]
            
            # CRITICAL LOGIC: SPLITTING WORKLOAD
            if len(workers) == 2:
                w1_households = daily_households[:DAILY_INDIVIDUAL_TARGET]
                w2_households = daily_households[DAILY_INDIVIDUAL_TARGET:]
                
                for household_id in w1_households:
                    tasks_to_create.append(CollectionAssignment(worker=workers[0], assignment_date=current_date, household_id=household_id, collection_cycle_day=day + 1))
                for household_id in w2_households:
                    tasks_to_create.append(CollectionAssignment(worker=workers[1], assignment_date=current_date, household_id=household_id, collection_cycle_day=day + 1))
            else: # Single worker case
                for household_id in daily_households:
                    tasks_to_create.append(CollectionAssignment(worker=workers[0], assignment_date=current_date, household_id=household_id, collection_cycle_day=day + 1))

        created_tasks = CollectionAssignment.objects.bulk_create(tasks_to_create, ignore_conflicts=True)
        assignments_created = len(created_tasks)
        
        messages.success(request, f"Successfully generated route for {ward_id}. {assignments_created} new tasks created.")
        return redirect('admin_monitoring_dashboard')

    context = {'form': form}
    return render(request, 'admin_dashboard/schedule_generator.html', context)


# --- 4. Priority Pickup Management ---

@login_required(login_url='admin_login')
@user_passes_test(is_superuser, login_url='admin_login')
def priority_pickup_management(request):
    pending_alerts = BinFullAlert.objects.filter(status__in=['PENDING', 'ASSIGNED']).order_by('-alert_time')
    all_workers = WorkerProfile.objects.all()

    if request.method == 'POST':
        alert_id = request.POST.get('alert_id')
        action = request.POST.get('action') 

        alert = get_object_or_404(BinFullAlert, id=alert_id)

        if action == 'ASSIGN':
            worker_id = request.POST.get('worker_id')
            worker = get_object_or_404(WorkerProfile, id=worker_id)
            alert.worker_assigned = worker
            alert.status = 'ASSIGNED'
            alert.save()
            messages.success(request, f"Alert {alert_id} assigned to {worker.worker_id}.")
        
        elif action == 'CLOSE':
            alert.status = 'CLEARED'
            alert.save()
            messages.success(request, f"Alert {alert_id} forcibly marked CLEARED by Admin.")
            
        return redirect('priority_pickup_management')
        
    context = {
        'pending_alerts': pending_alerts,
        'all_workers': all_workers,
    }
    return render(request, 'admin_dashboard/priority_pickup.html', context)


# --- 5. Complaint Resolution ---

@login_required(login_url='admin_login')
@user_passes_test(is_superuser, login_url='admin_login')
def complaint_resolution(request):
    resident_complaints = ResidentComplaint.objects.filter(status__in=['PENDING', 'IN_PROGRESS']).order_by('-submission_time')
    worker_complaints = WorkerComplaint.objects.filter(status='PENDING').order_by('-submission_time')

    if request.method == 'POST':
        complaint_type = request.POST.get('type')
        complaint_id = request.POST.get('id')
        action_notes = request.POST.get('notes')
        new_status = request.POST.get('status')

        if complaint_type == 'RESIDENT':
            model = ResidentComplaint
        else:
            model = WorkerComplaint

        complaint = get_object_or_404(model, id=complaint_id)
        complaint.status = new_status
        if complaint_type == 'RESIDENT':
            complaint.resolution_notes = action_notes
        complaint.save()

        messages.success(request, f"{complaint_type} Complaint #{complaint_id} updated to {new_status}.")
        return redirect('complaint_resolution')

    context = {
        'resident_complaints': resident_complaints,
        'worker_complaints': worker_complaints
    }
    return render(request, 'admin_dashboard/complaint_resolution.html', context)


# --- 6. Assign Daily Task (One-Off) ---
 # The form for this view

@login_required(login_url='admin_login')
@user_passes_test(is_superuser, login_url='admin_login')
def assign_daily_task(request):
    today = timezone.localdate()
    form = DailyTaskAssignmentForm(request.POST or None)
    absentee_data = [] # Initialize this list

    # --- 1. POST Request Handling (Task Creation) ---
    if request.method == 'POST' and form.is_valid():
        ward_id = form.cleaned_data['ward']
        target_date = form.cleaned_data['target_date']

        try:
            assignment_config = HKSWardAssignment.objects.get(ward_id=ward_id)
            workers = [assignment_config.worker1]
            if assignment_config.worker2:
                workers.append(assignment_config.worker2)
        except HKSWardAssignment.DoesNotExist:
            messages.error(request, f"Error: No HKS team assigned to Ward {ward_id}. Please assign a team first.")
            return redirect('assign_daily_task')

        # Task Creation Logic (Simplified Mock)
        mock_household_ids = [f"{ward_id}-COVER-H{i}" for i in range(5)]
        tasks_to_create = []

        for worker in workers:
            for household_id in mock_household_ids:
                tasks_to_create.append(CollectionAssignment(
                    worker=worker,
                    assignment_date=target_date,
                    household_id=household_id,
                    is_collected=False,
                    collection_cycle_day=0 
                ))

        created_tasks = CollectionAssignment.objects.bulk_create(tasks_to_create, ignore_conflicts=True)
        tasks_created = len(created_tasks)
        
        messages.success(request, f"Assigned {tasks_created} quick tasks to the team in {ward_id} for {target_date}.")
        return redirect('admin_monitoring_dashboard')


    # --- 2. GET Request Handling & Context Preparation ---

    # Fetch recent absence requests for context display
    recent_absences = WorkerComplaint.objects.filter(
        issue_type='ABSENCE',
        status='PENDING',
        submission_time__date=today
    ).select_related('worker') 
    
    # Process absence data to include Ward and Teammate info
    for absence in recent_absences:
        try:
            # Find the HKS assignment where this worker is involved (primary or secondary)
            assignment = HKSWardAssignment.objects.get(
                Q(worker1=absence.worker) | Q(worker2=absence.worker)
            )
            # Find the teammate (the one who is NOT the absent worker)
            if assignment.worker1 == absence.worker and assignment.worker2:
                teammate_id = assignment.worker2.worker_id
            elif assignment.worker2 == absence.worker and assignment.worker1:
                teammate_id = assignment.worker1.worker_id
            else:
                teammate_id = 'None'
                
            ward_id = assignment.ward_id
            
        except HKSWardAssignment.DoesNotExist:
            ward_id = 'Unassigned/Unknown'
            teammate_id = 'None'

        absentee_data.append({
            'worker_id': absence.worker.worker_id,
            'reason': absence.details,
            'ward_id': ward_id,
            'teammate': teammate_id,
        })
    
    context = {
        'form': form,
        'recent_absences_data': absentee_data, # Updated context variable name
        'today': today,
    }
    return render(request, 'admin_dashboard/assign_daily_task.html', context)

# --- 7. Ward Assignment Management (HKS Matrix View) ---

@login_required(login_url='admin_login')
@user_passes_test(is_superuser, login_url='admin_login')
def ward_assignment_management(request):
    assignments = HKSWardAssignment.objects.all().order_by('ward_id')
    all_workers = WorkerProfile.objects.all()
    all_supervisors = SupervisorProfile.objects.all()

    context = {
        'assignments': assignments,
        'all_workers': all_workers,
        'all_supervisors': all_supervisors,
    }
    return render(request, 'admin_dashboard/ward_management.html', context)


# --- 8. User Onboarding (Removed, placeholder added for structural completeness) ---

# --- 9. Financial Manager Views ---

# admin_dashboard/views.py (unconfirmed_payments_manager)

# admin_dashboard/views.py (Inside unconfirmed_payments_manager function)

@login_required(login_url='admin_login')
@user_passes_test(is_superuser, login_url='admin_login')
def unconfirmed_payments_manager(request):
    unconfirmed_payments = Payment.objects.filter(
        is_paid_online=False, 
        worker_who_received_cash__isnull=True
    ).order_by('-payment_date')

    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')
        action = request.POST.get('action') 

        payment = get_object_or_404(Payment, id=payment_id)

        if action == 'ALERT_WORKER':
            messages.success(request, f"ALERT SENT! Notification triggered for responsible worker to confirm payment #{payment_id}.")
            
            # Note: We do NOT redirect here yet, we let the outer block handle it.
            
        # --- CRITICAL FIX: Ensure REDIRECT is ALWAYS HIT AFTER POST IS DONE ---
        return redirect('admin_monitoring_dashboard') # <-- Moves control back to the dashboard

    # The rest of the function handles the GET request (displaying the list).
    context = {
        'unconfirmed_payments': unconfirmed_payments,
    }
    return render(request, 'admin_dashboard/unconfirmed_payments.html', context)

from django.contrib.auth.models import User
@login_required(login_url='admin_login')
@user_passes_test(is_superuser, login_url='admin_login')
def overdue_bills_manager(request):
    today = timezone.localdate()
    
    overdue_bills = BillingDue.objects.filter(
        is_paid=False, 
        due_date__lt=today
    ).order_by('due_date')

    if request.method == 'POST':
        bill_id = request.POST.get('bill_id')
        action = request.POST.get('action')
        
        bill = get_object_or_404(BillingDue, id=bill_id)
        
        if action == 'ALERT_RESIDENT':
            messages.warning(request, f"Overdue alert sent to Resident {bill.resident.household_id}.")
            return redirect('overdue_bills_manager')

    context = {
        'overdue_bills': overdue_bills,
    }
    return render(request, 'admin_dashboard/overdue_bills_manager.html', context)


# --- 10. Monthly Report Placeholder ---
# admin_dashboard/views.py (UPDATED monthly_report function)


@login_required(login_url='admin_login')
@user_passes_test(is_superuser, login_url='admin_login')
def monthly_report(request):
    # Default to current month/year or use GET parameters if submitted
    target_month = int(request.GET.get('month', timezone.now().month))
    target_year = int(request.GET.get('year', timezone.now().year))
    
    # Handle Form Submission (if Admin submits a specific month/year)
    if request.method == 'POST':
        form = MonthlyReportForm(request.POST)
        if form.is_valid():
            target_month = form.cleaned_data['month']
            target_year = form.cleaned_data['year']
        # If the form is submitted, we reload the page with GET parameters 
        # to ensure the report calculation is executed cleanly.
        return redirect(f"{reverse('monthly_report')}?month={target_month}&year={target_year}")

    # --- Calculation Logic (Uses target_month/year) ---
    
    all_assignments = CollectionAssignment.objects.filter(
        assignment_date__year=target_year,
        assignment_date__month=target_month
    )
    total_tasks = all_assignments.count()
    completed_tasks = all_assignments.filter(is_collected=True).count()
    completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0

    total_revenue = Payment.objects.filter(
        payment_date__year=target_year,
        payment_date__month=target_month,
    ).aggregate(
        total_collected=db_models.Sum('amount')
    )['total_collected'] or Decimal('0.00')

    total_resident_complaints = ResidentComplaint.objects.filter(submission_time__year=target_year, submission_time__month=target_month).count()
    total_worker_issues = WorkerComplaint.objects.filter(submission_time__year=target_year, submission_time__month=target_month).count()

    context = {
        'form': MonthlyReportForm(initial={'month': target_month, 'year': target_year}), # Pass form for month selection
        'target_month': date(target_year, target_month, 1).strftime('%B'),
        'target_year': target_year,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': round(completion_rate, 1),
        'total_revenue': total_revenue,
        'total_resident_complaints': total_resident_complaints,
        'total_worker_issues': total_worker_issues,
    }
    return render(request, 'admin_dashboard/monthly_report.html', context)