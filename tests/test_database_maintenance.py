import pytest
from pathlib import Path
from app.database.maintenance import DatabaseMaintenance
from app import create_app

@pytest.fixture
def maintenance():
    app = create_app('testing')
    with app.app_context():
        return DatabaseMaintenance(backup_dir='test_backups')

def test_backup_restore_flow(maintenance):
    """Test backup creation and restoration"""
    # Create backup
    backup_file = maintenance.create_backup()
    assert backup_file is not None
    assert backup_file.exists()
    
    # Verify backup file
    assert backup_file.stat().st_size > 0
    
    # Test restore
    assert maintenance.restore_backup(backup_file)

def test_database_stats(maintenance):
    """Test database statistics collection"""
    stats = maintenance.get_database_stats()
    
    assert 'database_size' in stats
    assert 'tables' in stats
    assert 'connections' in stats
    
    # Verify table stats
    assert any(table['name'] == 'room_scenes' for table in stats['tables'])
    assert any(table['name'] == 'components' for table in stats['tables'])

@pytest.fixture(autouse=True)
def cleanup():
    yield
    # Clean up test backups
    backup_dir = Path('test_backups')
    if backup_dir.exists():
        for file in backup_dir.glob('*'):
            file.unlink()
        backup_dir.rmdir()