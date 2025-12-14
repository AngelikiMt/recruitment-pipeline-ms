import pytest
from django.core.exceptions import ValidationError
from recruitment.services.pipeline import validate_transition
from recruitment.services.reject_reasons import validate_reject_reason


"""Tests for validate_transition."""


def test_transition_valid():
    validate_transition("applied", "phone_screen") 
    validate_transition("onsite", "offer") 

def test_transition_invalid():
    with pytest.raises(ValidationError) as excinfo:
        validate_transition("applied", "onsite")
    assert "Transition from 'applied' to 'onsite' is not allowed" in str(excinfo.value)


"""Tests for validate_reject_reason."""

def test_reject_reason_valid():
    validate_reject_reason("culture_fit")

def test_reject_reason_invalid():
    with pytest.raises(ValueError) as excinfo:
        validate_reject_reason("poor_attitude")
    assert "Invalid reject reason" in str(excinfo.value)