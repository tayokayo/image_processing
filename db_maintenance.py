import click
from pathlib import Path
from app.database.maintenance import DatabaseMaintenance
from app import create_app

@click.group()
def cli():
    """Database maintenance commands"""
    pass

@cli.command()
@click.option('--backup-dir', default='backups', help='Backup directory')
def backup(backup_dir):
    """Create a database backup"""
    app = create_app('production')
    with app.app_context():
        maintenance = DatabaseMaintenance(backup_dir)
        backup_file = maintenance.create_backup()
        if backup_file:
            click.echo(f"Backup created: {backup_file}")
        else:
            click.echo("Backup failed")

@cli.command()
@click.argument('backup-file')
def restore(backup_file):
    """Restore a database backup"""
    app = create_app('production')
    with app.app_context():
        maintenance = DatabaseMaintenance()
        success = maintenance.restore_backup(Path(backup_file))
        if success:
            click.echo("Restore completed successfully")
        else:
            click.echo("Restore failed")

@cli.command()
def stats():
    """Show database statistics"""
    app = create_app('production')
    with app.app_context():
        maintenance = DatabaseMaintenance()
        stats = maintenance.get_database_stats()
        
        click.echo("\nDatabase Statistics:")
        click.echo(f"Size: {stats.get('database_size', 'Unknown')}")
        
        click.echo("\nTable Statistics:")
        for table in stats.get('tables', []):
            click.echo(f"{table['name']}: {table['rows']} rows, {table['size']}")
        
        click.echo("\nConnections:")
        for state, count in stats.get('connections', {}).items():
            click.echo(f"{state}: {count}")

if __name__ == '__main__':
    cli()