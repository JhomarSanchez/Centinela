"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import metrics
from app.api.routes import ai, auth, dashboard, incidents, services
from app.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background scheduler with the app; stop it on shutdown.

    Tests disable the scheduler with SCHEDULER_ENABLED=false so they never
    make real network calls.
    """
    settings = get_settings()
    if settings.api_key == "change-me":
        # Not fatal (this is a local single-user tool), but worth a loud note:
        # anyone who reads the docs knows the default key.
        logger.warning(
            "API_KEY is still the default 'change-me'; set a real value in .env "
            "before exposing this API beyond localhost"
        )
    if settings.app_secret_key == "change-me":
        logger.warning(
            "APP_SECRET_KEY is still the development default; browser sessions work, "
            "but cloud provider credentials cannot be saved until it is changed"
        )

    scheduler = None
    if settings.scheduler_enabled:
        # Both imports happen here so test runs never touch APScheduler or
        # the real database engine at all.
        from app.database import SessionLocal
        from app.scheduler.jobs import create_scheduler

        # Re-seed the last-known-status gauges before the first tick, so a
        # restart does not show "No data" in Grafana until checks resume.
        try:
            with SessionLocal() as db:
                metrics.init_from_db(db)
        except Exception:
            # A missing table (migrations not applied yet) must not prevent
            # the API from starting; metrics simply begin empty.
            logger.warning("could not restore metrics from the database", exc_info=True)

        scheduler = create_scheduler()
        scheduler.start()
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Centinela",
    description="Personal service-monitoring platform with health checks and history.",
    version="0.6.0",
    lifespan=lifespan,
)
# The versioned API is the product contract used by the web app. The original
# paths remain as temporary authenticated aliases for existing CLI scripts.
app.include_router(auth.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(services.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(services.router, deprecated=True)
app.include_router(incidents.router, deprecated=True)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness probe for the API itself (not for monitored services)."""
    return {"status": "ok"}


@app.get("/metrics", tags=["observability"])
def prometheus_metrics() -> Response:
    """Prometheus scrape target exposing the health-check metrics."""
    # generate_latest renders every registered metric in the plain-text
    # exposition format that Prometheus understands.
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
