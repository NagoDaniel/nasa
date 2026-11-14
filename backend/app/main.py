from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from .assistant import router as assistant
from .config import settings
from .db import init_db
from .routers import area, crops, fields, geo, geocode, health, nasa, planner


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SPACE2FEED API",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (health.router, geo.router, nasa.router, area.router, crops.router, fields.router, assistant.router, planner.router, geocode.router):
    app.include_router(r, prefix="/api")


BODY_LIMITS = {"/api/assistant": 8 * 1024, "/api/fields": 64 * 1024, "/api/planner": 32 * 1024}


@app.middleware("http")
async def body_limit(request: Request, call_next):
    """Reject oversized or unsized request bodies on write endpoints before they are read."""
    if request.method in ("POST", "PUT", "PATCH"):
        for prefix, limit in BODY_LIMITS.items():
            if request.url.path.startswith(prefix):
                cl = request.headers.get("content-length")
                if cl is None or not cl.isdigit() or int(cl) > limit:
                    return ORJSONResponse({"detail": "Request too large"}, status_code=413)
    return await call_next(request)
