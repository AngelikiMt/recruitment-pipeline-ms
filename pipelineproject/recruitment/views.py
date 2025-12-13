from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Job, Candidate, Application, StageHistory, AuditLog
from .serializers import JobSerializer, CandidateSerializer, ApplicationSerializer, AuditLogSerializer


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer


class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all().select_related("candidate", "job").prefetch_related('stage_history')
    serializer_class = ApplicationSerializer

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):

        application = self.get_object()
        new_status = request.data.get("status")
        note = request.data.get("note", "")

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

        AuditLog.objects.create(
            actor=request.user if request.user.is_authenticated else None,
            verb="application_status_changed",
            target_type="Application",
            target_id=str(application.id),
            data={
                "old_status": application.status,
                "new_status": new_status,
                "note": note,
            },
        )

        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by("-timestamp")
    serializer_class = AuditLogSerializer


@api_view(['GET'])
def health_check(request):
    return Response({"status": "ok", "service": "Recruitment Pipeline API"}, status=status.HTTP_200_OK)