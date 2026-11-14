from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from .assistant import router as assistant
from .config import settings
from .db import init_db
from .routers import area, crops, geo, health, nasa


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

for r in (health.router, geo.router, nasa.router, area.router, crops.router, assistant.router):
    app.include_router(r, prefix="/api")


@app.middleware("http")
async def assistant_body_limit(request: Request, call_next):
    """Reject oversized or unsized assistant requests before the body is read."""
    if request.method == "POST" and request.url.path.startswith("/api/assistant") and not assistant.body_limit_ok(request):
        return ORJSONResponse({"detail": "Request too large"}, status_code=413)
    return await call_next(request)
