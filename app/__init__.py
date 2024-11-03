from flask import Flask
from flask_migrate import Migrate
from .config import Config, config
from .database import db
from filters import init_filters

migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    
    # Handle both string config names and config objects
    if isinstance(config_class, str):
        app.config.from_object(config[config_class])
    else:
        app.config.from_object(config_class)
    
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Initialize Flask-Migrate
    migrate.init_app(app, db)

    # Initialize Filters
    init_filters(app)
    
    # Register routes - both main and admin blueprints
    from .routes import main_bp, admin_bp
    app.register_blueprint(main_bp)  # This will be at '/'
    app.register_blueprint(admin_bp)  # This will be at '/admin'
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200
    
    # Add custom template filter
    @app.template_filter('avg')
    def avg_filter(lst):
        return sum(lst) / len(lst) if lst else 0

    return app