from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from app.api.routes_followups import router as followup_router
from app.api.routes_gmail import router as gmail_router
from app.api.routes_health import router as health_router
from app.api.routes_intake import router as intake_router
from app.api.routes_review import router as review_router
from app.config import settings
from app.db import Base, engine
app = FastAPI(title=settings.app_name)

app.include_router(health_router)
app.include_router(intake_router)
app.include_router(review_router)
app.include_router(followup_router)
app.include_router(gmail_router)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parent / "static" / "dashboard.html")
