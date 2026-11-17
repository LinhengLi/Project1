"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.db import RedisStateStore, init_database
from app.services.scenario_manager import sim_manager

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description="低轨卫星电磁干扰态势感知与预测系统 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

static_dir = settings.static_dir
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": settings.api_version,
        "docs": "/docs",
        "dashboard": "/static/index.html",
    }


@app.get("/health")
def health():
    redis_client = RedisStateStore(settings.redis_url).client
    return {
        "status": "healthy",
        "scenario_loaded": sim_manager.scenario is not None,
        "current_mode": sim_manager.current_mode.value,
        "scenario_path": sim_manager.current_scenario_path,
        "scenario_id": sim_manager.scenario.scenario_id if sim_manager.scenario else "",
        "database_url": settings.database_url,
        "data_dir": str(settings.data_dir),
        "static_dir": str(settings.static_dir),
        "redis_connected": redis_client is not None,
    }


@app.on_event("startup")
def startup():
    if settings.enable_db_bootstrap:
        init_database()
    scenario_path = settings.data_dir / "scenarios" / settings.startup_scenario
    if scenario_path.exists():
        try:
            sim_manager.load_scenario(scenario_path)
            for _ in range(5):
                sim_manager.step()
        except Exception:
            pass


