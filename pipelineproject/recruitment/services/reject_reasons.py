"""
Defines the official, approved reasons for rejecting an application.
This ensures consistency and standardization of rejection data across the system.
"""

REJECT_REASONS = {
    "culture_fit": "Not a culture fit",
    "technical_skills": "Insufficient technical skills",
    "experience": "Insufficient experience",
    "salary": "Salary expectations mismatch",
    "position_closed": "Position closed",
}

def validate_reject_reason(reason: str) -> None:
    """
    Checks if the provided reason code is one of the approved rejection reasons.
    """
    
    if reason not in REJECT_REASONS:
        raise ValueError("Invalid reject reason")
