from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from contextlib import contextmanager
from typing import Generator, Any
from flask import Flask
import logging
from .extensions import db  # Import db from extensions

logger = logging.getLogger(__name__)

def init_db(app: Flask) -> None:
    """Initialize database with PostgreSQL-specific configurations"""
    with app.app_context():
        # Register PostgreSQL-specific event listeners
        @event.listens_for(db.engine, 'connect')
        def set_postgresql_params(dbapi_connection: Any, connection_record: Any) -> None:
            with dbapi_connection.cursor() as cursor:
                cursor.execute("SET timezone='UTC';")
                cursor.execute("SET statement_timeout = '30s';")
                cursor.execute("SET lock_timeout = '10s';")

@contextmanager
def db_session() -> Generator:
    """Provide a transactional scope around a series of operations."""
    try:
        yield db.session
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error: {str(e)}")
        raise
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"Database operational error: {str(e)}")
        raise
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.session.remove()