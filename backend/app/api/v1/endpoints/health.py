from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import settings
from app.shared.llm import LLMProvider, LLMTask, TASK_MODEL_MAP

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check validating backend and MySQL connectivity."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "module": "Module 1 - Shared Student Profile",
    }


@router.get("/v1/models")
def list_models():
    """OpenAI-compatible models endpoint for model discovery."""
    models = []
    seen = set()
    
    for task, config in TASK_MODEL_MAP.items():
        provider = config.get("provider", LLMProvider.NVIDIA)
        model = config.get("model", settings.NVIDIA_DEFAULT_MODEL)
        key = f"{provider.value}/{model}"
        
        if key not in seen:
            seen.add(key)
            models.append({
                "id": key,
                "object": "model",
                "owned_by": provider.value,
                "permission": [],
                "root": key,
                "parent": None,
            })
    
    # Add default model if not already included
    default_key = f"{settings.LLM_PROVIDER}/{settings.NVIDIA_DEFAULT_MODEL if settings.LLM_PROVIDER == 'nvidia' else settings.GROQ_MODEL}"
    if default_key not in seen:
        models.append({
            "id": default_key,
            "object": "model",
            "owned_by": settings.LLM_PROVIDER,
            "permission": [],
            "root": default_key,
            "parent": None,
        })
    
    return {
        "object": "list",
        "data": models,
    }
