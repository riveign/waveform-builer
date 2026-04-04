"""FastAPI application factory for Kiku."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kiku.api.routes import audio, config, export, hunt, sets, soundcloud, stats, tinder, tracks, waveforms
from kiku.db.models import _init_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_schema()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Kiku API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:4173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(tracks.router)
    app.include_router(audio.router)
    app.include_router(waveforms.router)
    app.include_router(sets.router)
    app.include_router(stats.router)
    app.include_router(tinder.router)
    app.include_router(export.router)
    app.include_router(config.router)
    app.include_router(hunt.router)
    app.include_router(soundcloud.router)

    return app
