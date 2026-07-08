from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import async_session
from app.routers import (
    admin,
    admin_auth,
    auth,
    care,
    characters,
    chat,
    data,
    emotion,
    memory,
    push,
    relationship,
    settings as settings_router,
    subscription,
)
from app.services.seed import seed_characters


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed characters if not exist
    async with async_session() as db:
        await seed_characters(db)
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: restrict to actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(characters.router, prefix="/api/v1/characters", tags=["Characters"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(data.router, prefix="/api/v1/data", tags=["Data"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(emotion.router, prefix="/api/v1/emotion", tags=["Emotion"])
app.include_router(care.router, prefix="/api/v1/care", tags=["Care"])
app.include_router(push.router, prefix="/api/v1/push", tags=["Push"])
app.include_router(relationship.router, prefix="/api/v1/relationship", tags=["Relationship"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(subscription.router, prefix="/api/v1/subscription", tags=["Subscription"])
app.include_router(admin_auth.router, prefix="/api/v1/admin/auth", tags=["Admin"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}
