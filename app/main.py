import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from enum import Enum

import markdown
from sqlalchemy import and_, or_, func
from fastapi import FastAPI, HTTPException, Query, Request, Body, Depends, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .auth import get_current_user, require_auth, require_token, security
from .config import STATIC_DIR, TEMPLATE_DIR, get_settings
from .database import ServiceHealthCheck, get_db
from .services.monitor import StatusMonitor
from .schemas import StatusType, HealthCheckCreate, HealthCheckResponse, RecoveryCreate, NotificationCreate, RecoveryDataResponse
from .services.health_checks import HealthCheckService

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


@app.post("/api/health-checks", response_model=HealthCheckResponse)
@require_token
async def create_health_check(
    request: Request,
    data: Union[HealthCheckCreate, RecoveryCreate, NotificationCreate] = Body(...),
    db: Session = Depends(get_db)
):
    """Submit a service health check with support for all data types"""
    try:
        service = HealthCheckService(db)
        health_check = service.create_health_check(data)
        return HealthCheckResponse.model_validate(health_check)
    except Exception as e:
        logging.error(f"Error recording health check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health-checks/latest", response_model=List[HealthCheckResponse])
@require_token
async def get_latest_health_checks(
    request: Request,
    service_group: Optional[str] = None,
    service_name: Optional[str] = None,
    public_ip: Optional[str] = None,
    status: Optional[StatusType] = None,
    db: Session = Depends(get_db),
):
    """Get latest health checks with filtering"""
    try:
        service = HealthCheckService(db)
        results = service.get_latest_checks(
            service_group=service_group,
            service_name=service_name,
            public_ip=public_ip,
            status=status,
        )
        return [HealthCheckResponse.model_validate(check) for check in results]
    except Exception as e:
        logging.error(f"Error getting latest health checks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health-checks/history")
@require_token
async def get_health_check_history(
    request: Request,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    service_group: Optional[str] = None,
    service_name: Optional[str] = None,
    status: Optional[StatusType] = None,
    include_recovery: bool = False,
    include_notifications: bool = False,
    page: int = 1,
    page_size: int = 100,
):
    """Get historical health check data with comprehensive filtering"""
    try:
        db = next(get_db())

        query = db.query(ServiceHealthCheck)

        # Time range filter
        query = query.filter(ServiceHealthCheck.timestamp >= start_time)
        if end_time:
            query = query.filter(ServiceHealthCheck.timestamp <= end_time)

        # Apply other filters
        if service_group:
            query = query.filter(ServiceHealthCheck.service_group == service_group)
        if service_name:
            query = query.filter(ServiceHealthCheck.service_name == service_name)
        if status:
            query = query.filter(ServiceHealthCheck.status == status)

        # Status type filters
        if not include_recovery:
            query = query.filter(~ServiceHealthCheck.status.like("recovery_%"))
        if not include_notifications:
            query = query.filter(~ServiceHealthCheck.status.like("notification_%"))

        # Add pagination
        total = query.count()
        query = query.order_by(ServiceHealthCheck.timestamp.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        results = query.all()

        return {
            "status": "success",
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            },
            "data": [
                {
                    "timestamp": check.timestamp.isoformat(),
                    "hostname": check.hostname,
                    "local_ip": check.local_ip,
                    "public_ip": check.public_ip,
                    "service_name": check.service_name,
                    "service_group": check.service_group,
                    "status": check.status,
                    "response_time": check.response_time,
                    "url": check.url,
                    "extra_data": json.loads(check.extra_data)
                    if check.extra_data
                    else None,
                }
                for check in results
            ],
        }
    except Exception as e:
        logging.error(f"Error getting health check history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recovery")
async def get_recovery_data(
    request: Request,
    service_name: Optional[str] = None,
    service_group: Optional[str] = None,
    public_ip: Optional[str] = None,
    status: Optional[StatusType] = None,
    db: Session = Depends(get_db),
):
    """Get recovery data for services with query parameters"""
    try:
        service = HealthCheckService(db)
        results = service.get_recovery_data(
            service_name=service_name,
            service_group=service_group,
            public_ip=public_ip,
            status=status
        )
        data = RecoveryDataResponse.model_validate(results) if results else {}
        return data
    except Exception as e:
        logging.error(f"Error getting recovery data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class RecoveryStateUpdate(BaseModel):
    service_name: str
    service_group: str
    status: str
    stage: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    local_ip: Optional[str] = None
    public_ip: Optional[str] = None
    hostname: Optional[str] = None
    stabilization_end_time: Optional[datetime] = None


@app.post("/api/recovery", response_model=RecoveryDataResponse)
@require_token
async def update_recovery_state(
    request: Request,
    data: RecoveryStateUpdate,
    db: Session = Depends(get_db),
):
    """Update service recovery state"""
    try:
        service = HealthCheckService(db)
        recovery_data = RecoveryCreate(
            service_name=data.service_name,
            service_group=data.service_group,
            status=data.status,
            stage=data.stage,
            error=data.error,
            start_time=data.start_time or datetime.utcnow(),
            local_ip=data.local_ip,
            public_ip=data.public_ip,
            hostname=data.hostname,
            stabilization_end_time=data.stabilization_end_time,
        )
        result = service.create_recovery_state(recovery_data)
        return RecoveryDataResponse.model_validate(result)
    except Exception as e:
        logging.error(f"Error updating recovery state: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/public/status")
async def get_public_status(db: Session = Depends(get_db)) -> Dict[str, Dict[str, Union[bool, List[str], str]]]:
    """Public endpoint showing minimal system status from database - no auth required"""
    try:
        settings = get_settings()
        cutoff_time = datetime.utcnow() - timedelta(minutes=settings.PUBLIC_STATUS_MAX_AGE_MINUTES)
        
        # Get latest status for each service
        latest_checks = (
            db.query(
                ServiceHealthCheck.service_group,
                ServiceHealthCheck.service_name,
                ServiceHealthCheck.status,
                func.max(ServiceHealthCheck.timestamp).label('latest_timestamp')
            )
            .group_by(
                ServiceHealthCheck.service_group,
                ServiceHealthCheck.service_name
            )
            .having(func.max(ServiceHealthCheck.timestamp) >= cutoff_time)
            .all()
        )
        
        if not latest_checks:
            return JSONResponse(
                status_code=400,
                content={
                    "status": {
                        "healthy": False,
                        "down_services": ["no_recent_data"],
                        "last_check": None
                    }
                }
            )
            
        response = {
            "status": {
                "healthy": True,
                "down_services": [],
                "last_check": None
            }
        }
        
        latest_timestamp = None
        
        for check in latest_checks:
            # Skip system group
            if check.service_group.lower() == "system":
                continue
                
            # Update latest timestamp
            if latest_timestamp is None or check.latest_timestamp > latest_timestamp:
                latest_timestamp = check.latest_timestamp
                
            # Check if service is down
            if check.status.lower() != "up":
                response["status"]["healthy"] = False
                response["status"]["down_services"].append(
                    f"{check.service_group}/{check.service_name}"
                )
        
        # Add last check timestamp
        response["status"]["last_check"] = latest_timestamp.isoformat() if latest_timestamp else None
        
        # Return appropriate status code based on health
        return JSONResponse(
            status_code=200 if response["status"]["healthy"] else 400,
            content=response
        )
        
    except Exception as e:
        logging.error(f"Error getting public status from database: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "status": {
                    "healthy": False,
                    "down_services": ["system_error"],
                    "last_check": None
                }
            }
        )
