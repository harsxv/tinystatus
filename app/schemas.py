from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import json

from app.database import ServiceHealthCheck


class StatusType(str, Enum):
    UP = "up"
    DOWN = "down"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_IN_PROGRESS = "recovery_in_progress"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_FAILED = "notification_failed"


class BaseHealthCheck(BaseModel):
    """Base model for all health check types"""
    service_group: str
    service_name: str
    status: str
    local_ip: Optional[str] = None
    hostname: Optional[str] = None
    public_ip: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        'from_attributes': True
    }


class HealthCheckCreate(BaseHealthCheck):
    """Model for creating health checks"""
    response_time: Optional[float] = None
    url: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class RecoveryCreate(BaseHealthCheck):
    """Model for creating recovery states"""
    stage: Optional[str] = None
    error: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    stabilization_end_time: Optional[datetime] = None


class NotificationCreate(BaseHealthCheck):
    """Model for creating notifications"""
    notification_type: str
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Response model for all health check types"""
    timestamp: datetime
    hostname: Optional[str] = None
    local_ip: Optional[str] = None
    public_ip: Optional[str] = None
    service_name: str
    service_group: str
    status: str
    response_time: Optional[float] = None
    url: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None

    model_config = {
        'from_attributes': True
    }

    @field_validator('extra_data', mode='before')
    @classmethod
    def parse_extra_data(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value


class RecoveryDataResponse(BaseModel):
    """Response model for recovery data"""
    service_group: str
    service_name: str
    status: str
    local_ip: Optional[str] = None
    public_ip: Optional[str] = None
    hostname: Optional[str] = None
    stage: Optional[str] = None
    error: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    stabilization_end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        'from_attributes': True
    }

    @classmethod
    def model_validate(cls, obj):
        """Custom validation for ServiceHealthCheck objects"""
        if isinstance(obj, ServiceHealthCheck):
            # Parse the extra_data JSON
            extra_data = json.loads(obj.extra_data) if obj.extra_data else {}
            
            # Create a dictionary with all the fields
            data = {
                "service_group": obj.service_group,
                "service_name": obj.service_name,
                "status": obj.status,
                "local_ip": obj.local_ip,
                "public_ip": obj.public_ip,
                "hostname": obj.hostname,
                "stage": extra_data.get("stage"),
                "error": extra_data.get("error"),
                "start_time": datetime.fromisoformat(extra_data["start_time"]) if extra_data.get("start_time") else obj.timestamp,
                "end_time": datetime.fromisoformat(extra_data["end_time"]) if extra_data.get("end_time") else None,
                "stabilization_end_time": datetime.fromisoformat(extra_data["stabilization_end_time"]) if extra_data.get("stabilization_end_time") else None,
                "created_at": obj.timestamp,
                "updated_at": obj.timestamp
            }
            return super().model_validate(data)
        return super().model_validate(obj)
