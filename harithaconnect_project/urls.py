# harithaconnect_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView # Import this for the redirect

# --- NEW/VERIFICATION IMPORTS ---
from django.conf import settings
from django.conf.urls.static import static 


# harithaconnect_project/urls.py (Update urlpatterns)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Redirect the root URL (/) to the resident login page
    path('', RedirectView.as_view(pattern_name='resident_login', permanent=False)),

    path('residents/', include('residents.urls')),

    # NEW: Include all URLs from the workers app under the 'workers/' prefix
    path('workers/', include('workers.urls')), # <-- ADD THIS LINE

    # harithaconnect_project/urls.py (Ensure this is in urlpatterns)
    path('dashboard-admin/', include('admin_dashboard.urls')),
]



# This is essential for serving user-uploaded files (proofs, photos) during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)