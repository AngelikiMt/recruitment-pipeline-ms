import pytest
from django.utils import timezone
from recruitment.models import Candidate, Job, Application, StageHistory
from datetime import timedelta
from typing import Optional
from django.db import IntegrityError
from django.db import transaction

@pytest.mark.django_db
class TestApplicationCalculatedFields:
    """
    Tests for calculated fields and business logic on the Application model.
    """

    def setup_method(self, method):
        self.candidate = Candidate.objects.create(
            full_name="Angeliki Matta",
            email="angeliki_test@example.com"
        )
        self.job = Job.objects.create(title="Backend Engineer")
        
        self.applied_time = timezone.now() - timedelta(days=15)
        self.hire_time = self.applied_time + timedelta(days=10)

        self.application = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            applied_at=self.applied_time,
            status="applied"
        )
        StageHistory.objects.create(
            application=self.application,
            stage="applied",
            entered_at=self.applied_time
        )


    def test_days_to_hire_hired_case(self):
        """Checks the correct calculation when the candidate has been hired."""
        
        self.application.hired_at = self.hire_time
        self.application.save()
        
        days_to_hire: Optional[int] = self.application.days_to_hire()
        
        assert days_to_hire == 10
        assert isinstance(days_to_hire, int)

    def test_days_to_hire_not_hired_case(self):
        """Checks that None is returned when the candidate has not been hired."""
        
        days_to_hire: Optional[int] = self.application.days_to_hire()
        
        assert days_to_hire is None

    def test_current_time_in_stage_calculation(self, monkeypatch):
        """Controls time rewind to current stage (uses monkeypatch to freeze time)."""
        fake_now = self.applied_time + timedelta(days=5, seconds=10)
        
        monkeypatch.setattr(timezone, 'now', lambda: fake_now)

        StageHistory.objects.create(
            application=self.application,
            stage="phone_screen",
            entered_at=self.applied_time + timedelta(days=5)
        )

        seconds: Optional[float] = self.application.current_time_in_stage()
        
        assert seconds is not None
        assert 9.0 < seconds < 11.0


"""
Tests for the Unique Constraint
"""

from django.db import IntegrityError

@pytest.mark.django_db
def test_unique_active_application_constraint():
    """Checks that there cannot be two active applications for the same Candidate/Job."""

    candidate = Candidate.objects.create(full_name="Test Candidate", email="unique@test.com")
    job = Job.objects.create(title="Test Job")

    Application.objects.create(candidate=candidate, job=job, status="applied")

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Application.objects.create(candidate=candidate, job=job, status="phone_screen")

    Application.objects.filter(job=job).update(status="rejected") 
    Application.objects.create(candidate=candidate, job=job, status="applied")

    assert Application.objects.count() == 2