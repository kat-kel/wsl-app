# Main API router
from fastapi import APIRouter

from app.api.routes import health, players

router = APIRouter()
router.include_router(health.router)
router.include_router(players.router)
