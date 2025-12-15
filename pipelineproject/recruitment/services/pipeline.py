"""
Business logic for managing and validating application status transitions
in the recruitment pipeline.
"""
import logging
from django.core.exceptions import ValidationError
from typing import List, Dict

logger = logging.getLogger('recruitment')

PIPELINE_TRANSITIONS: Dict[str, List[str]] = {
    "applied": ["phone_screen", "rejected"],
    "phone_screen": ["onsite", "rejected"],
    "onsite": ["offer", "rejected"],
    "offer": ["hired", "rejected"],
    "hired": [],
    "rejected": [],
}


def validate_transition(application, new_status: str, user) -> None:
    """
    Validates whether a direct transition from current_status to new_status is allowed
    based on the PIPELINE_TRANSITIONS rules. 
    """
    
    current_status = application.status

    logger.debug(
        f"Transition attempt: User {user.username} from {current_status} to {new_status} for application ID: {application.id}"
    )

    allowed = PIPELINE_TRANSITIONS.get(current_status, [])

    if new_status not in allowed:
        logger.warning(
            f"Invalid transition blocked: {current_status} -> {new_status} for application ID: {application.id} by user: {user.username}"
        )
        raise ValidationError(
            f"Transition from '{current_status}' to '{new_status}' is not allowed."
        )

    logger.info(
        f"Transition Success: Application {application.id} status validated to be {new_status}"
    )
