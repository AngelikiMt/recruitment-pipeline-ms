import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from recruitment.services.pipeline import validate_transition
from recruitment.services.reject_reasons import validate_reject_reason
from recruitment.models import Application, Job, Candidate


@pytest.fixture
def test_user(db):
    return User.objects.create_user(username="test_recruiter", password="rec123")

@pytest.fixture
def initial_application(db):
    job = Job.objects.create(title="Python Developer", is_open=True)
    candidate = Candidate.objects.create(full_name="John", email="john@example.com")
    return Application.objects.create(
        job=job, 
        candidate=candidate, 
        status="applied"
    )

@pytest.mark.django_db
class TestPipelineServices:

    """Tests for validate_transition."""
    def test_transition_valid(self, test_user, initial_application):
        validate_transition(initial_application, "phone_screen", user=test_user)

    def test_transition_invalid(self, test_user, initial_application):
        with pytest.raises(ValidationError) as excinfo:
            validate_transition(initial_application, "onsite", user=test_user)
        assert "Transition from 'applied' to 'onsite' is not allowed" in str(excinfo.value)


    """Tests for validate_reject_reason."""

    def test_reject_reason_valid(self):
        validate_reject_reason("culture_fit")

    def test_reject_reason_invalid(self):
        with pytest.raises(ValueError) as excinfo:
            validate_reject_reason("poor_attitude")
        assert "Invalid reject reason" in str(excinfo.value)