# Creates the FastAPI app and includes routers
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import router as api_router
from app.config import get_settings
from app.services.players import UnknownReference

settings = get_settings()

app = FastAPI(title="WSL API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(UnknownReference)
def handle_unknown_reference(_: Request, error: UnknownReference) -> JSONResponse:
    """Services raise domain errors; turning them into HTTP belongs here."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": str(error)},
    )


app.include_router(api_router)
