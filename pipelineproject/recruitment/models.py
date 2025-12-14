"""
Database models for the Recruitment Pipeline Management System.
These models define the core entities (Job, Candidate, Application) and
the critical historical/observability entities (StageHistory, AuditLog).
"""
from typing import List, Tuple, Optional, Any

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone


User = get_user_model()


class Job(models.Model):
    """
    Represents a job opening available for recruitment.
    """
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=False)
    location = models.CharField(max_length=100, blank=False)
    hiring_manager = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title
    

class Candidate(models.Model):
    """
    Represents an individual applicant in the system.
    """
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    resume_url = models.URLField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} - {self.email}"
    

class Application(models.Model):
    """
    The core entity representing a candidate's progress through the recruitment pipeline
    for a specific job. Tracks status, score, and key dates.
    """
    STATUS_CHOICES: List[Tuple[str, str]] = [
        ("applied", "Applied"),
        ("phone_screen", "Phone Screen"),
        ("onsite", "Onsite"),
        ("offer", "Offer"),
        ("hired", "Hired"),
        ("rejected", "Rejected")
    ]

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="applied")
    score = models.IntegerField(null=True, blank=True)
    applied_at = models.DateTimeField(default=timezone.now)
    hired_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints: List[models.UniqueConstraint] = [
            models.UniqueConstraint(fields=['candidate', 'job'], condition=models.Q(status__in=['applied','phone_screen','onsite','offer']), name='unique_active_application')
        ]

    def days_to_hire(self) -> Optional[int]:
        """
        Calculates the total number of days taken to hire the candidate 
        from the application date.
        """
        if self.hired_at:
            return (self.hired_at - self.applied_at).days
        return None
    
    def current_time_in_stage(self) -> Optional[float]:
        """
        Calculates the duration (in seconds) since the last status transition
        """
        last: models.QuerySet[StageHistory] = self.stagehistory_set.order_by("-entered_at").first()
        if not last:
            return None
        return (timezone.now() - last.entered_at).total_seconds()
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Overrides save() to perform custom validation checks before saving the instance.
        Ensures the score is within the 0-100 range.
        """
        if self.score is not None and not (0 <= self.score <= 100):
            raise ValueError("Score must be between values 0 and 100 included.")
        super().save(*args, **kwargs)


class StageHistory(models.Model):
    """
    Immutable log of every status transition for a specific Application.
    """
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    stage = models.CharField(max_length=50)
    entered_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.application_id} moved to {self.stage} at {self.entered_at.isoformat()}"
    

class AuditLog(models.Model):
    """
    System-wide, immutable log of user actions (who, did what, to which entity, when).
    Critical for compliance, debugging, and general observability.
    """
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    verb = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=dict)

    class Meta:
        indexes: List[models.Index] = [models.Index(fields=["target_type", "target_id"])]

    def __str__(self) -> str:
        return f"{self.timestamp} {self.verb} {self.target_type}:{self.target_id}"