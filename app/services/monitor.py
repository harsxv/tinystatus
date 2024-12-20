import yaml
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
import json
from sqlalchemy import func
from ..config import get_settings
from ..database import ServiceHealthCheck, get_db
from . import checks

SERVER_SEPARATOR = "@"


class StatusMonitor:
    SERVER_SEPARATOR = SERVER_SEPARATOR

    def __init__(self):
        self.settings = get_settings()
        self.db = next(get_db())
        self._cache = {}
        self._cache_time = None
        self._cache_duration = timedelta(seconds=30)
        self._start_time = datetime.utcnow()

    def load_checks(self) -> List[Dict]:
        with open(self.settings.CHECKS_FILE, "r") as f:
            return yaml.safe_load(f) or {}

    async def check_all_services(self) -> Dict[str, List[Dict]]:
        # Check cache first
        now = datetime.now()
        if (
            self._cache
            and self._cache_time
            and (now - self._cache_time) < self._cache_duration
        ):
            return self._cache

        # Get configured checks
        groups = self.load_checks()
        results = {}

        # Run configured checks
        for group in groups:
            results[group["title"]] = await self.run_checks(group["checks"])

        self.update_history(results)

        # Update cache
        self._cache = results
        self._cache_time = now

        return results

    async def run_checks(self, checks_list: List[Dict]) -> List[Dict]:
        tasks = []
        for check in checks_list:
            if check["type"] == "http":
                task = checks.check_http(
                    check["host"], check["expected_code"], check.get("ssc", False)
                )
            elif check["type"] == "ping":
                task = checks.check_ping(check["host"])
            elif check["type"] == "port":
                task = checks.check_port(check["host"], check["port"])
            else:
                continue

            tasks.append((check, asyncio.create_task(task)))

        results = []
        for check, task in tasks:
            try:
                start_time = datetime.now()
                status = await asyncio.wait_for(task, timeout=10.0)
                response_time = (datetime.now() - start_time).total_seconds()

                results.append(
                    {
                        "name": check["name"],
                        "url": check.get("url"),
                        "status": status,
                        "response_time": response_time,
                        "extra_data": json.dumps(
                            {
                                "type": check["type"],
                                "host": check["host"],
                                "port": check.get("port"),
                                "expected_code": check.get("expected_code"),
                            }
                        ),
                    }
                )
            except Exception as e:
                logging.error(f"Error checking {check['name']}: {e}")
                results.append(
                    {
                        "name": check["name"],
                        "url": check.get("url"),
                        "status": False,
                        "response_time": 0,
                        "extra_data": json.dumps({"error": str(e)}),
                    }
                )

        return results

    def update_history(self, results: Dict):
        current_time = datetime.utcnow()

        # Batch insert all records
        records = []
        for group_name, services in results.items():
            for service in services:
                record = ServiceHealthCheck(
                    hostname="configured-check",
                    local_ip="0.0.0.0",
                    public_ip="0.0.0.0",
                    service_group=group_name,
                    service_name=service["name"],
                    status="up" if service["status"] else "down",
                    response_time=service.get("response_time", 0),
                    url=service.get("url"),
                    extra_data=service.get("extra_data"),
                    timestamp=current_time,
                )
                records.append(record)

        # Bulk insert
        self.db.bulk_save_objects(records)

        # Cleanup old records in batch
        cutoff = current_time - timedelta(days=30)
        self.db.query(ServiceHealthCheck).filter(
            ServiceHealthCheck.timestamp < cutoff
        ).delete()

        self.db.commit()

    def get_combined_history(self, hours: int = 24) -> Tuple[Dict, Dict]:
        """Get combined history from all services"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        results = (
            self.db.query(ServiceHealthCheck)
            .filter(ServiceHealthCheck.timestamp >= cutoff)
            .order_by(ServiceHealthCheck.timestamp.desc())
            .all()
        )

        grouped_history = {}
        uptimes = {}

        for result in results:
            # Format group name to include IP if available
            group_name = result.service_group
            if group_name in ["system"]:
                continue
            if result.local_ip and result.local_ip != "0.0.0.0":
                group_name = (
                    f"{result.service_group}{SERVER_SEPARATOR}{result.local_ip}"
                )
            elif result.public_ip and result.public_ip != "0.0.0.0":
                group_name = (
                    f"{result.service_group}{SERVER_SEPARATOR}{result.public_ip}"
                )

            if group_name not in grouped_history:
                grouped_history[group_name] = {}
                uptimes[group_name] = []

            if result.service_name not in grouped_history[group_name]:
                grouped_history[group_name][result.service_name] = []

            entry = {
                "x": result.timestamp.isoformat(),
                "y": 1 if result.status.lower() == "up" else 0,
                "response_time": result.response_time,
                "extra_data": result.extra_data,
            }

            grouped_history[group_name][result.service_name].append(entry)
            uptimes[group_name].append(result.status.lower() == "up")

        # Calculate uptimes
        for group_name in uptimes:
            if uptimes[group_name]:
                up_count = sum(1 for status in uptimes[group_name] if status)
                uptimes[group_name] = round(
                    (up_count / len(uptimes[group_name])) * 100, 2
                )
            else:
                uptimes[group_name] = 100.0

        return grouped_history, uptimes

    def reset_database(self):
        """Reset the database by removing all service checks"""
        self.db.query(ServiceHealthCheck).delete()
        self.db.commit()
