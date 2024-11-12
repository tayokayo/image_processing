class DatabaseError(Exception):
    """Base exception for database errors"""
    pass

class PoolConnectionError(DatabaseError):
    """Raised when connection pool encounters an error"""
    pass

class ConfigurationError(Exception):
    """Raised when there's a configuration error"""
    pass

class SceneProcessingError(Exception):
    """Raised when there's an error processing a scene"""
    pass

class DatabaseOperationalError(DatabaseError):
    """Raised when there's a database operational error"""
    pass

class DatabaseIntegrityError(DatabaseError):
    """Raised when database integrity constraints are violated"""
    pass