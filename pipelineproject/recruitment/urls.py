from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views


router = DefaultRouter()

router.register('jobs', views.JobViewSet, basename='job')
router.register('candidates', views.CandidateViewSet, basename='candidate')
router.register('applications', views.ApplicationViewSet, basename='application')
router.register('auditlogs', views.AuditLogViewSet, basename='auditlog')

urlpatterns = [
    path('', include(router.urls)),
]