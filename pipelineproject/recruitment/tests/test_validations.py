import pytest
from django.db import IntegrityError, transaction
from recruitment.models import Candidate, Job, Application


@pytest.mark.django_db
class TestApplicationValidations:
    """
    Tests for all validation rules defined on the Application model:
    1. Score range validation (Model's save method).
    2. Unique active application constraint (Database level).
    """

    def setup_method(self, method):
        """
        Sets up reusable Candidate and Job instances for all tests in this class.
        """
        self.candidate = Candidate.objects.create(
            full_name="Test Candidate Validation",
            email="validation@test.com"
        )
        self.job = Job.objects.create(title="Validation Engineer Role")

    def test_application_score_valid_range(self):
        """
        Verifies that scores within the 0-100 range are accepted by the model's save method.
        """
        Application.objects.create(
            candidate=self.candidate, job=self.job, score=0, status="applied"
        )
        self.job2 = Job.objects.create(title="Second Job")
        Application.objects.create(
            candidate=self.candidate, job=self.job2, score=100, status="applied"
        )
        self.job3 = Job.objects.create(title="Third Job")
        Application.objects.create(
            candidate=self.candidate, job=self.job3, score=50, status="applied"
        )

    def test_application_score_out_of_range_raises_error(self):
        """
        Verifies that scores outside the 0-100 range raise a ValueError 
        from the Application model's save method.
        """
        
        application_high = Application(
            candidate=self.candidate, job=self.job, score=150
        )
        with pytest.raises(ValueError, match="Score must be between values 0 and 100 included."):
            application_high.save()
            
        self.job_low = Job.objects.create(title="Low Score Test")
        application_low = Application(
            candidate=self.candidate, job=self.job_low, score=-5
        )
        with pytest.raises(ValueError, match="Score must be between values 0 and 100 included."):
            application_low.save()

    def test_unique_active_application_raises_integrity_error(self):
        """
        Verifies that creating a second active application for the same (candidate, job) pair fails 
        with IntegrityError (due to the database constraint).
        """
        
        Application.objects.create(
            candidate=self.candidate, job=self.job, status="applied"
        )

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                Application.objects.create(
                    candidate=self.candidate, job=self.job, status="phone_screen"
                )
        
    def test_new_application_allowed_after_rejection(self):
        """
        Verifies that a new application is allowed if the previous one was inactive ('rejected').
        """
        Application.objects.create(
            candidate=self.candidate, job=self.job, status="rejected"
        )
        
        self.job_retest = Job.objects.create(title="Re-application Job")
        
        Application.objects.create(
            candidate=self.candidate, job=self.job_retest, status="applied"
        )
        
        assert Application.objects.filter(candidate=self.candidate).count() == 2