from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.baboon import router as baboon_router
from app.api.friends import router as friends_router
from app.api.health import router as health_router
from app.api.matches import router as matches_router
from app.core.config import get_settings
from app.database.session import init_db


def create_app(*, initialize_database: bool = True) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if initialize_database:
            init_db()
        yield

    app = FastAPI(
        title="ARAM Baboon Tracker API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(friends_router, prefix="/api")
    app.include_router(matches_router, prefix="/api")
    app.include_router(baboon_router, prefix="/api")
    return app


app = create_app()
