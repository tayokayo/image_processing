import pytest
from sqlalchemy import text
from app.models import RoomScene, Component
from datetime import datetime

def test_jsonb_operations(session, test_scene):
    """Test PostgreSQL JSONB operations"""
    # Update metadata using JSONB operations
    session.execute(
        text("""
        UPDATE room_scenes 
        SET scene_metadata = scene_metadata || '{"new_key": "new_value"}'::jsonb 
        WHERE id = :scene_id
        """),
        {"scene_id": test_scene.id}
    )
    session.commit()
    
    # Verify JSONB update
    updated_scene = session.get(RoomScene, test_scene.id)
    assert updated_scene.scene_metadata.get('new_key') == 'new_value'
    
    # Test JSONB containment query
    result = session.query(RoomScene).filter(
        RoomScene.scene_metadata.contains({'test': 'data'})
    ).first()
    assert result is not None

def test_component_status_enum(session, test_component):
    """Test PostgreSQL enum type operations"""
    # Update status using enum
    test_component.status = 'ACCEPTED'
    session.commit()
    
    # Query using enum
    accepted_components = session.query(Component).filter(
        Component.status == 'ACCEPTED'
    ).all()
    assert len(accepted_components) == 1
    assert accepted_components[0].id == test_component.id

def test_gin_index_performance(session, test_scene):
    """Test GIN index performance for JSONB queries"""
    # Add test data
    test_scene.scene_metadata = {
        'attributes': ['modern', 'spacious'],
        'dimensions': {'width': 100, 'height': 200},
        'tags': ['living_room', 'contemporary']
    }
    session.commit()
    
    # Query using GIN index
    result = session.query(RoomScene).filter(
        RoomScene.scene_metadata['attributes'].contains(['modern'])
    ).explain()
    
    # Verify GIN index usage in query plan
    assert 'Index Scan' in str(result)
    assert 'gin' in str(result).lower()

def test_postgres_specific_features(session):
    """Test PostgreSQL-specific features"""
    # Test JSONB operations
    scene = RoomScene(
        name='JSONB Test',
        category='test',
        file_path='/test/path.jpg',
        scene_metadata={'test_key': 'test_value'}
    )
    session.add(scene)
    session.commit()
    
    # Test JSONB query
    result = session.query(RoomScene).filter(
        RoomScene.scene_metadata['test_key'].astext == 'test_value'
    ).first()
    assert result is not None
    
    # Test enum operations
    component = Component(
        room_scene_id=scene.id,
        name='Enum Test',
        component_type='test',
        file_path='/test/component.jpg',
        status='ACCEPTED'
    )
    session.add(component)
    session.commit()
    
    # Test enum filtering
    accepted = session.query(Component).filter_by(status='ACCEPTED').first()
    assert accepted is not None