from flask import Flask
from .extensions import db, Migrate
from .database import init_db
from .verify_postgres_setup import register_commands, verify_setup
from .tasks import start_view_refresh_scheduler
from .config import config
import logging
from logging.handlers import RotatingFileHandler
import os
from os import environ

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Load config based on environment
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)  # Initialize SQLAlchemy with the app
    migrate = Migrate(app, db)

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    app.logger.info('Application startup')
    
    # Configure database URI based on environment
    db_name = environ.get('TEST_DB_NAME') if config_name == 'testing' else environ.get('DB_NAME')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://{}:{}@{}:{}/{}'.format(
        environ.get('DB_USER'),
        environ.get('DB_PASSWORD'),
        environ.get('DB_HOST'),
        environ.get('DB_PORT'),
        db_name
    )
    
    # Configure SQLAlchemy settings
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'max_overflow': 2
    }
    
    # Ensure logs directory exists
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging
    handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=10240000, 
        backupCount=10
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')
    
    # Initialize database
    init_db(app)  # Perform additional database setup

    # Register CLI commands
    register_commands(app)
    
    # Start materialized view refresh scheduler if not in testing mode
    if not app.config['TESTING']:
        try:
            start_view_refresh_scheduler()
            app.logger.info('View refresh scheduler started')
        except Exception as e:
            app.logger.error(f'Failed to start view refresh scheduler: {e}')
    
    # Register blueprints
    try:
        from .routes import main_bp, admin_bp
        app.register_blueprint(main_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.logger.info('Blueprints registered successfully')
    except ImportError as e:
        app.logger.error(f'Failed to register blueprints: {e}')
        if not app.debug:
            raise
    
    # Session Cleanup
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            app.logger.error(f'Exception during request: {exception}')
            db.session.rollback()
        db.session.remove()

    # Register error handlers
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        return {"error": "Internal Server Error"}, 500

    @app.errorhandler(404)
    def not_found_error(error):
        return {"error": "Not Found"}, 404
    
    return app