import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import traceback
import sys

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address

        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("realum")
    logger.setLevel(getattr(logging, log_level.upper()))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_dir / log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    error_handler = logging.FileHandler(log_dir / "errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    logger.addHandler(error_handler)

    security_handler = logging.FileHandler(log_dir / "security.log")
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(JSONFormatter())
    logger.addHandler(security_handler)

    return logger

class LoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        kwargs["extra"].update(self.extra)
        return msg, kwargs

def get_logger(name: str, **extra) -> LoggerAdapter:
    logger = logging.getLogger(f"realum.{name}")
    return LoggerAdapter(logger, extra)

class AuditLogger:
    def __init__(self, supabase_client=None):
        self.logger = get_logger("audit")
        self.supabase = supabase_client

    async def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent
        }

        self.logger.info(
            f"Audit: {event_type} - {action}",
            extra=audit_entry
        )

        if self.supabase:
            try:
                self.supabase.table("audit_logs").insert(audit_entry).execute()
            except Exception as e:
                self.logger.error(f"Failed to write audit log to database: {str(e)}")

    async def log_login(self, user_id: str, success: bool, ip_address: str, user_agent: str):
        await self.log_event(
            event_type="authentication",
            user_id=user_id,
            action="login_success" if success else "login_failed",
            ip_address=ip_address,
            user_agent=user_agent
        )

    async def log_data_access(self, user_id: str, resource_type: str, resource_id: str, ip_address: str):
        await self.log_event(
            event_type="data_access",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action="read",
            ip_address=ip_address
        )

    async def log_data_modification(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        changes: Dict[str, Any],
        ip_address: str
    ):
        await self.log_event(
            event_type="data_modification",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details={"changes": changes},
            ip_address=ip_address
        )

    async def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        await self.log_event(
            event_type="security",
            user_id=user_id,
            action=event_type,
            details={"severity": severity, **details},
            ip_address=ip_address
        )

class PerformanceLogger:
    def __init__(self):
        self.logger = get_logger("performance")

    async def log_request(
        self,
        method: str,
        path: str,
        duration_ms: float,
        status_code: int,
        user_id: Optional[str] = None
    ):
        self.logger.info(
            f"Request: {method} {path} - {duration_ms}ms - {status_code}",
            extra={
                "method": method,
                "path": path,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "user_id": user_id
            }
        )

    async def log_db_query(
        self,
        query_type: str,
        table: str,
        duration_ms: float,
        rows_affected: Optional[int] = None
    ):
        self.logger.debug(
            f"DB Query: {query_type} on {table} - {duration_ms}ms",
            extra={
                "query_type": query_type,
                "table": table,
                "duration_ms": duration_ms,
                "rows_affected": rows_affected
            }
        )

class ErrorTracker:
    def __init__(self):
        self.logger = get_logger("errors")
        self.error_counts = {}

    async def track_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        error_key = f"{error_type}:{error_message}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        self.logger.error(
            f"Error: {error_type} - {error_message}",
            extra={
                "error_type": error_type,
                "error_message": error_message,
                "stack_trace": stack_trace,
                "context": context or {},
                "user_id": user_id,
                "request_id": request_id,
                "occurrence_count": self.error_counts[error_key]
            }
        )

    def get_error_stats(self) -> Dict[str, int]:
        return self.error_counts.copy()

    def reset_stats(self):
        self.error_counts.clear()

logger = setup_logging()
audit_logger = AuditLogger()
performance_logger = PerformanceLogger()
error_tracker = ErrorTracker()
