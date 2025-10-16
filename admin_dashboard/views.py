from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages 
from django.utils import timezone
from django.db import models as db_models
from django.db.models import Q # Used for complex queries
from django.contrib.auth.models import User
from datetime import timedelta, date

from .forms import ScheduleGenerationForm, DailyTaskAssignmentForm, UserOnboardingForm # Added UserOnboardingForm here
from residents.models import BinFullAlert, ResidentComplaint, Payment, BillingDue 
from workers.models import WorkerProfile, CollectionAssignment, WorkerComplaint, HKSWardAssignment, SupervisorProfile


# --- Helper Function for Admin Check ---
def is_superuser(user):
    return user.is_superuser

# --- 1. Admin Monitoring Dashboard ---
@login_required(login_url='admin:login')
@user_passes_test(is_superuser, login_url='admin:login')
def admin_monitoring_dashboard(request):
    today = timezone.localdate()

    # --- 1. Workflow Monitoring (KPIs) ---
    pending_alerts = BinFullAlert.objects.filter(status='PENDING').count()
    pending_complaints_res = ResidentComplaint.objects.filter(status='PENDING').count()
    pending_complaints_wkr = WorkerComplaint.objects.filter(status='PENDING').count()
    unconfirmed_payments = Payment.objects.filter(is_paid_online=False, worker_who_received_cash__isnull=True).count()
    overdue_bills = BillingDue.objects.filter(is_paid=False, due_date__lt=today).count()

    # --- 2. Collection Progress Today ---
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


# --- 2. Generate Monthly Schedule ---
@login_required(login_url='admin:login')
@user_passes_test(is_superuser, login_url='admin:login')
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

        # Core HKS Logic (Assumes 500 households, 10-day cycle)
        HOUSEHOLDS_IN_WARD = 500 
        COLLECTION_DAYS = 10
        DAILY_TEAM_TARGET = HOUSEHOLDS_IN_WARD // COLLECTION_DAYS # 50 houses
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
                
                # Prepare Worker 1's tasks
                for household_id in w1_households:
                    tasks_to_create.append(CollectionAssignment(
                        worker=workers[0], assignment_date=current_date, household_id=household_id, collection_cycle_day=day + 1
                    ))
                # Prepare Worker 2's tasks
                for household_id in w2_households:
                    tasks_to_create.append(CollectionAssignment(
                        worker=workers[1], assignment_date=current_date, household_id=household_id, collection_cycle_day=day + 1
                    ))
            else: # Single worker case
                for household_id in daily_households:
                    tasks_to_create.append(CollectionAssignment(
                        worker=workers[0], assignment_date=current_date, household_id=household_id, collection_cycle_day=day + 1
                    ))

        created_tasks = CollectionAssignment.objects.bulk_create(tasks_to_create, ignore_conflicts=True)
        assignments_created = len(created_tasks)
        
        messages.success(request, f"Successfully generated route for {ward_id}. {assignments_created} new tasks created.")
        return redirect('admin_monitoring_dashboard')

    context = {'form': form}
    return render(request, 'admin_dashboard/schedule_generator.html', context)


# --- 3. Priority Pickup Management ---
@login_required(login_url='admin:login')
@user_passes_test(is_superuser, login_url='admin:login')
def priority_pickup_management(request):
    # Fetch all pending alerts (those needing action)
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


# --- 4. Complaint Resolution ---
@login_required(login_url='admin:login')
@user_passes_test(is_superuser, login_url='admin:login')
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


# --- 5. Assign Daily Task (One-Off) ---
@login_required(login_url='admin:login')
@user_passes_test(is_superuser, login_url='admin:login')
def assign_daily_task(request):
    form = DailyTaskAssignmentForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        ward_id = form.cleaned_data['ward']
        target_date = form.cleaned_data['target_date']
        # house_start = form.cleaned_data['house_start'] # Not used in mock creation
        # house_end = form.cleaned_data['house_end'] # Not used in mock creation

        try:
            assignment_config = HKSWardAssignment.objects.get(ward_id=ward_id)
            workers = [assignment_config.worker1]
            if assignment_config.worker2:
                workers.append(assignment_config.worker2)
        except HKSWardAssignment.DoesNotExist:
            messages.error(request, f"Error: No HKS team assigned to Ward {ward_id}.")
            return redirect('assign_daily_task')

        mock_household_ids = [f"{ward_id}-MOCK-H{i}" for i in range(5)] # Create 5 mock tasks
        tasks_to_create = []

        for worker in workers:
            for household_id in mock_household_ids:
                tasks_to_create.append(CollectionAssignment(
                    worker=worker,
                    assignment_date=target_date,
                    household_id=household_id,
                    is_collected=False,
                    collection_cycle_day=0 # Mark as one-off assignment
                ))

        created_tasks = CollectionAssignment.objects.bulk_create(tasks_to_create, ignore_conflicts=True)
        tasks_created = len(created_tasks)
        
        messages.success(request, f"Assigned {tasks_created} quick tasks to the team in {ward_id} for {target_date}.")
        return redirect('admin_monitoring_dashboard')

    context = {'form': form}
    return render(request, 'admin_dashboard/assign_daily_task.html', context)


# --- 6. Ward Assignment Management (HKS Matrix View) ---
@login_required(login_url='admin:login')
@user_passes_test(is_superuser, login_url='admin:login')
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


# --- 7. User Onboarding ---
@login_required(login_url='admin:login')
@user_passes_test(is_superuser, login_url='admin:login')
def user_onboarding(request):
    if request.method == 'POST':
        form = UserOnboardingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            
            try:
                user = User.objects.create_user(
                    username=data['username'],
                    password=data['password'],
                    email=data['email']
                )
            except Exception as e:
                messages.error(request, f"Error creating user: {e}")
                return redirect('user_onboarding')

            if data['profile_type'] == 'WORKER':
                WorkerProfile.objects.create(
                    user=user, 
                    worker_id=data['profile_id'],
                    assigned_wards=[data['ward_number']] if data['ward_number'] else []
                )
            elif data['profile_type'] == 'SUPERVISOR':
                SupervisorProfile.objects.create(
                    user=user, 
                    supervisor_id=data['profile_id']
                )
            
            messages.success(request, f"User {user.username} created and linked as {data['profile_type']}.")
            return redirect('admin_monitoring_dashboard')
        else:
            messages.error(request, "Form validation failed. Please check all fields.")
    
    else:
        form = UserOnboardingForm()
        
    context = {'form': form}
    return render(request, 'admin_dashboard/user_onboarding.html', context)

# --- 8. Monthly Report Placeholder (Not fully implemented) ---
@login_required(login_url='admin:login')
@user_passes_test(is_superuser, login_url='admin:login')
def monthly_report(request):
    messages.info(request, "The monthly report feature is not yet implemented.")
    return redirect('admin_monitoring_dashboard')