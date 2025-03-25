__all__ = (
    'router',
)

from fastapi import APIRouter
from .v1 import incidents_router

router = APIRouter(prefix="/api/v1")

router.include_router(incidents_router)
