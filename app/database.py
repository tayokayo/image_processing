from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .config import Config

# Initialize Flask-SQLAlchemy
db = SQLAlchemy()

# Create DatabaseManager for custom session handling
class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
    
    def init_db(self):
        """Initialize the database, creating all tables"""
        db.create_all()
    
    def get_session(self):
        """Get a new database session"""
        return self.Session()
    
    def cleanup_session(self):
        """Remove the current session"""
        self.Session.remove()

# Create global database manager instance
db_manager = DatabaseManager()