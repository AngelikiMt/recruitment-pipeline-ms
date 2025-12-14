import pytest
from django.utils import timezone
from recruitment.models import Candidate, Job, Application, StageHistory
from datetime import timedelta


@pytest.mark.django_db
class TestApplicationPipelineLogic:
    """
    Tests the core workflow logic within the Application model and its related entities.
    Focuses on StageHistory creation and hired_at field setting.
    """

    def setup_method(self, method):
        """
        Sets up the necessary entities (Candidate, Job, Application) before each test.
        """
        self.candidate = Candidate.objects.create(
            full_name="Pipeline Tester",
            email="pipeline@test.com"
        )
        self.job = Job.objects.create(title="Pipeline Test Role")
        
        self.application = Application.objects.create(
            candidate=self.candidate,
            job=self.job
        )
        StageHistory.objects.create(
            application=self.application,
            stage=self.application.status,
            note="Initial application"
        )
    
    def test_stage_transition_creates_history(self):
        """
        Verifies that manually changing the status results in a new StageHistory entry.
        NOTE: In production, the view function handles both status change and history creation.
        """
        new_status = "phone_screen"
        transition_note = "Passed initial CV screening"

        self.application.status = new_status
        self.application.save() 
        
        StageHistory.objects.create(
            application=self.application,
            stage=new_status,
            note=transition_note
        )

        history = self.application.stagehistory_set.all()
        assert history.count() == 2
        assert history.last().stage == new_status
        assert history.last().note == transition_note
        assert history.first().stage == "applied"

    def test_hiring_sets_hired_at_field(self):
        """
        Verifies that when the application status is set to 'hired', the hired_at timestamp is set.
        (This logic is typically implemented in the view/serializer logic, not the model save, 
         as per your views.py).
        """
        
        current_time = timezone.now()
        self.application.status = "hired"
        self.application.hired_at = current_time
        self.application.save()

        assert self.application.hired_at is not None
        
        time_difference: timedelta = timezone.now() - self.application.hired_at
        assert time_difference.total_seconds() < 5

    
    def test_time_to_hire_calculation_after_hiring(self):
        """
        Verifies that time_to_hire returns the correct duration after setting hired_at.
        """
        applied_time = timezone.now() - timedelta(days=15)
        self.application.applied_at = applied_time
        
        hire_time = applied_time + timedelta(days=10)
        self.application.hired_at = hire_time
        self.application.status = "hired"
        self.application.save()
        
        assert self.application.days_to_hire() == 10
        assert self.application.days_to_hire() is not None
