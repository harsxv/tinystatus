from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import markdown
from datetime import datetime
import asyncio
import logging
from pathlib import Path

from .config import get_settings, STATIC_DIR, TEMPLATE_DIR
from .services.monitor import StatusMonitor
from .database import get_db

# Setup FastAPI app
app = FastAPI(title="StatusWatch")
settings = get_settings()

# Mount static files
app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# Initialize monitor
monitor = StatusMonitor()

# Background task for continuous monitoring
async def continuous_monitoring():
    while True:
        try:
            await monitor.check_all_services()
            await asyncio.sleep(settings.CHECK_INTERVAL)
        except Exception as e:
            logging.error(f"Monitoring error: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    if settings.MONITOR_CONTINUOUSLY:
        asyncio.create_task(continuous_monitoring())

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    results = await monitor.check_all_services()
    
    with open(settings.INCIDENTS_FILE, 'r') as f:
        incidents = markdown.markdown(f.read())
    
    return templates.TemplateResponse(
        "index.html.theme",
        {
            "request": request,
            "groups": results,
            "incidents": incidents,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

@app.get("/history", response_class=HTMLResponse)
async def history(
    request: Request,
    hours: int = Query(24, description="Hours of history to show")
):
    grouped_history, uptimes = monitor.get_combined_history(hours=hours)
    
    return templates.TemplateResponse(
        "history.html.theme",
        {
            "request": request,
            "grouped_history": grouped_history,
            "uptimes": uptimes,
            "timeframe": f"Last {hours} hours",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

# API endpoints
@app.get("/api/status")
async def get_status():
    """Get current status of all services"""
    return await monitor.check_all_services()

@app.get("/api/history")
async def get_history(hours: int = Query(24, description="Hours of history to return")):
    """Get historical data for all services"""
    grouped_history, uptimes = monitor.get_combined_history(hours=hours)
    return {
        "history": grouped_history,
        "uptimes": uptimes,
        "timeframe": f"Last {hours} hours"
    }

@app.get("/api/history/{group_name}")
async def get_group_history(
    group_name: str,
    hours: int = Query(24, description="Hours of history to return")
):
    """Get historical data for a specific group"""
    grouped_history, uptimes = monitor.get_combined_history(hours=hours)
    if group_name not in grouped_history:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return {
        "history": grouped_history[group_name],
        "uptime": uptimes.get(group_name, 100.0),
        "timeframe": f"Last {hours} hours"
    }

@app.post("/api/reset-db")
async def reset_database():
    try:
        monitor.reset_database()
        return JSONResponse(content={"message": "Database reset successful"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring the service status.
    Returns:
        JSONResponse: Health status with timestamp and version
    """
    try:
        # Basic application health check
        return JSONResponse(
            content={
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.1.0",  # Match with CHANGELOG version
                "database": "connected" if monitor.db else "disconnected",
                "monitor_status": "running" if monitor.settings.MONITOR_CONTINUOUSLY else "stopped",
                "last_check": monitor._cache_time.isoformat() if monitor._cache_time else None,
                "uptime": (datetime.utcnow() - monitor._start_time).total_seconds() if hasattr(monitor, '_start_time') else 0
            },
            status_code=200
        )
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        ) 