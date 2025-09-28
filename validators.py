from pydantic import BaseModel, EmailStr, ValidationError, Field, validator
import re

class CandidateDetails(BaseModel):
    full_name: str = Field(..., min_length=2, description="Full name must be at least 2 characters.")
    email: EmailStr
    phone_number: str
    experience: int = Field(..., ge=0, description="Years of experience cannot be negative.")
    desired_position: str = Field(..., min_length=2, description="Desired position must be at least 2 characters.")
    current_location: str = Field(..., min_length=2, description="Location must be at least 2 characters.")
    tech_stack: str = Field(..., min_length=2, description="Tech stack cannot be empty.")

    @validator('phone_number')
    def validate_phone_number(cls, v):
        """
        Validates a phone number.
        This is a simple regex that checks for 10-15 digits, allowing for optional
        spaces, hyphens, parentheses, and a leading '+'.
        """
        phone_regex = re.compile(r"^\+?[\d\s\-\(\)]{10,15}$")
        if not phone_regex.match(v):
            raise ValueError('Invalid phone number format.')
        return v

def validate_form(details: dict):
    """
    Validates a dictionary of form details against the CandidateDetails model.
    Returns a tuple: (bool, list_of_errors | None).
    """
    try:
        CandidateDetails(**details)
        return True, None  # Validation successful
    except ValidationError as e:
        # Format errors into a user-friendly list of strings
        error_messages = [f"{err['loc'][0].replace('_', ' ').title()}: {err['msg']}" for err in e.errors()]
        return False, error_messages
