import uuid
from typing import Tuple, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.modules.profile.models import Student, StudentProfile
from app.modules.auth.schemas import StudentRegister, StudentLogin
from app.modules.auth.security import hash_password, verify_password, create_access_token


def register_student(db: Session, data: StudentRegister) -> Tuple[Student, str]:
    """Registers a new student, hashes password with bcrypt, and initializes profile."""
    email_clean = data.email.lower().strip()

    # Check for existing account
    existing = db.query(Student).filter(Student.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this email address is already registered.",
        )

    # Generate unique student ID and hashed password
    student_id = f"std_{uuid.uuid4().hex[:12]}"
    hashed_pwd = hash_password(data.password)

    student = Student(
        id=student_id,
        email=email_clean,
        full_name=data.full_name.strip(),
        hashed_password=hashed_pwd,
        is_active=True,
    )
    db.add(student)
    db.flush()

    # Initialize associated profile record
    profile = StudentProfile(
        id=str(uuid.uuid4()),
        student_id=student.id,
        target_role=None,
        company_type=None,
        target_companies=[],
        career_goal=None,
        weekly_study_hours=10.0,
        preparation_deadline=None,
        skills=[],
        education=[],
    )
    db.add(profile)
    db.commit()
    db.refresh(student)

    # Issue access token
    token = create_access_token(student_id=student.id, email=student.email)
    return student, token


def authenticate_student(db: Session, data: StudentLogin) -> Tuple[Student, str]:
    """Authenticates student credentials and issues a signed JWT token."""
    email_clean = data.email.lower().strip()
    student = db.query(Student).filter(Student.email == email_clean).first()

    if not student or not verify_password(data.password, student.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not student.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This student account has been deactivated.",
        )

    token = create_access_token(student_id=student.id, email=student.email)
    return student, token


def get_student_by_id(db: Session, student_id: str) -> Optional[Student]:
    """Retrieves student by authenticated ID."""
    return db.query(Student).filter(Student.id == student_id).first()
