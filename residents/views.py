# residents/views.py
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction  # <-- ADD THIS LINE
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import (BinFullAlertForm, ResidentComplaintForm,
                    OfflinePaymentForm)
from .models import (BinFullAlert, BillingDue, NoCollectionRequest, Payment,
                     ResidentComplaint, ResidentProfile)


# --- 1. Authentication Views ---

# residents/views.py (UPDATED resident_login function)
def resident_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            try:
                # **CRUCIAL CHECK:** Only allow login if ResidentProfile exists
                profile = user.residentprofile 
                login(request, user)
                messages.success(request, f"Welcome, {user.username}.")
                return redirect('resident_dashboard')
            except ResidentProfile.DoesNotExist:
                # Fail authentication if profile type does not match
                messages.error(request, "Access Denied. Your account is not registered as a Resident.")
        else:
            messages.error(request, "Invalid username or password.")

    # If GET or failed login
    return render(request, 'residents/login.html')


@login_required(login_url='resident_login')
def resident_logout(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('resident_login')



# residents/views.py (Updated resident_dashboard function)
@login_required(login_url='resident_login')
def resident_dashboard(request):
    try:
        resident_profile = request.user.residentprofile

        # --- PAYMENT DUE LOGIC FIX ---
        # Find the oldest unpaid due for this resident
        pending_due = BillingDue.objects.filter(
            resident=resident_profile, 
            is_paid=False
        ).order_by('due_date').first()

        if pending_due:
            current_due_amount = pending_due.amount_due
            due_id = pending_due.id
        else:
            current_due_amount = 0.00
            due_id = None
        # --- END PAYMENT DUE LOGIC FIX ---

        # Fetch data for the dashboard view (rest remains the same)
        pending_alerts = BinFullAlert.objects.filter(resident=resident_profile, status='PENDING').count()
        pending_complaints = ResidentComplaint.objects.filter(resident=resident_profile, status='PENDING').count()

        # Context dictionary holds all data passed to the HTML template
        context = {
            'username': request.user.username,
            'household_id': resident_profile.household_id,
            'pending_alerts': pending_alerts,
            'pending_complaints': pending_complaints,
            # NEW CONTEXT VARIABLES
            'current_due_amount': current_due_amount,
            'due_id': due_id,
        }
        return render(request, 'residents/dashboard.html', context)

    except ResidentProfile.DoesNotExist:
        # Handle cases where a logged-in user (e.g., the superuser) has no resident profile
        messages.error(request, "Access denied. You do not have a registered Resident Profile.")
        # Still show a basic dashboard template, but with an error.
        return render(request, 'residents/dashboard.html', {'username': request.user.username})


# --- 2. Use Case 1: Alert Bin is Full (Stub, will be detailed with forms later) ---
# residents/views.py (Updated alert_bin_full function)
@login_required(login_url='resident_login')
def alert_bin_full(request):
    # 1. Ensure the logged-in user has a ResidentProfile
    try:
        resident_profile = request.user.residentprofile
    except ResidentProfile.DoesNotExist:
        messages.error(request, "Access Denied: You do not have a registered Resident Profile.")
        return redirect('resident_dashboard')

    if request.method == 'POST':
        # 2. Process the submitted form data and file uploads
        # NOTE: request.FILES is required for file uploads (photo_proof)
        form = BinFullAlertForm(request.POST, request.FILES) 

        if form.is_valid():
            # 3. Form is valid: Don't save to the database immediately (commit=False)
            alert = form.save(commit=False) 

            # 4. Manually assign fields that were not in the form (Resident and Status)
            alert.resident = resident_profile 
            alert.status = 'PENDING'
            # Manually assign the custom form field 'bin_location' to the model's 'location_detail' field
            alert.location_detail = form.cleaned_data['bin_location']

            alert.save() # Save the alert and the photo file

            messages.success(request, "Bin full alert submitted successfully! The Admin has been notified for priority pickup.")
            return redirect('resident_dashboard')
        else:
            # 5. Form is invalid (e.g., no photo uploaded)
            messages.error(request, "Please correct the errors below and ensure a photo is uploaded.")

    else:
        # 6. GET request: Display a blank form
        form = BinFullAlertForm()

    context = {'form': form}
    return render(request, 'residents/alert_bin_full.html', context)



# residents/views.py (New function for Use Case 2)
# residents/views.py (The complete, correct pay_waste_fee function)

# residents/views.py (The complete, corrected pay_waste_fee function)

@login_required(login_url='resident_login')
@transaction.atomic
def pay_waste_fee(request):
    try:
        resident_profile = request.user.residentprofile
    except ResidentProfile.DoesNotExist:
        messages.error(request, "Access Denied: Profile not found.")
        return redirect('resident_dashboard')
        
    # CRITICAL: current_due_amount is fetched as a Decimal, or set to Decimal('0.00')
    pending_due = BillingDue.objects.filter(
        resident=resident_profile, 
        is_paid=False
    ).order_by('due_date').first()
    
    current_due_amount = pending_due.amount_due if pending_due else Decimal('0.00')
    
    # --- Handle Offline Payment Submission (POST) ---
    if request.method == 'POST':
        if current_due_amount == 0:
            messages.error(request, "You have no outstanding dues to report a payment against.")
            return redirect('pay_waste_fee')
        
        # Form receives data and files
        form = OfflinePaymentForm(request.POST, request.FILES) 
        
        if form.is_valid():
            paid_amount = form.cleaned_data['amount'] # This is a Decimal
            
            # CRITICAL FIX: Direct comparison of the two Decimal objects
            if paid_amount != current_due_amount: 
                 messages.error(request, f"Reported amount ({paid_amount}) does not match the outstanding due amount ({current_due_amount}). Please pay the exact amount.")
                 return redirect('pay_waste_fee')
            
            # Create the Payment record
            payment = form.save(commit=False)
            payment.resident = resident_profile
            payment.is_paid_online = False
            payment.save()
            
            # Mark the corresponding BillingDue record as paid
            if pending_due:
                pending_due.is_paid = True
                pending_due.save()
            
            messages.success(request, f"Offline payment of ₹{paid_amount} reported successfully! Worker confirmation pending.")
            return redirect('resident_dashboard')
        else:
            # If form validation fails (e.g., photo missing, amount malformed)
            messages.error(request, "Error in payment details. Please check the amount, receipt number, and ensure a photo is attached.")
            # Fall through to render form with errors
    
    # --- Handle GET Request (Display the form) ---
    else:
        # Pre-fill the amount, converting Decimal to string for HTML rendering
        initial_data = {'amount': str(current_due_amount)}
        form = OfflinePaymentForm(initial=initial_data)
        
    context = {
        'pending_due_amount': current_due_amount,
        'offline_form': form
    }
    return render(request, 'residents/pay_waste_fee.html', context)

    
# --- 3. Use Case 3: Raise Complaint (Stub) ---
# residents/views.py (Complete raise_complaint function)
@login_required(login_url='resident_login')
def raise_complaint(request):
    # 1. Ensure the logged-in user has a ResidentProfile
    try:
        resident_profile = request.user.residentprofile
    except ResidentProfile.DoesNotExist:
        messages.error(request, "Access Denied: You do not have a registered Resident Profile.")
        return redirect('resident_dashboard')

    if request.method == 'POST':
        # 2. Process the submitted form data and file uploads
        form = ResidentComplaintForm(request.POST, request.FILES)

        if form.is_valid():
            # 3. Form is valid: Don't save to the database immediately
            complaint = form.save(commit=False)

            # 4. Manually assign fields
            complaint.resident = resident_profile
            complaint.status = 'PENDING' # Set the initial status
            complaint.save()

            messages.success(request, "Complaint submitted successfully! An Admin has been notified for review.")
            return redirect('resident_dashboard')
        else:
            # 5. Form is invalid
            messages.error(request, "Please correct the errors in the form.")

    else:
        # 6. GET request: Display a blank form
        form = ResidentComplaintForm()

    # 7. Render the complaint page with the form
    context = {'form': form}
    return render(request, 'residents/raise_complaint.html', context)



# --- 4. History (Stub) ---
# residents/views.py (Complete resident_history function)
# residents/views.py (UPDATED resident_history function)
@login_required(login_url='resident_login')
def resident_history(request):
    try:
        resident_profile = request.user.residentprofile
    except ResidentProfile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('resident_dashboard')

    # --- NEW: Get date filters from URL ---
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Start with an empty filter dictionary
    date_filter = {} 

    if start_date_str:
        # Filter where the date is greater than or equal to the start date
        date_filter['alert_time__gte'] = start_date_str # Use __gte for dates >=
        date_filter['submission_time__gte'] = start_date_str 
        date_filter['payment_date__gte'] = start_date_str 
    
    if end_date_str:
        # Filter where the date is less than or equal to the end date
        # Django's date range uses __lte (less than or equal)
        date_filter['alert_time__lte'] = end_date_str
        date_filter['submission_time__lte'] = end_date_str
        date_filter['payment_date__lte'] = end_date_str
    # --- END Date Filter Logic ---

    # Apply the filters to the queries
    alerts = BinFullAlert.objects.filter(resident=resident_profile, **{'alert_time__range': (date_filter.get('alert_time__gte'), date_filter.get('alert_time__lte'))} if date_filter.get('alert_time__gte') or date_filter.get('alert_time__lte') else {}).order_by('-alert_time')
    complaints = ResidentComplaint.objects.filter(resident=resident_profile, **{'submission_time__range': (date_filter.get('submission_time__gte'), date_filter.get('submission_time__lte'))} if date_filter.get('submission_time__gte') or date_filter.get('submission_time__lte') else {}).order_by('-submission_time')
    payments = Payment.objects.filter(resident=resident_profile, **{'payment_date__range': (date_filter.get('payment_date__gte'), date_filter.get('payment_date__lte'))} if date_filter.get('payment_date__gte') or date_filter.get('payment_date__lte') else {}).order_by('-payment_date')
    
    context = {
        'alerts': alerts,
        'complaints': complaints,
        'payments': payments,
        'start_date': start_date_str, # Pass back to template for form stickiness
        'end_date': end_date_str,
    }
    return render(request, 'residents/history.html', context)

# residents/views.py (Add the new view)
@login_required(login_url='resident_login')
def no_collection_request(request):
    try:
        resident_profile = request.user.residentprofile
    except ResidentProfile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('resident_dashboard')

    current_month = timezone.now().month
    current_year = timezone.now().year
    
    # Check if request already exists for this month
    is_submitted = NoCollectionRequest.objects.filter(
        resident=resident_profile,
        collection_month=current_month,
        collection_year=current_year
    ).exists()

    if request.method == 'POST' and not is_submitted:
        reason = request.POST.get('reason')
        
        NoCollectionRequest.objects.create(
            resident=resident_profile,
            collection_month=current_month,
            collection_year=current_year,
            reason=reason
        )
        
        # Admin is now notified this collection should be skipped
        messages.success(request, f"Collection skip request submitted for {current_month}/{current_year}. The worker will not visit.")
        return redirect('resident_dashboard')
    
    context = {
        'current_month_name': timezone.now().strftime("%B %Y"),
        'is_submitted': is_submitted,
        'reasons': NoCollectionRequest.reason.field.choices, # Pass choices to template
    }
    return render(request, 'residents/no_collection_request.html', context)