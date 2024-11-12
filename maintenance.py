import os
import subprocess
from datetime import datetime
from pathlib import Path
import logging
from typing import Optional, Dict, List
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from ..config import Config

logger = logging.getLogger(__name__)

class DatabaseMaintenance:
    def __init__(self, backup_dir: str = 'backups'):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.db_url = Config.SQLALCHEMY_DATABASE_URI
        
    def create_backup(self) -> Optional[Path]:
        """Create a PostgreSQL backup using pg_dump"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f'backup_{timestamp}.sql'
            
            # Extract database connection info from URL
            db_info = self._parse_db_url()
            
            # Create pg_dump command
            cmd = [
                'pg_dump',
                '-h', db_info['host'],
                '-p', db_info['port'],
                '-U', db_info['user'],
                '-F', 'c',  # Custom format
                '-b',  # Include large objects
                '-v',  # Verbose
                '-f', str(backup_file),
                db_info['dbname']
            ]
            
            # Execute backup
            result = subprocess.run(
                cmd, 
                env={'PGPASSWORD': db_info['password']},
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Backup created successfully: {backup_file}")
                return backup_file
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Backup creation failed: {str(e)}")
            return None
    
    def restore_backup(self, backup_file: Path) -> bool:
        """Restore a PostgreSQL backup"""
        try:
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")
            
            db_info = self._parse_db_url()
            
            # Create pg_restore command
            cmd = [
                'pg_restore',
                '-h', db_info['host'],
                '-p', db_info['port'],
                '-U', db_info['user'],
                '-d', db_info['dbname'],
                '-v',
                str(backup_file)
            ]
            
            result = subprocess.run(
                cmd,
                env={'PGPASSWORD': db_info['password']},
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Backup restored successfully")
                return True
            else:
                logger.error(f"Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False
    
    def get_database_stats(self) -> Dict:
        """Get database statistics and health metrics"""
        try:
            conn = psycopg2.connect(self.db_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            
            stats = {}
            
            # Database size
            cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            stats['database_size'] = cur.fetchone()[0]
            
            # Table statistics
            cur.execute("""
                SELECT relname as table_name,
                       n_live_tup as row_count,
                       pg_size_pretty(pg_total_relation_size(relid)) as total_size
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            """)
            stats['tables'] = [dict(zip(['name', 'rows', 'size'], row)) 
                             for row in cur.fetchall()]
            
            # Connection info
            cur.execute("""
                SELECT count(*), state
                FROM pg_stat_activity
                GROUP BY state
            """)
            stats['connections'] = dict(cur.fetchall())
            
            cur.close()
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {}
    
    def _parse_db_url(self) -> Dict[str, str]:
        """Parse database URL into components"""
        from urllib.parse import urlparse
        
        parsed = urlparse(self.db_url)
        return {
            'user': parsed.username,
            'password': parsed.password,
            'host': parsed.hostname,
            'port': str(parsed.port or 5432),
            'dbname': parsed.path[1:]  # Remove leading slash
        }