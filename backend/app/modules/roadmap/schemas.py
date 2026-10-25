from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class SourceTypeEnum(str, Enum):
    GENERATED = "generated"
    INTERVIEW = "interview"
    RESUME = "resume"


class AdaptationStatusEnum(str, Enum):
    PROPOSED = "proposed"
    APPLIED = "applied"
    REJECTED = "rejected"


class RoadmapTaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    estimated_hours: float = Field(..., ge=0.5, le=8.0)
    success_criteria: str = Field(..., min_length=1)
    topic_tags: List[str] = Field(default_factory=list)
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    due_date: Optional[date] = None
    source: SourceTypeEnum = SourceTypeEnum.GENERATED


class RoadmapTaskCreate(RoadmapTaskBase):
    pass


class RoadmapTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    estimated_hours: Optional[float] = Field(None, ge=0.5, le=8.0)
    success_criteria: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    status: Optional[TaskStatusEnum] = None
    due_date: Optional[date] = None


class RoadmapTaskResponse(RoadmapTaskBase):
    id: str
    roadmap_id: str
    phase_id: str
    position: int
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RoadmapPhaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class RoadmapPhaseCreate(RoadmapPhaseBase):
    pass


class RoadmapPhaseResponse(RoadmapPhaseBase):
    id: str
    roadmap_id: str
    position: int
    tasks: List[RoadmapTaskResponse] = []

    model_config = {"from_attributes": True}


class RoadmapBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    target_role: str = Field(..., min_length=1, max_length=100)
    total_estimated_hours: float = Field(..., ge=0)
    source: SourceTypeEnum = SourceTypeEnum.GENERATED
    prompt_version: Optional[str] = None
    model: Optional[str] = None


class RoadmapCreate(RoadmapBase):
    pass


class RoadmapResponse(RoadmapBase):
    id: str
    student_id: str
    version: int
    is_active: bool
    created_at: datetime
    phases: List[RoadmapPhaseResponse] = []

    model_config = {"from_attributes": True}


class RoadmapGenerationRequest(BaseModel):
    force_regenerate: bool = False


class RoadmapAdaptationResponse(BaseModel):
    id: str
    roadmap_id: str
    source_type: str
    source_id: str
    proposed_tasks: List[dict]
    status: AdaptationStatusEnum
    created_at: datetime

    model_config = {"from_attributes": True}


class RoadmapAdaptationAction(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")


class TaskCompletionRequest(BaseModel):
    status: TaskStatusEnum


# Alias for backward compatibility with graph imports
RoadmapTask = RoadmapTaskResponse