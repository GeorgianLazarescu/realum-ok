import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import os
from typing import Optional, List
import gzip
import shutil
from backend.core.logging import get_logger

logger = get_logger("backup")

class DatabaseBackup:
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backups = 30
        self.database_url = os.getenv("DATABASE_URL")

    async def create_backup(self, compress: bool = True) -> Optional[str]:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"realum_backup_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename

            logger.info(f"Starting database backup: {backup_filename}")

            if self.database_url:
                result = subprocess.run(
                    ["pg_dump", self.database_url, "-f", str(backup_path)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode != 0:
                    logger.error(f"Backup failed: {result.stderr}")
                    return None
            else:
                logger.warning("DATABASE_URL not found, creating dummy backup for development")
                with open(backup_path, 'w') as f:
                    f.write(f"-- Backup created at {datetime.now()}\n")
                    f.write("-- This is a development mode backup\n")

            if compress and backup_path.exists():
                compressed_path = self._compress_backup(backup_path)
                backup_path.unlink()
                backup_path = compressed_path

            file_size = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"Backup completed: {backup_path.name} ({file_size:.2f} MB)")

            await self._cleanup_old_backups()

            return str(backup_path)

        except subprocess.TimeoutExpired:
            logger.error("Backup timed out after 5 minutes")
            return None
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return None

    def _compress_backup(self, backup_path: Path) -> Path:
        compressed_path = backup_path.with_suffix(".sql.gz")

        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        logger.info(f"Backup compressed: {compressed_path.name}")
        return compressed_path

    async def _cleanup_old_backups(self):
        backups = sorted(self.backup_dir.glob("realum_backup_*.sql*"))

        if len(backups) > self.max_backups:
            to_delete = backups[:-self.max_backups]
            for backup in to_delete:
                backup.unlink()
                logger.info(f"Deleted old backup: {backup.name}")

    async def restore_backup(self, backup_file: str) -> bool:
        try:
            backup_path = self.backup_dir / backup_file

            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False

            if backup_path.suffix == ".gz":
                temp_path = backup_path.with_suffix("")
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                backup_path = temp_path

            logger.info(f"Restoring database from: {backup_file}")

            if self.database_url:
                result = subprocess.run(
                    ["psql", self.database_url, "-f", str(backup_path)],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if result.returncode != 0:
                    logger.error(f"Restore failed: {result.stderr}")
                    return False
            else:
                logger.warning("DATABASE_URL not found, simulating restore for development")

            logger.info(f"Database restored successfully from: {backup_file}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False

    def list_backups(self) -> List[dict]:
        backups = []

        for backup_path in sorted(self.backup_dir.glob("realum_backup_*.sql*"), reverse=True):
            stat = backup_path.stat()
            backups.append({
                "filename": backup_path.name,
                "size_mb": stat.st_size / (1024 * 1024),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "compressed": backup_path.suffix == ".gz"
            })

        return backups

    async def schedule_automatic_backups(self):
        logger.info("Starting automatic backup scheduler")

        while True:
            try:
                await asyncio.sleep(24 * 60 * 60)
                await self.create_backup(compress=True)
            except asyncio.CancelledError:
                logger.info("Backup scheduler stopped")
                break
            except Exception as e:
                logger.error(f"Scheduled backup failed: {str(e)}")

    def get_backup_statistics(self) -> dict:
        backups = self.list_backups()
        total_size = sum(b["size_mb"] for b in backups)

        return {
            "total_backups": len(backups),
            "total_size_mb": total_size,
            "oldest_backup": backups[-1]["created_at"] if backups else None,
            "newest_backup": backups[0]["created_at"] if backups else None,
            "average_size_mb": total_size / len(backups) if backups else 0
        }

database_backup = DatabaseBackup()
