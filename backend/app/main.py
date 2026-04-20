"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.agents.factory import build_agent
from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.engine.orchestrator import Orchestrator

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent = build_agent(settings)
    orchestrator = Orchestrator(settings=settings, agent=agent)
    app.state.orchestrator = orchestrator

    scheduler = AsyncIOScheduler()
    scheduler.add_job(orchestrator.run_once, "interval", minutes=1, id="engine-tick", max_instances=1)
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Quant Sentinel v%s started in %s mode", __version__, settings.trading_mode)
    try:
        # Kick one cycle right away so the dashboard has data.
        await orchestrator.run_once()
        yield
    finally:
        scheduler.shutdown(wait=False)
        await orchestrator.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Quant Sentinel",
        version=__version__,
        description="Multi-asset automated trading platform (paper-first).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/")
    async def root() -> dict:
        return {
            "name": "Quant Sentinel",
            "version": __version__,
            "mode": settings.trading_mode,
            "docs": "/docs",
        }

    return app


app = create_app()
