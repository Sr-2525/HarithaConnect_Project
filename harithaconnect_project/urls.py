from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView 
from django.views.generic import TemplateView

# --- NEW/VERIFICATION IMPORTS ---
from django.conf import settings
from django.conf.urls.static import static 


urlpatterns = [
    
    path('admin/', admin.site.urls),

    # CORRECT ROOT PATH: Renders the unified home.html template
    
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Removed the conflicting path('', RedirectView...)

    path('residents/', include('residents.urls')),

    path('workers/', include('workers.urls')),

    path('dashboard-admin/', include('admin_dashboard.urls')),
]


# This is essential for serving user-uploaded files (proofs, photos) during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)