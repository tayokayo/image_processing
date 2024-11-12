import pytest
from app import create_app
from app.extensions import db
from app.database import db_session
from app.models import RoomScene, Component
from sqlalchemy import text

@pytest.fixture(scope='session')
def app():
    """Create test application"""
    app = create_app('testing')
    return app

@pytest.fixture(scope='session')
def _db(app):
    """Create test database"""
    with app.app_context():
        # Drop existing tables and views
        db.session.execute(text("DROP MATERIALIZED VIEW IF EXISTS review_metrics_mv CASCADE"))
        db.session.execute(text("DROP MATERIALIZED VIEW IF EXISTS detection_accuracy_stats_mv CASCADE"))
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def session(_db, app):
    """Create fresh database session for tests"""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Create session with connection
        session = db.create_scoped_session(
            options={"bind": connection, "binds": {}}
        )
        
        db.session = session
        
        yield session
        
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture
def test_scene(session):
    """Create test room scene"""
    scene = RoomScene(
        name='Test Scene',
        category='living_room',
        file_path='/test/path.jpg',
        scene_metadata={'test': 'data'}
    )
    session.add(scene)
    session.commit()
    return scene