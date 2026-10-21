from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TargetRoleEnum(str, Enum):
    # Software Engineering & Core Development
    SOFTWARE_DEVELOPER = "Software Developer"
    SDE = "Software Engineer (SDE)"
    BACKEND_DEVELOPER = "Backend Developer"
    FRONTEND_DEVELOPER = "Frontend Developer"
    FULL_STACK_DEVELOPER = "Full-Stack Developer"
    JAVA_DEVELOPER = "Java Developer"
    PYTHON_DEVELOPER = "Python Developer"
    WEB_DEVELOPER = "Web Developer"
    MOBILE_APP_DEVELOPER = "Mobile App Developer"
    ANDROID_DEVELOPER = "Android Developer"
    IOS_DEVELOPER = "iOS Developer"
    DATABASE_DEVELOPER = "Database Developer"

    # Data & Artificial Intelligence
    DATA_ANALYST = "Data Analyst"
    DATA_SCIENTIST = "Data Scientist"
    DATA_ENGINEER = "Data Engineer"
    BUSINESS_ANALYST = "Business Analyst"
    BI_ANALYST = "Business Intelligence Analyst"
    AI_ML_ENGINEER = "AI/ML Engineer"
    ML_ENGINEER = "Machine Learning Engineer"
    GEN_AI_ENGINEER = "Generative AI Engineer"

    # Cloud, DevOps & Security
    CLOUD_ENGINEER = "Cloud Engineer"
    DEVOPS_ENGINEER = "DevOps Engineer"
    SRE = "Site Reliability Engineer (SRE)"
    CLOUD_ARCHITECT = "Cloud Solutions Architect"
    CYBERSECURITY_ANALYST = "Cybersecurity Analyst"

    # Quality Assurance & Testing
    QA_ENGINEER = "QA Engineer"
    AUTOMATION_TEST_ENGINEER = "Automation Test Engineer"
    SDET = "Software Development Engineer in Test (SDET)"

    # Specialized Domains & Enterprise
    BLOCKCHAIN_DEVELOPER = "Blockchain Developer"
    GAME_DEVELOPER = "Game Developer"
    EMBEDDED_ENGINEER = "Embedded Software Engineer"
    SALESFORCE_DEVELOPER = "Salesforce Developer"
    SAP_CONSULTANT = "SAP Consultant"

    # Design & Product Management
    UI_UX_DESIGNER = "UI/UX Designer"
    PRODUCT_MANAGER = "Product Manager"
    TECHNICAL_PROGRAM_MANAGER = "Technical Program Manager"


class CompanyTypeEnum(str, Enum):
    PRODUCT = "product"
    SERVICE = "service"
    STARTUP = "startup"


class ProficiencyEnum(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SkillItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of technical skill")
    level: ProficiencyEnum = Field(default=ProficiencyEnum.INTERMEDIATE, description="Skill proficiency")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Skill name cannot be empty")
        return cleaned


class EducationItem(BaseModel):
    institution: str = Field(..., min_length=1, max_length=200, description="University / College name")
    degree: str = Field(..., min_length=1, max_length=100, description="Degree or diploma (e.g., B.Tech IT)")
    year_of_completion: Optional[int] = Field(None, ge=1970, le=2035, description="Graduation year")
    cgpa: Optional[float] = Field(None, ge=0.0, le=10.0, description="CGPA or percentage out of 10")


class ProfileBase(BaseModel):
    target_role: Optional[TargetRoleEnum] = None
    company_type: Optional[CompanyTypeEnum] = None
    target_companies: List[str] = Field(default_factory=list, description="Target companies (e.g. Google, TCS)")
    career_goal: Optional[str] = Field(None, max_length=1000, description="Brief career objective")
    weekly_study_hours: Optional[float] = Field(
        default=10.0,
        ge=1.0,
        le=80.0,
        description="Available weekly study hours for roadmap feasibility",
    )
    preparation_deadline: Optional[date] = Field(
        None,
        description="Target completion deadline date (YYYY-MM-DD)",
    )
    skills: List[SkillItem] = Field(default_factory=list, description="List of evaluated skills")
    education: List[EducationItem] = Field(default_factory=list, description="Academic background records")


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: str
    student_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_profile_complete: bool = False

    model_config = {"from_attributes": True}


class StudentResponse(BaseModel):
    id: str
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    profile: Optional[ProfileResponse] = None

    model_config = {"from_attributes": True}
