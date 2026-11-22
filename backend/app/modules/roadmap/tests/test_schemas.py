"""
test_schemas.py — Unit tests for roadmap Pydantic schemas.

Run: uv run pytest app/modules/roadmap/tests/test_schemas.py -v
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from app.modules.roadmap.schemas import (
    RoadmapTaskBase,
    RoadmapTaskUpdate,
    RoadmapTaskResponse,
    RoadmapPhaseBase,
    RoadmapPhaseResponse,
    RoadmapBase,
    RoadmapResponse,
    RoadmapGenerationRequest,
    RoadmapAdaptationResponse,
    RoadmapAdaptationAction,
    TaskCompletionRequest,
    TaskStatusEnum,
    SourceTypeEnum,
    AdaptationStatusEnum,
)

from app.modules.profile.schemas import (
    ProficiencyEnum,
    TargetRoleEnum,
    CompanyTypeEnum,
    SkillItem,
    EducationItem,
)


class TestEnums:
    """Test enum values."""

    def test_task_status_enum(self):
        assert TaskStatusEnum.PENDING.value == "pending"
        assert TaskStatusEnum.COMPLETED.value == "completed"

    def test_source_type_enum(self):
        assert SourceTypeEnum.GENERATED.value == "generated"
        assert SourceTypeEnum.INTERVIEW.value == "interview"
        assert SourceTypeEnum.RESUME.value == "resume"

    def test_adaptation_status_enum(self):
        assert AdaptationStatusEnum.PROPOSED.value == "proposed"
        assert AdaptationStatusEnum.APPLIED.value == "applied"
        assert AdaptationStatusEnum.REJECTED.value == "rejected"

    def test_proficiency_enum(self):
        assert ProficiencyEnum.BEGINNER.value == "beginner"
        assert ProficiencyEnum.INTERMEDIATE.value == "intermediate"
        assert ProficiencyEnum.ADVANCED.value == "advanced"

    def test_target_role_enum_has_expected_roles(self):
        expected = ["BACKEND_DEVELOPER", "FULL_STACK_DEVELOPER", "DATA_ANALYST", "AI_ML_ENGINEER"]
        for role in expected:
            assert hasattr(TargetRoleEnum, role)

    def test_company_type_enum(self):
        assert CompanyTypeEnum.PRODUCT.value == "product"
        assert CompanyTypeEnum.SERVICE.value == "service"
        assert CompanyTypeEnum.STARTUP.value == "startup"


class TestSkillItem:
    """Test SkillItem schema."""

    def test_valid_skill_item(self):
        skill = SkillItem(name="Python", level=ProficiencyEnum.ADVANCED)
        assert skill.name == "Python"
        assert skill.level == ProficiencyEnum.ADVANCED

    def test_skill_default_level_is_intermediate(self):
        skill = SkillItem(name="Python")
        assert skill.level == ProficiencyEnum.INTERMEDIATE

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            SkillItem(name="", level=ProficiencyEnum.BEGINNER)

    def test_whitespace_name_rejected(self):
        with pytest.raises(ValidationError):
            SkillItem(name="   ", level=ProficiencyEnum.BEGINNER)

    def test_name_stripped(self):
        skill = SkillItem(name="  Python  ", level=ProficiencyEnum.BEGINNER)
        assert skill.name == "Python"


class TestEducationItem:
    """Test EducationItem schema."""

    def test_valid_education_item(self):
        edu = EducationItem(
            institution="ABC University",
            degree="B.Tech Computer Science",
            year_of_completion=2024,
            cgpa=8.5,
        )
        assert edu.institution == "ABC University"
        assert edu.year_of_completion == 2024
        assert edu.cgpa == 8.5

    def test_optional_fields_can_be_none(self):
        edu = EducationItem(institution="Uni", degree="B.Tech")
        assert edu.year_of_completion is None
        assert edu.cgpa is None

    def test_invalid_year_too_high_rejected(self):
        with pytest.raises(ValidationError):
            EducationItem(institution="Uni", degree="B.Tech", year_of_completion=2050)

    def test_invalid_year_too_low_rejected(self):
        with pytest.raises(ValidationError):
            EducationItem(institution="Uni", degree="B.Tech", year_of_completion=1960)

    def test_cgpa_out_of_bounds_rejected(self):
        with pytest.raises(ValidationError):
            EducationItem(institution="Uni", degree="B.Tech", cgpa=11.0)
        with pytest.raises(ValidationError):
            EducationItem(institution="Uni", degree="B.Tech", cgpa=-1.0)


class TestRoadmapTaskSchemas:
    """Test task-related schemas."""

    def test_task_base_valid(self):
        task = RoadmapTaskBase(
            title="Learn Python",
            estimated_hours=4.0,
            success_criteria="Complete tutorial",
            topic_tags=["python", "basics"],
        )
        assert task.title == "Learn Python"
        assert task.estimated_hours == 4.0
        assert task.status == TaskStatusEnum.PENDING
        assert task.source == SourceTypeEnum.GENERATED

    def test_task_estimated_hours_bounds(self):
        with pytest.raises(ValidationError):
            RoadmapTaskBase(title="T", estimated_hours=0.1, success_criteria="C")
        with pytest.raises(ValidationError):
            RoadmapTaskBase(title="T", estimated_hours=10.0, success_criteria="C")

    def test_task_update_all_optional(self):
        update = RoadmapTaskUpdate()
        assert update.title is None
        assert update.estimated_hours is None
        assert update.status is None

    def test_task_update_partial(self):
        update = RoadmapTaskUpdate(title="New Title", estimated_hours=5.0)
        assert update.title == "New Title"
        assert update.estimated_hours == 5.0
        assert update.status is None

    def test_task_update_invalid_hours_rejected(self):
        with pytest.raises(ValidationError):
            RoadmapTaskUpdate(estimated_hours=10.0)
        with pytest.raises(ValidationError):
            RoadmapTaskUpdate(estimated_hours=0.1)

    def test_task_response_has_extra_fields(self):
        task = RoadmapTaskResponse(
            id="task-1",
            roadmap_id="roadmap-1",
            phase_id="phase-1",
            position=1,
            title="Test",
            estimated_hours=4.0,
            success_criteria="Done",
        )
        assert task.id == "task-1"
        assert task.completed_at is None


class TestRoadmapPhaseSchemas:
    """Test phase-related schemas."""

    def test_phase_base_valid(self):
        phase = RoadmapPhaseBase(name="Phase 1", description="Foundation")
        assert phase.name == "Phase 1"
        assert phase.description == "Foundation"

    def test_phase_response_has_tasks(self):
        phase = RoadmapPhaseResponse(
            id="phase-1",
            roadmap_id="roadmap-1",
            position=1,
            name="Phase 1",
            tasks=[],
        )
        assert phase.tasks == []


class TestRoadmapSchemas:
    """Test roadmap schemas."""

    def test_roadmap_base_valid(self):
        roadmap = RoadmapBase(
            title="My Roadmap",
            target_role="Backend Developer",
            total_estimated_hours=40.0,
        )
        assert roadmap.title == "My Roadmap"
        assert roadmap.source == SourceTypeEnum.GENERATED

    def test_roadmap_response_has_metadata(self):
        roadmap = RoadmapResponse(
            id="rm-1",
            student_id="std-1",
            version=1,
            is_active=True,
            title="My Roadmap",
            target_role="Backend Developer",
            total_estimated_hours=40.0,
            created_at=datetime.now(),
            phases=[],
        )
        assert roadmap.version == 1
        assert roadmap.is_active is True

    def test_generation_request_default(self):
        req = RoadmapGenerationRequest()
        assert req.force_regenerate is False

    def test_generation_request_can_force(self):
        req = RoadmapGenerationRequest(force_regenerate=True)
        assert req.force_regenerate is True


class TestAdaptationSchemas:
    """Test adaptation schemas."""

    def test_adaptation_response(self):
        resp = RoadmapAdaptationResponse(
            id="adapt-1",
            roadmap_id="rm-1",
            source_type="interview",
            source_id="int-1",
            proposed_tasks=[{"title": "New Task", "estimated_hours": 4}],
            status=AdaptationStatusEnum.PROPOSED,
            created_at=datetime.now(),
        )
        assert resp.source_type == "interview"
        assert resp.status == AdaptationStatusEnum.PROPOSED

    def test_adaptation_action_approve(self):
        action = RoadmapAdaptationAction(action="approve")
        assert action.action == "approve"

    def test_adaptation_action_reject(self):
        action = RoadmapAdaptationAction(action="reject")
        assert action.action == "reject"

    def test_adaptation_action_invalid_rejected(self):
        with pytest.raises(ValidationError):
            RoadmapAdaptationAction(action="invalid")


class TestTaskCompletionRequest:
    """Test task completion request."""

    def test_valid_completion(self):
        req = TaskCompletionRequest(status=TaskStatusEnum.COMPLETED)
        assert req.status == TaskStatusEnum.COMPLETED

    def test_pending_completion(self):
        req = TaskCompletionRequest(status=TaskStatusEnum.PENDING)
        assert req.status == TaskStatusEnum.PENDING