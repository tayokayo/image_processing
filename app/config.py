import os
from dotenv import load_dotenv
import torch

load_dotenv()

class Config:
    # Common configurations
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    
    # SAM Model Configuration
    SAM_MODEL_PATH = os.getenv('SAM_MODEL_PATH', 'models/sam_vit_h_4b8939.pth')
    SAM_MODEL_TYPE = os.getenv('SAM_MODEL_TYPE', 'vit_h')
    SAM_DEVICE = os.getenv('SAM_DEVICE', 'cuda' if torch.cuda.is_available() else 'cpu')

    # PostgreSQL Database URI
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    
    # Connection Pool Settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'connect_args': {
            'application_name': 'modular_scenes',
            'options': '-c timezone=UTC'
        }
    }

class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('TEST_DB_NAME')}"
    )

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}