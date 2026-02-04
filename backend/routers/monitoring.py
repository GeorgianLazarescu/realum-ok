from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from core.auth import require_admin
from core.backup import database_backup
from core.logging import error_tracker, get_logger
from core.rate_limiter import rate_limiter
from datetime import datetime, timedelta
import psutil
import os

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])
logger = get_logger("monitoring")

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@router.get("/system-stats", dependencies=[Depends(require_admin)])
async def get_system_stats():
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total_gb": memory.total / (1024 ** 3),
                "used_gb": memory.used / (1024 ** 3),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total / (1024 ** 3),
                "used_gb": disk.used / (1024 ** 3),
                "percent": disk.percent
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/error-stats", dependencies=[Depends(require_admin)])
async def get_error_stats():
    try:
        stats = error_tracker.get_error_stats()
        return {
            "errors": stats,
            "total_errors": sum(stats.values()),
            "unique_errors": len(stats),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/error-stats/reset", dependencies=[Depends(require_admin)])
async def reset_error_stats():
    try:
        error_tracker.reset_stats()
        return {"message": "Error statistics reset successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backups", dependencies=[Depends(require_admin)])
async def list_backups():
    try:
        backups = database_backup.list_backups()
        stats = database_backup.get_backup_statistics()

        return {
            "backups": backups,
            "statistics": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backups/create", dependencies=[Depends(require_admin)])
async def create_backup(compress: bool = True):
    try:
        backup_path = await database_backup.create_backup(compress=compress)

        if backup_path:
            return {
                "message": "Backup created successfully",
                "backup_path": backup_path
            }
        else:
            raise HTTPException(status_code=500, detail="Backup failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backups/restore", dependencies=[Depends(require_admin)])
async def restore_backup(backup_filename: str):
    try:
        success = await database_backup.restore_backup(backup_filename)

        if success:
            return {"message": "Backup restored successfully"}
        else:
            raise HTTPException(status_code=500, detail="Restore failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rate-limits", dependencies=[Depends(require_admin)])
async def get_rate_limit_stats():
    try:
        return {
            "active_requests": len(rate_limiter.requests),
            "blocked_ips": len(rate_limiter.blocked_ips),
            "blocked_ips_list": [
                {
                    "ip": ip,
                    "blocked_until": block_time.isoformat()
                }
                for ip, block_time in rate_limiter.blocked_ips.items()
            ],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rate-limits/unblock-ip", dependencies=[Depends(require_admin)])
async def unblock_ip(ip_address: str):
    try:
        await rate_limiter.unblock_ip(ip_address)
        return {"message": f"IP {ip_address} unblocked successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rate-limits/block-ip", dependencies=[Depends(require_admin)])
async def block_ip(ip_address: str, duration_hours: int = 24):
    try:
        await rate_limiter.block_ip(ip_address, duration_hours)
        return {
            "message": f"IP {ip_address} blocked for {duration_hours} hours"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/recent", dependencies=[Depends(require_admin)])
async def get_recent_logs(lines: int = 100, log_type: str = "errors"):
    try:
        log_file_map = {
            "errors": "logs/errors.log",
            "security": "logs/security.log",
            "audit": "logs/audit.log"
        }

        log_file = log_file_map.get(log_type, "logs/errors.log")

        if not os.path.exists(log_file):
            return {"logs": [], "message": "Log file not found"}

        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]

        return {
            "logs": [line.strip() for line in recent_lines],
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard", dependencies=[Depends(require_admin)])
async def get_admin_dashboard():
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        error_stats = error_tracker.get_error_stats()
        backup_stats = database_backup.get_backup_statistics()

        return {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent
            },
            "errors": {
                "total": sum(error_stats.values()),
                "unique": len(error_stats)
            },
            "backups": backup_stats,
            "rate_limiting": {
                "active_limits": len(rate_limiter.requests),
                "blocked_ips": len(rate_limiter.blocked_ips)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
