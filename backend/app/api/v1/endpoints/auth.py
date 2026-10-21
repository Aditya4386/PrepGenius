from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_student_id
from app.modules.auth.schemas import (
    StudentRegister,
    StudentLogin,
    TokenResponse,
    StudentAuthResponse,
)
from app.modules.auth.service import (
    register_student,
    authenticate_student,
    get_student_by_id,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: StudentRegister,
    db: Session = Depends(get_db),
):
    """Register a new student account and receive a signed JWT token."""
    student, token = register_student(db, data)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        student=StudentAuthResponse.model_validate(student),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    data: StudentLogin,
    db: Session = Depends(get_db),
):
    """Authenticate with registered email and password to receive a signed JWT token."""
    student, token = authenticate_student(db, data)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        student=StudentAuthResponse.model_validate(student),
    )


@router.get("/me", response_model=StudentAuthResponse)
def get_current_student_info(
    student_id: str = Depends(get_current_student_id),
    db: Session = Depends(get_db),
):
    """Retrieve details for the currently authenticated student."""
    student = get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student record not found.",
        )
    return StudentAuthResponse.model_validate(student)
