# Main API router
from fastapi import APIRouter

from app.api.routes import countries, health, players, teams

router = APIRouter()
router.include_router(health.router)
router.include_router(players.router)
router.include_router(countries.router)
router.include_router(teams.router)
