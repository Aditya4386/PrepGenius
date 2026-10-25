"""
test_profile.py — Integration tests for profile endpoints.
"""

import pytest
from app.modules.profile.schemas import (
    ProfileUpdate,
    SkillItem,
    EducationItem,
    ProficiencyEnum,
    TargetRoleEnum,
    CompanyTypeEnum,
)


class TestProfileSchemas:
    """Unit tests for profile schemas."""

    def test_skill_item_validation(self):
        """Test SkillItem validation."""
        skill = SkillItem(name="Python", level=ProficiencyEnum.ADVANCED)
        assert skill.name == "Python"
        assert skill.level == ProficiencyEnum.ADVANCED

    def test_skill_item_empty_name_rejected(self):
        """Test that empty skill names are rejected."""
        with pytest.raises(ValueError):
            SkillItem(name="", level=ProficiencyEnum.BEGINNER)

    def test_education_item_validation(self):
        """Test EducationItem validation."""
        edu = EducationItem(
            institution="ABC University",
            degree="B.Tech Computer Science",
            year_of_completion=2024,
            cgpa=8.5,
        )
        assert edu.institution == "ABC University"
        assert edu.year_of_completion == 2024
        assert edu.cgpa == 8.5

    def test_education_item_invalid_year(self):
        """Test that invalid years are rejected."""
        with pytest.raises(ValueError):
            EducationItem(
                institution="ABC University",
                degree="B.Tech",
                year_of_completion=2050,  # > 2035
            )

    def test_profile_update_validation(self):
        """Test ProfileUpdate validation."""
        profile = ProfileUpdate(
            target_role=TargetRoleEnum.BACKEND_DEVELOPER,
            company_type=CompanyTypeEnum.PRODUCT,
            target_companies=["Google", "Microsoft"],
            career_goal="Become a backend engineer at a top tech company",
            weekly_study_hours=15.0,
            skills=[
                SkillItem(name="Python", level=ProficiencyEnum.ADVANCED),
                SkillItem(name="SQL", level=ProficiencyEnum.INTERMEDIATE),
            ],
            education=[
                EducationItem(
                    institution="ABC University",
                    degree="B.Tech Computer Science",
                    year_of_completion=2024,
                ),
            ],
        )
        assert profile.target_role == TargetRoleEnum.BACKEND_DEVELOPER
        assert profile.company_type == CompanyTypeEnum.PRODUCT
        assert len(profile.skills) == 2
        assert len(profile.education) == 1

    def test_weekly_hours_bounds(self):
        """Test weekly_study_hours bounds."""
        with pytest.raises(ValueError):
            ProfileUpdate(weekly_study_hours=0.5)  # < 1.0

        with pytest.raises(ValueError):
            ProfileUpdate(weekly_study_hours=100.0)  # > 80.0


class TestProfileEndpoints:
    """Integration tests for profile endpoints (require auth)."""

    def test_get_profile_with_mock_auth(self, client):
        """Test that profile endpoints work with dev mock auth."""
        response = client.get("/api/v1/profile")
        # DEV_MOCK_AUTH is enabled by default, so it returns a mock student profile
        assert response.status_code == 200
        data = response.json()
        assert "student_id" in data

    def test_update_profile_with_mock_auth(self, client):
        """Test that update profile works with dev mock auth."""
        response = client.put("/api/v1/profile", json={
            "target_role": "Backend Developer",
            "company_type": "product",
            "weekly_study_hours": 10.0,
            "skills": [{"name": "Python", "level": "advanced"}],
            "education": [{"institution": "Test Uni", "degree": "B.Tech", "year_of_completion": 2024}],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["target_role"] == "Backend Developer"


class TestTargetRoleEnum:
    """Test TargetRoleEnum values."""

    def test_all_roles_defined(self):
        """Test that all expected roles are defined."""
        expected_roles = [
            "BACKEND_DEVELOPER",
            "FULL_STACK_DEVELOPER",
            "DATA_ANALYST",
            "AI_ML_ENGINEER",
            "SOFTWARE_DEVELOPER",
            "FRONTEND_DEVELOPER",
            "DATA_SCIENTIST",
            "DEVOPS_ENGINEER",
        ]
        for role in expected_roles:
            assert hasattr(TargetRoleEnum, role)


class TestCompanyTypeEnum:
    """Test CompanyTypeEnum values."""

    def test_all_types_defined(self):
        assert CompanyTypeEnum.PRODUCT.value == "product"
        assert CompanyTypeEnum.SERVICE.value == "service"
        assert CompanyTypeEnum.STARTUP.value == "startup"