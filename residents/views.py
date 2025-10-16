# residents/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# residents/views.py (Update the import line)
from .forms import BinFullAlertForm, ResidentComplaintForm, OfflinePaymentForm # <-- ADD OfflinePaymentForm
from .models import ResidentProfile, BinFullAlert, ResidentComplaint, Payment, BillingDue # Import Payment model too
# ... other imports
# ORIGINAL (or similar)


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

@login_required(login_url='resident_login')
def pay_waste_fee(request):
    try:
        resident_profile = request.user.residentprofile
    except ResidentProfile.DoesNotExist:
        messages.error(request, "Access Denied: Profile not found.")
        return redirect('resident_dashboard')
        
    # --- Get the Current Pending Due ---
    pending_due = BillingDue.objects.filter(
        resident=resident_profile, 
        is_paid=False
    ).order_by('due_date').first()
    
    if pending_due:
        current_due_amount = pending_due.amount_due
    else:
        current_due_amount = 0.00
    
    # --- START: Handle Offline Payment Submission (Your POST block goes here) ---
    if request.method == 'POST':
        # Check if there is an amount due to be paid against
        if current_due_amount == 0:
            messages.error(request, "You have no outstanding dues to report a payment against.")
            return redirect('pay_waste_fee')
        
        # IMPORTANT: Pass request.FILES for the photo upload!
        form = OfflinePaymentForm(request.POST, request.FILES)
        
        if form.is_valid():
            paid_amount = form.cleaned_data['amount']
            
            # Check if the reported payment matches the outstanding due amount
            if paid_amount != current_due_amount:
                 messages.error(request, f"Reported amount ({paid_amount}) does not match the outstanding due amount ({current_due_amount}). Please pay the exact amount.")
                 return redirect('pay_waste_fee')
            
            # Create the Payment record
            payment = form.save(commit=False)
            payment.resident = resident_profile
            payment.is_paid_online = False
            payment.save()
            
            # CRUCIAL STEP: Mark the corresponding BillingDue record as paid
            if pending_due:
                pending_due.is_paid = True
                pending_due.save()
            
            messages.success(request, f"Offline payment of ₹{paid_amount} reported successfully! Due marked as paid. Worker confirmation pending.")
            return redirect('resident_dashboard')
        else:
            messages.error(request, "Error in payment details. Please check the amount, receipt number, and ensure a photo is attached.")
    
    # --- END: Handle Offline Payment Submission ---
    
    
    # --- Handle GET Request (Display the page) ---
    else:
        # GET request: Display a blank form, pre-filled with the due amount if one exists
        form = OfflinePaymentForm(initial={'amount': current_due_amount})
        
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
@login_required(login_url='resident_login')
def resident_history(request):
    try:
        resident_profile = request.user.residentprofile
    except ResidentProfile.DoesNotExist:
        messages.error(request, "Access Denied: Profile not found.")
        return redirect('resident_dashboard')

    # 1. Fetch all records related to the resident, ordered by creation time
    alerts = BinFullAlert.objects.filter(resident=resident_profile).order_by('-alert_time')
    complaints = ResidentComplaint.objects.filter(resident=resident_profile).order_by('-submission_time')
    payments = Payment.objects.filter(resident=resident_profile).order_by('-payment_date')

    # 2. Consolidate and sort all activities for a timeline view (optional, but good practice)
    # For simplicity, we'll pass the lists separately and display them in different tabs/sections.

    context = {
        'alerts': alerts,
        'complaints': complaints,
        'payments': payments,
    }
    return render(request, 'residents/history.html', context)