"""
API Views for the Recruitment Pipeline Management System.
This module handles CRUD operations for Job, Candidate, Application, and AuditLog,
and enforces core business logic for application status transitions.
"""
from typing import Optional, Type

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.utils import timezone

from .models import Job, Candidate, Application, StageHistory, AuditLog
from .serializers import JobSerializer, CandidateSerializer, ApplicationSerializer, AuditLogSerializer
from .services.pipeline import validate_transition
from .services.reject_reasons import validate_reject_reason


class JobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Job listings (CRUD operations).
    Requires authentication for all operations.
    """
    queryset: QuerySet[Job] = Job.objects.all()
    serializer_class: Type[JobSerializer] = JobSerializer


class CandidateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Candidate profiles (CRUD operations).
    Requires authentication for all operations.
    """
    queryset: QuerySet[Candidate] = Candidate.objects.all()
    serializer_class: Type[CandidateSerializer] = CandidateSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Applications in the recruitment pipeline (CRUD operations).
    Includes a custom action for status updates to enforce pipeline rules.
    """
    queryset: QuerySet[Application] = Application.objects.all().select_related("candidate", "job").prefetch_related('stagehistory_set')
    serializer_class: Type[ApplicationSerializer] = ApplicationSerializer

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    logger = logging.getLogger('recruitment')

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request: Request, pk: Optional[str]=None) -> Response:
        """
        Updates the application status, enforcing pipeline transition rules
        and logging the change in StageHistory and AuditLog.

        Endpoint: PATCH /recruitments/applications/{id}/status/

        Request Body fields:
        - status (required): The new status (e.g., 'phone_screen', 'rejected', 'hired').
        - note (optional): A note justifying the status change.
        - reject_reason (required if status is 'rejected'): Standardized code (e.g., 'technical_skills').

        Raises:
            400 Bad Request: If the transition is invalid, the new status is invalid, 
                             or if 'rejected' is chosen without a valid 'reject_reason'.
        """

        application: Application = self.get_object()
        old_status: str = application.status

        new_status: Optional[str] = request.data.get("status")
        note: str = request.data.get("note", "")
        reject_reason: Optional[str] = request.data.get("reject_reason")

        valid_statuses = dict(Application.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({"detail": "Invalid status"}, status=400)

        try:
            validate_transition(application, new_status, request.user)

            if new_status == "rejected":
                if not reject_reason:
                    self.logger.warning(f"Reject attempt failed for App {pk}: Missing reject_reason.")
                    return Response(
                        {"detail": "reject_reason is required when rejecting an application"},
                        status=400
                    )
                validate_reject_reason(reject_reason)
            
            StageHistory.objects.create(application=application, stage=new_status, note=note)

            application.status = new_status
            if new_status == "hired":
                application.hired_at = timezone.now()

            application.save()

            user: AbstractUser = request.user
            actor: Optional[AbstractUser] = user if user.is_authenticated else None

            AuditLog.objects.create(
                actor=actor,
                verb="application_status_changed",
                target_type="Application",
                target_id=str(application.id),
                data={
                    "old_status": application.status,
                    "new_status": new_status,
                    "note": note,
                    "reject_reason": reject_reason,
                },
            )

            self.logger.info(f"API Success: Application {pk} status updated to {new_status} by user {request.user.username}")

            serializer: Serializer = self.get_serializer(application)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except (ValidationError, ValueError) as e:
            self.logger.warning(f"API Failure (400): Invalid data/transition request from user {request.user.username} on application: {pk}. Error: {e}")
            return Response({'error': str(e)}, status=400)
             
        except Exception as e:
            self.logger.error(f"API CRITICAL FAILURE: Unhandled exception on application: {pk}.", exc_info=True)
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing system-wide immutable Audit Logs.
    Only read operations are allowed. Logs are ordered by timestamp descending.
    """
    queryset: QuerySet[AuditLog] = AuditLog.objects.all().order_by("-timestamp")
    serializer_class: Type[AuditLogSerializer] = AuditLogSerializer


@api_view(['GET'])
def health_check(request: Request)-> Response:
    """
    Provides a simple readiness/liveness check for container deployment.
    Endpoint: GET /healthz/
    """
    return Response({"status": "ok", "service": "Recruitment Pipeline API"}, status=status.HTTP_200_OK)