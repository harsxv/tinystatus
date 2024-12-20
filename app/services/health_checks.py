import json
from datetime import datetime
from typing import List, Dict, Optional, Union
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from app.database import ServiceHealthCheck, ServiceRecovery
from app.schemas import StatusType, HealthCheckCreate, RecoveryCreate, NotificationCreate


class HealthCheckService:
    def __init__(self, db: Session):
        self.db = db

    def create_health_check(
        self, data: Union[HealthCheckCreate, RecoveryCreate, NotificationCreate]
    ) -> ServiceHealthCheck:
        """Create a health check record from any of the supported types"""
        extra_data = {}

        if isinstance(data, HealthCheckCreate):
            extra_data = {**data.metrics, ** data.extra_data}
        elif isinstance(data, RecoveryCreate):
            extra_data = {
                "stage": data.stage,
                "error": data.error,
                "start_time": data.start_time.isoformat(),
                "end_time": data.end_time.isoformat() if data.end_time else None,
                "stabilization_end_time": (
                    data.stabilization_end_time.isoformat()
                    if data.stabilization_end_time
                    else None
                ),
            }
        elif isinstance(data, NotificationCreate):
            extra_data = {
                "notification_type": data.notification_type,
                "error": data.error,
            }

        health_check = ServiceHealthCheck(
            timestamp=data.timestamp or datetime.utcnow(),
            hostname=data.hostname if hasattr(data, "hostname") else None,
            local_ip=data.local_ip,
            public_ip=data.public_ip,
            service_name=data.service_name,
            service_group=data.service_group,
            status=data.status,
            response_time=getattr(data, "response_time", None),
            url=getattr(data, "url", None),
            extra_data=json.dumps(extra_data) if extra_data else None,
        )

        self.db.add(health_check)
        self.db.commit()
        return health_check

    def get_latest_checks(
        self,
        service_group: Optional[str] = None,
        service_name: Optional[str] = None,
        public_ip: Optional[str] = None,
        status: Optional[StatusType] = None,
    ) -> List[ServiceHealthCheck]:
        # Subquery to get latest timestamp for each service
        latest_checks = (
            self.db.query(
                ServiceHealthCheck.service_group,
                ServiceHealthCheck.service_name,
                ServiceHealthCheck.hostname,
                func.max(ServiceHealthCheck.timestamp).label("max_timestamp"),
            )
            .group_by(
                ServiceHealthCheck.service_group,
                ServiceHealthCheck.service_name,
                ServiceHealthCheck.hostname,
            )
            .subquery()
        )

        # Build main query
        query = self.db.query(ServiceHealthCheck).join(
            latest_checks,
            and_(
                ServiceHealthCheck.service_group == latest_checks.c.service_group,
                ServiceHealthCheck.service_name == latest_checks.c.service_name,
                ServiceHealthCheck.hostname == latest_checks.c.hostname,
                ServiceHealthCheck.timestamp == latest_checks.c.max_timestamp,
            ),
        )

        # Apply filters
        if service_group:
            query = query.filter(ServiceHealthCheck.service_group == service_group)
        if service_name:
            query = query.filter(ServiceHealthCheck.service_name == service_name)
        if public_ip:
            query = query.filter(ServiceHealthCheck.public_ip == public_ip)
        if status:
            query = query.filter(ServiceHealthCheck.status == status)

        return query.all()

    def get_recovery_data(
        self,
        service_name: Optional[str] = None,
        service_group: Optional[str] = None,
        public_ip: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[ServiceRecovery]:
        """Get recovery data with filters"""
        query = self.db.query(ServiceRecovery)

        # Apply filters
        if service_name:
            query = query.filter(ServiceRecovery.service_name == service_name)
        if service_group:
            query = query.filter(ServiceRecovery.service_group == service_group)
        if public_ip:
            query = query.filter(ServiceRecovery.public_ip == public_ip)
        if status:
            query = query.filter(ServiceRecovery.status == status)

        # Order by created_at descending to get latest first
        query = query.order_by(ServiceRecovery.created_at.desc())
        return query.first()

    def create_recovery_state(self, data: RecoveryCreate) -> ServiceRecovery:
        """Create or update recovery state for a service"""
        # First check if there's an existing recovery state
        existing = (
            self.db.query(ServiceRecovery)
            .filter(
                ServiceRecovery.service_name == data.service_name,
                ServiceRecovery.service_group == data.service_group,
                ServiceRecovery.end_time.is_(None)  # Only get active recoveries
            )
            .order_by(ServiceRecovery.created_at.desc())
            .first()
        )

        # If there's an existing recovery and it's not completed/failed,
        # update its end_time
        if existing and existing.status not in ["recovery_completed", "recovery_failed"]:
            existing.end_time = datetime.utcnow()
            self.db.add(existing)

        # Create new recovery state
        recovery = ServiceRecovery(
            service_name=data.service_name,
            service_group=data.service_group,
            status=data.status,
            stage=data.stage,
            error=data.error,
            hostname=data.hostname,
            local_ip=data.local_ip,
            public_ip=data.public_ip,
            start_time=data.start_time or datetime.utcnow(),
            end_time=data.end_time,
            stabilization_end_time=data.stabilization_end_time,
        )

        self.db.add(recovery)
        self.db.commit()
        return recovery
