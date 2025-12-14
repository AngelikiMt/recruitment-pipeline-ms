import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from recruitment.models import Application, StageHistory, AuditLog


@pytest.fixture
def auth_client():
    user = User.objects.create_user(
        username="recruiter",
        password="strong-password"
    )
    refresh = RefreshToken.for_user(user)

    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}"
    )
    return client


@pytest.mark.django_db
def test_full_recruitment_flow(auth_client):
    """
    Job -> Candidate -> Application -> Status transitions -> Hire
    """

    expected = auth_client.post(
        "/recruitments/jobs/",
        {
            "title": "Backend Engineer",
            "department": "Engineering",
            "location": "Remote"
        },
        format="json"
    )
    assert expected.status_code == 201
    job_id = expected.data["id"]

    expected_resp = auth_client.post(
        "/recruitments/candidates/",
        {
            "full_name": "Angeliki Matta",
            "email": "angeliki@example.com"
        },
        format="json"
    )
    assert expected_resp.status_code == 201
    candidate_id = expected_resp.data["id"]

    expected_appl = auth_client.post(
        "/recruitments/applications/",
        {
            "candidate": candidate_id,
            "job": job_id,
            "score": 85
        },
        format="json"
    )
    assert expected_appl.status_code == 201
    application_id = expected_appl.data["id"]

    expected_status = auth_client.patch(
        f"/recruitments/applications/{application_id}/status/",
        {
            "status": "phone_screen",
            "note": "Passed CV review"
        },
        format="json"
    )
    assert expected_status.status_code == 200

    expected_hire = auth_client.patch(
        f"/recruitments/applications/{application_id}/status/",
        {
            "status": "hired",
            "note": "Excellent interview"
        },
        format="json"
    )
    assert expected_hire.status_code == 200

    application = Application.objects.get(id=application_id)
    assert application.status == "hired"
    assert application.hired_at is not None

    history = StageHistory.objects.filter(application=application)
    assert history.count() == 2
    assert history.last().stage == "hired"

    logs = AuditLog.objects.filter(target_id=str(application_id)).order_by('timestamp')
    assert logs.count() == 2

    last_log = logs.last()
    assert last_log.actor.username == "recruiter"
    assert "hired" in last_log.data['new_status']