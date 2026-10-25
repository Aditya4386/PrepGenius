from fastapi import APIRouter
from app.api.v1.endpoints import profile, health, auth, resume, roadmap

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(resume.router)
api_router.include_router(roadmap.router)
