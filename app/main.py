import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

import markdown
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import get_current_user, require_auth, require_token, security
from .config import STATIC_DIR, TEMPLATE_DIR, get_settings
from .services.monitor import StatusMonitor

# Setup FastAPI app
app = FastAPI(title="StatusWatch")
settings = get_settings()
app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
monitor = StatusMonitor()


def sort_groups(data: dict) -> dict:
    """Sort groups with IBL groups first, then others"""
    ibl_groups = {k: v for k, v in data.items() if k.lower().startswith("ibl-")}
    other_groups = {k: v for k, v in data.items() if not k.lower().startswith("ibl-")}

    sorted_data = {}
    sorted_data.update(dict(sorted(ibl_groups.items())))
    sorted_data.update(dict(sorted(other_groups.items())))
    return sorted_data


def format_group_display(group_name: str) -> tuple:
    """Split group name into display name and IP if available"""
    if monitor.SERVER_SEPARATOR in group_name:
        name, ip = group_name.split(monitor.SERVER_SEPARATOR, 1)
        return name.strip(), ip.strip()
    return group_name.strip(), None


def get_url_from_status(status_data: dict) -> str:
    """Extract URL from status extra data"""
    try:
        if extra_data := status_data.get("extra_data"):
            data = json.loads(extra_data)
            if data.get("type") == "http":
                return data.get("host")
    except:
        pass
    return None


async def get_session_token(request: Request) -> Optional[str]:
    """Get token from session or basic auth"""
    try:
        credentials = await security(request)
        user = get_current_user(credentials)
        if user and user.api_token:
            return user.api_token
    except:
        pass
    return None


async def continuous_monitoring():
    """Background task for continuous monitoring"""
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


@app.get("/", response_class=HTMLResponse)
@require_auth
async def index(request: Request):
    """Home page showing current status of all services"""
    try:
        grouped_history, uptimes = monitor.get_combined_history(hours=24)
        with open(monitor.settings.INCIDENTS_FILE, "r") as f:
            incidents_html = markdown.markdown(f.read())

        sorted_groups = sort_groups(grouped_history)
        groups = {}

        for group_name, services in sorted_groups.items():
            display_name, ip = format_group_display(group_name)
            groups[group_name] = {
                "info": {"display": display_name, "ip": ip},
                "services": [],
            }

            for service_name, history_data in services.items():
                latest_status = (
                    history_data[-1] if history_data else {"y": 1, "response_time": 0}
                )
                groups[group_name]["services"].append(
                    {
                        "name": service_name,
                        "status": latest_status["y"] == 1,
                        "url": get_url_from_status(latest_status),
                        "response_time": latest_status.get("response_time", 0),
                    }
                )
        return templates.TemplateResponse(
            "index.html.theme",
            {
                "request": request,
                "groups": groups,
                "uptimes": uptimes,
                "incidents": incidents_html,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "SERVER_SEPARATOR": monitor.SERVER_SEPARATOR,
            },
        )
    except Exception as e:
        logging.error(f"Error rendering index: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history", response_class=HTMLResponse)
@require_auth
async def history(request: Request, hours: int = Query(24)):
    """History page showing service status over time"""
    # Get session token if available
    session_token = await get_session_token(request)
    grouped_history, uptimes = monitor.get_combined_history(hours=hours)
    sorted_history = sort_groups(grouped_history)

    sorted_uptimes = {
        group_name: uptimes.get(group_name, 100.0)
        for group_name in sorted_history.keys()
    }

    return templates.TemplateResponse(
        "history.html.theme",
        {
            "request": request,
            "grouped_history": sorted_history,
            "uptimes": sorted_uptimes,
            "timeframe": f"Last {hours} hours",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "SERVER_SEPARATOR": monitor.SERVER_SEPARATOR,
            "session_token": session_token,
        },
    )


@app.get("/api/status")
@require_token
async def get_status(request: Request):
    """Get current status of all services"""
    current_status = await monitor.check_all_services()
    return sort_groups(current_status)


@app.get("/api/history")
@require_token
async def get_history(request: Request, hours: int = Query(24)):
    """Get historical data for all services"""
    grouped_history, uptimes = monitor.get_combined_history(hours=hours)
    sorted_history = sort_groups(grouped_history)
    sorted_uptimes = {
        group_name: uptimes.get(group_name, 100.0)
        for group_name in sorted_history.keys()
    }

    return {
        "history": sorted_history,
        "uptimes": sorted_uptimes,
        "timeframe": f"Last {hours} hours",
    }


@app.get("/api/history/{group_name}")
@require_token
async def get_group_history(request: Request, group_name: str, hours: int = Query(24)):
    """Get historical data for a specific group"""
    grouped_history, uptimes = monitor.get_combined_history(hours=hours)
    if group_name not in grouped_history:
        raise HTTPException(status_code=404, detail="Group not found")

    return {
        "history": grouped_history[group_name],
        "uptime": uptimes.get(group_name, 100.0),
        "timeframe": f"Last {hours} hours",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return JSONResponse(
            content={
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.1.0",
                "database": "connected" if monitor.db else "disconnected",
                "monitor_status": "running"
                if monitor.settings.MONITOR_CONTINUOUSLY
                else "stopped",
                "last_check": monitor._cache_time.isoformat()
                if monitor._cache_time
                else None,
                "uptime": (datetime.utcnow() - monitor._start_time).total_seconds()
                if hasattr(monitor, "_start_time")
                else 0,
            },
            status_code=200,
        )
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
            status_code=503,
        )
