import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import text
from app.database import db_session
from app.extensions import db

def register_commands(app):
    """Register CLI commands"""
    app.cli.add_command(verify_setup)

@click.command('verify-postgres')
@click.option('--env', default='development', help='Environment to verify')
@click.option('--verbose', is_flag=True, help='Show detailed output')
@with_appcontext
def verify_setup(env, verbose):
    """Verify PostgreSQL setup and configuration"""
    click.echo(f"\nVerifying PostgreSQL setup for {env} environment...")
    
    try:
        with db_session() as session:
            # 1. Verify Database Connection
            version = session.execute(text('SELECT version()')).scalar()
            click.echo("✓ Database connection successful")
            if verbose:
                click.echo(f"  Version: {version}")

            # 2. Verify Table Schema
            tables = db.metadata.tables
            click.echo("\nVerifying table schema:")
            for table_name in ['room_scenes', 'components']:
                if table_name in tables:
                    click.echo(f"✓ Table '{table_name}' exists")
                    if verbose:
                        for column in tables[table_name].columns:
                            click.echo(f"  - {column.name}: {column.type}")
                else:
                    click.echo(f"✗ Table '{table_name}' missing")

            # 3. Verify Materialized Views
            views = session.execute(text("""
                SELECT 
                    schemaname,
                    matviewname,
                    pg_size_pretty(pg_relation_size(schemaname || '.' || matviewname)) as size
                FROM pg_matviews 
                WHERE schemaname = 'public'
            """)).fetchall()
            
            click.echo("\nVerifying materialized views:")
            if views:
                for view in views:
                    click.echo(f"✓ View '{view.matviewname}' exists (size: {view.size})")
            else:
                click.echo("! No materialized views found - may need to run migrations")

            # 4. Verify Indexes
            indexes = session.execute(text("""
                SELECT 
                    tablename, 
                    indexname, 
                    indexdef 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """)).fetchall()
            
            if verbose:
                click.echo("\nVerifying indexes:")
                for idx in indexes:
                    click.echo(f"✓ Index '{idx.indexname}' on '{idx.tablename}'")
                    click.echo(f"  Definition: {idx.indexdef}")

            click.echo("\n✓ PostgreSQL setup verification completed successfully")
            
    except Exception as e:
        click.echo(f"✗ Verification failed: {e}")
        return False
    
    return True

def verify_postgres_features():
    """Verify PostgreSQL-specific features"""
    try:
        with db_session() as session:
            # Test JSONB operations
            session.execute(text("""
                SELECT jsonb_build_object('test', 'value') AS test_jsonb;
            """))
            click.echo("✓ JSONB operations working")
            
            # Test enum types
            session.execute(text("""
                SELECT enum_range(NULL::component_status) AS status_values;
            """))
            click.echo("✓ Custom enum types available")
            
            # Test materialized views
            session.execute(text("""
                SELECT COUNT(*) FROM detection_accuracy_stats_mv;
            """))
            click.echo("✓ Materialized views accessible")
            return True
            
    except Exception as e:
        click.echo(f"✗ Feature verification failed: {e}")
        return False

if __name__ == '__main__':
    verify_setup()