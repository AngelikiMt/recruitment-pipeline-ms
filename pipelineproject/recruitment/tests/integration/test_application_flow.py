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


@pytest.fixture
def initial_application(db):
    """Δημιουργεί Job, Candidate, και μια αρχική Application."""
    from recruitment.models import Job, Candidate, Application
    
    job = Job.objects.create(
        title="Test Job",
        department="Test Dept",
        location="Remote"
    )

    candidate = Candidate.objects.create(
        full_name="Initial Test User",
        email="initial@test.com"
    )

    application = Application.objects.create(
        candidate=candidate,
        job=job,
        status="applied"
    )
    return application


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

    expected_status_phone = auth_client.patch(
        f"/recruitments/applications/{application_id}/status/",
        {
            "status": "phone_screen",
            "note": "Passed CV review, moving to phone screening"
        },
        format="json"
    )

    assert expected_status_phone.status_code == 200

    expected_status_onsite = auth_client.patch(
        f"/recruitments/applications/{application_id}/status/",
        {
            "status": "onsite",
            "note": "Passed phone screen"
        },
        format="json"
    )

    assert expected_status_onsite.status_code == 200

    expected_offer = auth_client.patch(
        f"/recruitments/applications/{application_id}/status/",
        {
            "status": "offer",
            "note": "Great interview, proposing offer."
        },
        format="json"
    )

    assert expected_offer.status_code == 200

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
    assert history.count() == 4
    assert history.last().stage == "hired"

    logs = AuditLog.objects.filter(target_id=str(application_id)).order_by('timestamp')
    assert logs.count() == 4

    last_log = logs.last()
    assert last_log.actor.username == "recruiter"
    assert "hired" in last_log.data['new_status']


@pytest.mark.django_db
def test_transition_failure_on_invalid_status(auth_client, initial_application):
    """Tests that the API rejects an invalid transition (eg., applied -> offer)."""
    
    app_id = initial_application.id
    
    resp = auth_client.patch(
        f"/recruitments/applications/{app_id}/status/",
        {
            "status": "offer",
            "note": "Skipping steps"
        },
        format="json"
    )
    assert resp.status_code == 400
    assert "Transition from 'applied' to 'offer' is not allowed" in resp.data["detail"]


@pytest.mark.django_db
def test_reject_requires_reason(auth_client, initial_application):
    """Checks that rejection requires 'reject_reason'."""
    
    app_id = initial_application.id
    
    resp = auth_client.patch(
        f"/recruitments/applications/{app_id}/status/",
        {
            "status": "rejected", 
            "note": "CV not good enough"
        },
        format="json"
    )
    assert resp.status_code == 400
    assert "reject_reason is required" in resp.data["detail"]

    resp_invalid = auth_client.patch(
        f"/recruitments/applications/{app_id}/status/",
        {
            "status": "rejected", 
            "note": "CV not good enough",
            "reject_reason": "unknown_code"
        },
        format="json"
    )
    assert resp_invalid.status_code == 400
    assert "Invalid reject reason" in resp_invalid.data["detail"]