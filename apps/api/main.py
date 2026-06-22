"""
(a) What this file is: FastAPI app factory. Registers routers, CORS, auth middleware, lifespan.
(b) What it does: Sets up loggers, lifespan startup/shutdown messages, and defines the /health route.
(c) How it fits into the MENO system: Serves as the core HTTP entry point for serving requests on all database and session layers.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings

# Setup logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("meno.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: log "MENO Intelligence Platform v0.2.0 starting"
    logger.info("MENO Intelligence Platform v0.2.0 starting")
    if settings.app_env == "development":
        logger.warning("AUTH DISABLED — development mode")
    yield
    # On shutdown
    logger.info("MENO Intelligence Platform v0.2.0 shutting down")


app = FastAPI(
    title="MENO API",
    version="0.2.0",
    lifespan=lifespan
)

# CORS middleware registration
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from apps.api.middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

from apps.api.routes import knowledge
from apps.api.routes import relationships
from apps.api.routes import context
from apps.api.routes import sessions
from apps.api.routes import worker
from apps.api.routes import profiles

app.include_router(knowledge.router)
app.include_router(relationships.router)
app.include_router(context.router)
app.include_router(sessions.router)
app.include_router(worker.router)
app.include_router(profiles.router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.2.0",
        "env": settings.app_env,
        "tiers": {
            "working_memory": "redis",
            "knowledge": "postgres+pgvector",
            "relationships": "postgres"
        }
    }
