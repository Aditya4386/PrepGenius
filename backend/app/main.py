from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import init_db
from app.api.v1.router import api_router
from app.shared.llm import LLMProvider, LLMTask, TASK_MODEL_MAP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MySQL tables on startup
    try:
        logger.info("Initializing database tables...")
        init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization warning: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="PrepGenius - Smart Unified System for Personalized Career Readiness (Module 1: Shared Student Profile)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def root_health():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": "1.0.0",
    }


@app.get("/v1/models", tags=["Health"], include_in_schema=False)
def root_list_models():
    """OpenAI-compatible models endpoint for model discovery (root level)."""
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
