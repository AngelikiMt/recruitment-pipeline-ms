from typing import Optional, Type

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from django.db.models.query import QuerySet
from django.contrib.auth.models import AbstractUser

from .models import Job, Candidate, Application, StageHistory, AuditLog
from .serializers import JobSerializer, CandidateSerializer, ApplicationSerializer, AuditLogSerializer


class JobViewSet(viewsets.ModelViewSet):
    queryset: QuerySet[Job] = Job.objects.all()
    serializer_class: Type[JobSerializer] = JobSerializer


class CandidateViewSet(viewsets.ModelViewSet):
    queryset: QuerySet[Candidate] = Candidate.objects.all()
    serializer_class: Type[CandidateSerializer] = CandidateSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset: QuerySet[Application] = Application.objects.all().select_related("candidate", "job").prefetch_related('stagehistory_set')
    serializer_class: Type[ApplicationSerializer] = ApplicationSerializer

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request: Request, pk: Optional[str]=None) -> Response:

        application: Application = self.get_object()
        new_status: Optional[str] = request.data.get("status")
        note: str = request.data.get("note", "")

        valid_statuses = dict(Application.STATUS_CHOICES).keys()

        if new_status not in valid_statuses:
            return Response(
                {"detail": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )

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
            },
        )

        serializer: Serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset: QuerySet[AuditLog] = AuditLog.objects.all().order_by("-timestamp")
    serializer_class: Type[AuditLogSerializer] = AuditLogSerializer


@api_view(['GET'])
def health_check(request: Request)-> Response:
    return Response({"status": "ok", "service": "Recruitment Pipeline API"}, status=status.HTTP_200_OK)