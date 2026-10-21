from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class StudentRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Student full name")
    email: EmailStr = Field(..., description="Student college/personal email")
    password: str = Field(..., min_length=6, max_length=128, description="Account password (min 6 chars)")


class StudentLogin(BaseModel):
    email: EmailStr = Field(..., description="Registered email")
    password: str = Field(..., description="Account password")


class StudentAuthResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student: StudentAuthResponse
