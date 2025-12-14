"""
Business logic for managing and validating application status transitions
in the recruitment pipeline.
"""

from django.core.exceptions import ValidationError


PIPELINE_TRANSITIONS = {
    "applied": ["phone_screen", "rejected"],
    "phone_screen": ["onsite", "rejected"],
    "onsite": ["offer", "rejected"],
    "offer": ["hired", "rejected"],
    "hired": [],
    "rejected": [],
}


def validate_transition(current_status: str, new_status: str) -> None:
    """
    Validates whether a direct transition from current_status to new_status is allowed
    based on the PIPELINE_TRANSITIONS rules. 
    """
    
    allowed = PIPELINE_TRANSITIONS.get(current_status, [])

    if new_status not in allowed:
        raise ValidationError(
            f"Transition from '{current_status}' to '{new_status}' is not allowed."
        )
