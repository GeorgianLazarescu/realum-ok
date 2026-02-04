import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import os
from typing import Optional, List
import gzip
import shutil
import json
from core.logging import get_logger

logger = get_logger("backup")

class DatabaseBackup:
    """MongoDB Backup and Recovery System"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backups = 30
        self.mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        self.db_name = os.getenv("DB_NAME", "realum")

    async def create_backup(self, compress: bool = True) -> Optional[str]:
        """Create a MongoDB backup using mongodump"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = f"realum_backup_{timestamp}"
            backup_path = self.backup_dir / backup_folder

            logger.info(f"Starting MongoDB backup: {backup_folder}")

            # Try using mongodump if available
            try:
                result = subprocess.run(
                    [
                        "mongodump",
                        "--uri", self.mongo_url,
                        "--db", self.db_name,
                        "--out", str(backup_path)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode != 0:
                    logger.warning(f"mongodump not available or failed: {result.stderr}")
                    # Fallback to JSON export
                    return await self._create_json_backup(timestamp, compress)
            except FileNotFoundError:
                logger.warning("mongodump not found, falling back to JSON export")
                return await self._create_json_backup(timestamp, compress)

            # Compress the backup folder
            if compress and backup_path.exists():
                compressed_path = self._compress_backup_folder(backup_path)
                shutil.rmtree(backup_path)
                final_path = compressed_path
            else:
                final_path = backup_path

            file_size = self._get_size(final_path)
            logger.info(f"Backup completed: {final_path.name} ({file_size:.2f} MB)")

            await self._cleanup_old_backups()

            return str(final_path)

        except subprocess.TimeoutExpired:
            logger.error("Backup timed out after 5 minutes")
            return None
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return None

    async def _create_json_backup(self, timestamp: str, compress: bool = True) -> Optional[str]:
        """Create a JSON-based backup by exporting collections"""
        from core.database import db
        
        try:
            backup_filename = f"realum_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            backup_data = {
                "timestamp": timestamp,
                "database": self.db_name,
                "collections": {}
            }

            # Get all collection names
            collections = await db.list_collection_names()
            
            for collection_name in collections:
                try:
                    docs = await db[collection_name].find({}, {"_id": 0}).to_list(None)
                    backup_data["collections"][collection_name] = docs
                    logger.info(f"Exported {len(docs)} documents from {collection_name}")
                except Exception as e:
                    logger.warning(f"Failed to export {collection_name}: {e}")
            
            # Write JSON backup
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, default=str, indent=2)
            
            # Compress if requested
            if compress:
                compressed_path = self._compress_backup(backup_path)
                backup_path.unlink()
                backup_path = compressed_path
            
            file_size = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"JSON backup completed: {backup_path.name} ({file_size:.2f} MB)")
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"JSON backup failed: {str(e)}")
            return None

    def _compress_backup(self, backup_path: Path) -> Path:
        """Compress a single file backup"""
        compressed_path = backup_path.with_suffix(backup_path.suffix + ".gz")

        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        logger.info(f"Backup compressed: {compressed_path.name}")
        return compressed_path

    def _compress_backup_folder(self, backup_path: Path) -> Path:
        """Compress a backup folder to tar.gz"""
        compressed_path = backup_path.with_suffix(".tar.gz")
        
        shutil.make_archive(
            str(backup_path),
            'gztar',
            backup_path.parent,
            backup_path.name
        )
        
        # Rename from .tar.gz to proper name
        archive_path = Path(str(backup_path) + ".tar.gz")
        if archive_path.exists():
            return archive_path
        
        return compressed_path

    def _get_size(self, path: Path) -> float:
        """Get size of file or folder in MB"""
        if path.is_file():
            return path.stat().st_size / (1024 * 1024)
        elif path.is_dir():
            total = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
            return total / (1024 * 1024)
        return 0

    async def _cleanup_old_backups(self):
        """Remove old backups beyond retention limit"""
        backups = sorted(
            [p for p in self.backup_dir.glob("realum_backup_*") if p.is_file() or p.is_dir()],
            key=lambda p: p.stat().st_mtime
        )

        if len(backups) > self.max_backups:
            to_delete = backups[:-self.max_backups]
            for backup in to_delete:
                if backup.is_file():
                    backup.unlink()
                elif backup.is_dir():
                    shutil.rmtree(backup)
                logger.info(f"Deleted old backup: {backup.name}")

    async def restore_backup(self, backup_file: str) -> bool:
        """Restore from a backup file"""
        try:
            backup_path = self.backup_dir / backup_file

            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False

            logger.info(f"Restoring database from: {backup_file}")

            # Handle different backup formats
            if backup_file.endswith('.json.gz'):
                return await self._restore_json_backup(backup_path, compressed=True)
            elif backup_file.endswith('.json'):
                return await self._restore_json_backup(backup_path, compressed=False)
            elif backup_file.endswith('.tar.gz'):
                return await self._restore_mongodump_backup(backup_path)
            else:
                logger.error(f"Unknown backup format: {backup_file}")
                return False

        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False

    async def _restore_json_backup(self, backup_path: Path, compressed: bool = False) -> bool:
        """Restore from JSON backup"""
        from core.database import db
        
        try:
            if compressed:
                with gzip.open(backup_path, 'rt') as f:
                    backup_data = json.load(f)
            else:
                with open(backup_path, 'r') as f:
                    backup_data = json.load(f)
            
            collections = backup_data.get("collections", {})
            
            for collection_name, documents in collections.items():
                if documents:
                    # Clear existing collection
                    await db[collection_name].delete_many({})
                    # Insert backed up documents
                    await db[collection_name].insert_many(documents)
                    logger.info(f"Restored {len(documents)} documents to {collection_name}")
            
            logger.info("JSON backup restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"JSON restore failed: {str(e)}")
            return False

    async def _restore_mongodump_backup(self, backup_path: Path) -> bool:
        """Restore from mongodump backup"""
        try:
            # Extract the archive
            temp_dir = self.backup_dir / "temp_restore"
            shutil.unpack_archive(backup_path, temp_dir)
            
            # Find the database folder
            db_folder = temp_dir / backup_path.stem.replace('.tar', '') / self.db_name
            
            if not db_folder.exists():
                # Try finding any folder with BSON files
                for item in temp_dir.rglob("*.bson"):
                    db_folder = item.parent
                    break
            
            result = subprocess.run(
                [
                    "mongorestore",
                    "--uri", self.mongo_url,
                    "--db", self.db_name,
                    "--drop",
                    str(db_folder)
                ],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            # Cleanup temp directory
            shutil.rmtree(temp_dir)
            
            if result.returncode != 0:
                logger.error(f"mongorestore failed: {result.stderr}")
                return False
            
            logger.info("mongodump backup restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"mongodump restore failed: {str(e)}")
            return False

    def list_backups(self) -> List[dict]:
        """List all available backups"""
        backups = []

        for backup_path in sorted(self.backup_dir.glob("realum_backup_*"), reverse=True):
            stat = backup_path.stat()
            backups.append({
                "filename": backup_path.name,
                "size_mb": self._get_size(backup_path),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "is_compressed": backup_path.suffix in [".gz", ".tar.gz"] or backup_path.name.endswith('.tar.gz'),
                "type": "folder" if backup_path.is_dir() else "file"
            })

        return backups

    async def schedule_automatic_backups(self):
        """Run automatic daily backups"""
        logger.info("Starting automatic backup scheduler")

        while True:
            try:
                # Wait 24 hours between backups
                await asyncio.sleep(24 * 60 * 60)
                await self.create_backup(compress=True)
            except asyncio.CancelledError:
                logger.info("Backup scheduler stopped")
                break
            except Exception as e:
                logger.error(f"Scheduled backup failed: {str(e)}")

    def get_backup_statistics(self) -> dict:
        """Get backup statistics"""
        backups = self.list_backups()
        total_size = sum(b["size_mb"] for b in backups)

        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size, 2),
            "oldest_backup": backups[-1]["created_at"] if backups else None,
            "newest_backup": backups[0]["created_at"] if backups else None,
            "average_size_mb": round(total_size / len(backups), 2) if backups else 0,
            "backup_directory": str(self.backup_dir),
            "max_backups_retained": self.max_backups
        }

# Global instance
database_backup = DatabaseBackup()
