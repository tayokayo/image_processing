from app import create_app
from sqlalchemy import text
from app.extensions import db

def verify_database():
    """Verify database setup and connections"""
    app = create_app('testing')
    
    print("\nStarting database verification...")
    
    with app.app_context():
        try:
            # First verify basic connection
            result = db.session.execute(text('SELECT version()')).scalar()
            print(f"\n✓ Database connection works")
            print(f"PostgreSQL version: {result}")
            
            # Check tables
            result = db.session.execute(text("""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema='public'
                AND table_type='BASE TABLE'
            """))
            tables = result.fetchall()
            
            if tables:
                print("\nFound tables:")
                for table in tables:
                    print(f"- {table[0]} ({table[1]})")
            else:
                print("\n⚠️  No tables found in public schema")
            
            # Check materialized views
            views = db.session.execute(text("""
                SELECT matviewname, definition
                FROM pg_matviews 
                WHERE schemaname = 'public'
            """))
            view_list = views.fetchall()
            
            if view_list:
                print("\nFound materialized views:")
                for view in view_list:
                    print(f"- {view[0]}")
            else:
                print("\n⚠️  No materialized views found")
            
            # Verify table structures
            print("\nVerifying table structures...")
            
            # Check room_scenes structure
            columns = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'room_scenes'
                ORDER BY ordinal_position;
            """))
            
            print("\nroom_scenes columns:")
            for col in columns:
                print(f"- {col[0]}: {col[1]} (nullable: {col[2]})")
            
            # Check components structure
            columns = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'components'
                ORDER BY ordinal_position;
            """))
            
            print("\ncomponents columns:")
            for col in columns:
                print(f"- {col[0]}: {col[1]} (nullable: {col[2]})")
            
            print("\n✓ Database verification completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Verification failed: {e}")
        finally:
            db.session.remove()

if __name__ == '__main__':
    verify_database()