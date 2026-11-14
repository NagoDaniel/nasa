from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

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

for r in (health.router, geo.router, nasa.router, area.router, crops.router):
    app.include_router(r, prefix="/api")
