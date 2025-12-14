"""
Serializers for the Recruitment Pipeline API.
These handle data validation, formatting, and conversion between Django models and JSON representations.
Custom logic includes pipeline history embedding and complex validation rules (e.g., uniqueness, score range).
"""
from typing import Tuple, Optional, Dict, Any
from django.db.models import Model

from rest_framework import serializers
from .models import Job, Candidate, Application, StageHistory, AuditLog


class JobSerializer(serializers.ModelSerializer):
    """
    Serializer for the Job model.
    Handles basic CRUD serialization for job postings.
    """
    class Meta:
        model: Model = Job
        fields: Tuple[Any] = '__all__'


class CandidateSerializer(serializers.ModelSerializer):
    """
    Serializer for the Candidate model.
    Handles basic CRUD serialization for candidate profiles.
    """
    class Meta:
        model: Model = Candidate
        fields: Tuple[Any] = '__all__'


class StageHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for the StageHistory model.
    Used primarily for read-only embedding within the ApplicationSerializer
    to show the complete stage history.
    """
    class Meta:
        model: Model = StageHistory
        fields: Tuple[Any] = ('id','stage','entered_at','note')


class ApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Application model.
    Includes custom fields and complex validation logic:
    1. Embeds read-only StageHistory.
    2. Calculates days_to_hire dynamically.
    3. Enforces unique active application constraint per candidate/job pair.
    4. Enforces score range validation (0-100).
    """
    stage_history = StageHistorySerializer(many=True, read_only=True)
    days_to_hire = serializers.SerializerMethodField()

    class Meta:
        model: Model = Application
        fields: Tuple[Any] = ('id','candidate','job','status','score','applied_at','hired_at','days_to_hire','stage_history')

    def get_days_to_hire(self, obj: Application) -> Optional[int]:
        return obj.days_to_hire()

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self.instance is None:
            candidate: Candidate = data.get('candidate')
            job: Job = data.get('job')

            from .models import Application as AppModel

            exists: bool = AppModel.objects.filter(candidate=candidate, job=job).exclude(status__in=('rejected','hired')).exists()

            if exists:
                raise serializers.ValidationError('Candidate already has an active application for this job')
            
        score: Optional[int] = data.get('score')
        if score is not None and not (0 <= score <= 100):
            raise serializers.ValidationError('Score must be between values 0 and 100 included.')
        
        return data


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for the AuditLog model.
    Used for reading the system's immutable log of actions.
    """
    class Meta:
        model: Model = AuditLog
        fields: Tuple[Any] = '__all__'