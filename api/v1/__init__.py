from fastapi import APIRouter
from .endpoints import router as incidents_router


__all__ = (
    'incidents_router',
)
