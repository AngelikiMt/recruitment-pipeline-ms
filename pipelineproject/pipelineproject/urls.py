from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('recruitments/', include ('recruitment.urls')),
    path('healthz/', include('recruitment.health_urls'))
]
