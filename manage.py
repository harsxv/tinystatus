import click
import os
import sys
from pathlib import Path
import yaml
from datetime import datetime
import json
from app.config import get_settings
import os
from dotenv import load_dotenv, set_key
from app.database import User, ServiceHealthCheck, get_db
from datetime import datetime, timedelta
from sqlalchemy.sql import func
import secrets
import string

# Add app directory to path
sys.path.append(str(Path(__file__).parent))

from app.database import init_db, get_db, Base, engine
from app.config import get_settings

settings = get_settings()

@click.group()
def cli():
    """StatusWatch Management CLI"""
    pass

@cli.command()
@click.option('--username', prompt=True, help='Admin username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
def createuser(username, password):
    """Create a new admin user"""
    try:
        from app.database import User
        db = next(get_db())
        
        # Check if user exists
        if db.query(User).filter(User.username == username).first():
            click.echo(f"User {username} already exists!", err=True)
            return
        
        # Create user
        user = User(username=username)
        user.set_password(password)
        
        db.add(user)
        user.generate_token()
        db.commit()
        
        click.echo(f"Created user: {username}")
    except Exception as e:
        click.echo(f"Error creating user: {str(e)}", err=True)

@cli.command()
def initdb():
    """Initialize the database"""
    try:
        init_db()
        click.echo("Database initialized successfully!")
    except Exception as e:
        click.echo(f"Error initializing database: {str(e)}", err=True)

@cli.command()
def resetdb():
    """Reset the database (WARNING: This will delete all data)"""
    if click.confirm('Are you sure you want to reset the database? This will delete all data!'):
        try:
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)
            click.echo("Database reset successfully!")
        except Exception as e:
            click.echo(f"Error resetting database: {str(e)}", err=True)

@cli.command()
@click.argument('output', type=click.Path())
def backup(output):
    """Backup the database and configuration"""
    try:
        from app.database import ServiceHealthCheck
        db = next(get_db())
        
        # Get all data
        checks = db.query(ServiceHealthCheck).all()
        
        # Prepare backup data
        backup_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.1.0',
            'checks': [
                {
                    'timestamp': check.timestamp.isoformat(),
                    'service_name': check.service_name,
                    'service_group': check.service_group,
                    'status': check.status,
                    'response_time': check.response_time,
                    'extra_data': check.extra_data
                }
                for check in checks
            ]
        }
        
        # Save backup
        with open(output, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        click.echo(f"Backup saved to: {output}")
    except Exception as e:
        click.echo(f"Error creating backup: {str(e)}", err=True)

@cli.command()
@click.argument('backup_file', type=click.Path(exists=True))
def restore(backup_file):
    """Restore from a backup file"""
    if click.confirm('This will overwrite existing data. Continue?'):
        try:
            from app.database import ServiceHealthCheck
            db = next(get_db())
            
            # Load backup
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Clear existing data
            db.query(ServiceHealthCheck).delete()
            
            # Restore checks
            for check_data in backup_data['checks']:
                check = ServiceHealthCheck(
                    timestamp=datetime.fromisoformat(check_data['timestamp']),
                    service_name=check_data['service_name'],
                    service_group=check_data['service_group'],
                    status=check_data['status'],
                    response_time=check_data['response_time'],
                    extra_data=check_data['extra_data']
                )
                db.add(check)
            
            db.commit()
            click.echo("Backup restored successfully!")
        except Exception as e:
            click.echo(f"Error restoring backup: {str(e)}", err=True)

@cli.command()
def checkconfig():
    """Validate configuration files"""
    try:
        # Check checks.yaml
        if os.path.exists('checks.yaml'):
            with open('checks.yaml', 'r') as f:
                yaml.safe_load(f)
            click.echo("✓ checks.yaml is valid")
        else:
            click.echo("⨯ checks.yaml not found", err=True)
        
        # Check incidents.md
        if os.path.exists('incidents.md'):
            with open('incidents.md', 'r') as f:
                f.read()
            click.echo("✓ incidents.md is valid")
        else:
            click.echo("⨯ incidents.md not found", err=True)
        
        # Check environment variables
        required_vars = ['MONITOR_CONTINUOUSLY', 'CHECK_INTERVAL', 'MAX_HISTORY_ENTRIES']
        for var in required_vars:
            if hasattr(settings, var):
                click.echo(f"✓ {var} is set")
            else:
                click.echo(f"⨯ {var} is not set", err=True)
                
    except Exception as e:
        click.echo(f"Error checking configuration: {str(e)}", err=True)

@cli.command()
def shell():
    """Start an interactive shell with app context"""
    import code
    from app.database import ServiceHealthCheck, User
    from app.services.monitor import StatusMonitor
    
    context = {
        'db': next(get_db()),
        'ServiceHealthCheck': ServiceHealthCheck,
        'User': User,
        'StatusMonitor': StatusMonitor,
        'settings': settings
    }
    
    banner = "StatusWatch Interactive Shell\n" + \
             "Available objects: db, ServiceHealthCheck, User, StatusMonitor, settings"
    
    code.interact(banner=banner, local=context)

@cli.group()
def token():
    """Manage API tokens"""
    pass

@token.command()
@click.argument('username')
@click.option('--expires', type=int, help='Token expiry in days')
def create(username, expires):
    """Create a new API token for a user"""
    try:
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            click.echo(f"User {username} not found!", err=True)
            return
        
        token = user.generate_token(expires_in_days=expires)
        db.commit()
        
        click.echo(f"Token generated for {username}:")
        click.echo(f"Token: {token}")
        if expires:
            click.echo(f"Expires: {user.token_expiry}")
        else:
            click.echo("Token never expires")
            
    except Exception as e:
        click.echo(f"Error generating token: {str(e)}", err=True)

@token.command()
@click.argument('username')
def revoke(username):
    """Revoke a user's API token"""
    try:
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            click.echo(f"User {username} not found!", err=True)
            return
        
        if not user.api_token:
            click.echo(f"User {username} has no active token!", err=True)
            return
        
        user.revoke_token()
        db.commit()
        
        click.echo(f"Token revoked for {username}")
    except Exception as e:
        click.echo(f"Error revoking token: {str(e)}", err=True)

@token.command()
@click.argument('username')
def info(username):
    """Show token information for a user"""
    try:
        db = next(get_db())
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            click.echo(f"User {username} not found!", err=True)
            return
        
        if not user.api_token:
            click.echo(f"User {username} has no active token")
            return
        
        click.echo(f"Token information for {username}:")
        click.echo(f"Token: {user.api_token}")
        if user.token_expiry:
            remaining = user.token_expiry - datetime.utcnow()
            if remaining.total_seconds() > 0:
                click.echo(f"Expires in: {remaining.days} days, {remaining.seconds//3600} hours")
            else:
                click.echo("Token has expired")
        else:
            click.echo("Token never expires")
        
        click.echo(f"Valid: {'Yes' if user.is_token_valid() else 'No'}")
        
    except Exception as e:
        click.echo(f"Error getting token info: {str(e)}", err=True)

@token.command()
def list():
    """List all users and their token status"""
    try:
        db = next(get_db())
        users = db.query(User).all()
        
        if not users:
            click.echo("No users found")
            return
        
        click.echo("\nUser Token Status:")
        click.echo("-" * 50)
        
        for user in users:
            status = "No token"
            if user.api_token:
                if user.is_token_valid():
                    status = "Valid"
                    if user.token_expiry:
                        remaining = user.token_expiry - datetime.utcnow()
                        if remaining.total_seconds() > 0:
                            status += f" (Expires in {remaining.days}d {remaining.seconds//3600}h)"
                else:
                    status = "Expired"
            
            click.echo(f"{user.username}: {status}")
            
    except Exception as e:
        click.echo(f"Error listing tokens: {str(e)}", err=True)

@cli.group()
def auth():
    """Manage authentication settings"""
    pass

@auth.command()
def status():
    """Show current auth status"""
    settings = get_settings()
    click.echo(f"Authentication is currently: {'enabled' if settings.AUTH_ENABLED else 'disabled'}")
    
    if settings.AUTH_ENABLED:
        db = next(get_db())
        users = db.query(User).count()
        click.echo(f"Number of users: {users}")

@auth.command()
def enable():
    """Enable authentication"""
    env_file = '.env'
    try:
        # Check if we can write to the file
        try:
            with open(env_file, 'a') as f:
                pass
        except (IOError, PermissionError):
            click.echo(f"Error: Cannot write to {env_file}. Please check permissions.", err=True)
            return

        load_dotenv(env_file)
        set_key(env_file, 'AUTH_ENABLED', 'true')
        click.echo("Authentication enabled")
        click.echo("Please restart the application for changes to take effect")
        
        # Check if there are any users
        db = next(get_db())
        if db.query(User).count() == 0:
            click.echo("\nWarning: No users exist. Create a user with:")
            click.echo("python manage.py createuser")
    except Exception as e:
        click.echo(f"Error enabling authentication: {str(e)}", err=True)
        click.echo("\nTip: You can manually set AUTH_ENABLED=true in your environment")

@auth.command()
def disable():
    """Disable authentication"""
    if click.confirm('Are you sure you want to disable authentication? This will make your instance public!'):
        env_file = '.env'
        try:
            # Check if we can write to the file
            try:
                with open(env_file, 'a') as f:
                    pass
            except (IOError, PermissionError):
                click.echo(f"Error: Cannot write to {env_file}. Please check permissions.", err=True)
                return

            load_dotenv(env_file)
            set_key(env_file, 'AUTH_ENABLED', 'false')
            click.echo("Authentication disabled")
            click.echo("Please restart the application for changes to take effect")
        except Exception as e:
            click.echo(f"Error disabling authentication: {str(e)}", err=True)
            click.echo("\nTip: You can manually set AUTH_ENABLED=false in your environment")

@auth.command()
def setup():
    """Interactive auth setup"""
    click.echo("StatusWatch Authentication Setup")
    click.echo("-" * 30)
    
    # Check if we can write to .env
    env_file = '.env'
    try:
        try:
            with open(env_file, 'a') as f:
                pass
        except (IOError, PermissionError):
            click.echo(f"Warning: Cannot write to {env_file}. Authentication settings must be set manually.", err=True)
            click.echo("Please set AUTH_ENABLED=true in your environment")
    except Exception as e:
        click.echo(f"Warning: {str(e)}", err=True)
    
    try:
        # Enable auth if we can
        if os.access(env_file, os.W_OK):
            load_dotenv(env_file)
            set_key(env_file, 'AUTH_ENABLED', 'true')
        
        # Create admin user if none exists
        db = next(get_db())
        if db.query(User).count() == 0:
            click.echo("\nNo users exist. Let's create an admin user.")
            username = click.prompt("Username")
            password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
            
            user = User(username=username)
            user.set_password(password)
            db.add(user)
            db.commit()
            
            # Generate API token
            token = user.generate_token()
            db.commit()
            
            click.echo("\nUser created successfully!")
            click.echo(f"API Token: {token}")
        
        click.echo("\nAuthentication setup complete!")
        if os.access(env_file, os.W_OK):
            click.echo("Please restart the application for changes to take effect")
        else:
            click.echo("\nNote: You need to manually set AUTH_ENABLED=true in your environment")
            
    except Exception as e:
        click.echo(f"Error during setup: {str(e)}", err=True)
        click.echo("\nTip: You can manually configure authentication settings in your environment")

@cli.group()
def db():
    """Database management commands"""
    pass

@db.command()
@click.option('--group', help='Group name to remove entries for')
@click.option('--service', help='Service name to remove entries for')
@click.option('--older-than', type=int, help='Remove entries older than X days')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without actually deleting')
def cleanup(group, service, older_than, dry_run):
    """Remove entries from database by group or service name"""
    try:
        db = next(get_db())
        query = db.query(ServiceHealthCheck)

        # Build query based on filters
        filters = []
        if group:
            filters.append(ServiceHealthCheck.service_group.contains(group))
        if service:
            filters.append(ServiceHealthCheck.service_name.contains(service))
        if older_than:
            cutoff = datetime.utcnow() - timedelta(days=older_than)
            filters.append(ServiceHealthCheck.timestamp < cutoff)

        if not filters:
            click.echo("Error: Please specify at least one filter (--group, --service, or --older-than)", err=True)
            return

        # Apply all filters
        query = query.filter(*filters)

        # Count entries that would be deleted
        count = query.count()
        if count == 0:
            click.echo("No matching entries found")
            return

        # Show what would be deleted
        click.echo(f"\nFound {count} entries to delete:")
        
        # Sample of entries to be deleted
        sample = query.limit(5).all()
        for entry in sample:
            click.echo(f"- {entry.service_group}/{entry.service_name} ({entry.timestamp})")
        
        if count > 5:
            click.echo(f"... and {count - 5} more entries")

        # Confirm and delete if not dry run
        if not dry_run:
            if click.confirm('\nDo you want to delete these entries?'):
                deleted = query.delete()
                db.commit()
                click.echo(f"\nDeleted {deleted} entries")
            else:
                click.echo("\nOperation cancelled")
        else:
            click.echo("\nDry run - no entries were deleted")

    except Exception as e:
        click.echo(f"Error cleaning up database: {str(e)}", err=True)

@db.command()
def stats():
    """Show database statistics"""
    try:
        db = next(get_db())
        
        # Get total entries
        total_entries = db.query(ServiceHealthCheck).count()
        
        # Get entries by group
        group_stats = db.query(
            ServiceHealthCheck.service_group,
            func.count(ServiceHealthCheck.id).label('count')
        ).group_by(ServiceHealthCheck.service_group).all()
        
        # Get date range
        oldest = db.query(func.min(ServiceHealthCheck.timestamp)).scalar()
        newest = db.query(func.max(ServiceHealthCheck.timestamp)).scalar()
        
        # Display statistics
        click.echo("\nDatabase Statistics")
        click.echo("-" * 50)
        click.echo(f"Total entries: {total_entries}")
        click.echo(f"Date range: {oldest} to {newest}")
        
        click.echo("\nEntries by group:")
        for group, count in group_stats:
            click.echo(f"- {group}: {count}")
            
        # Calculate database size
        db_path = settings.PRIMARY_DATABASE_URL.replace('sqlite:///', '')
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            click.echo(f"\nDatabase size: {size / 1024 / 1024:.2f} MB")
            
    except Exception as e:
        click.echo(f"Error getting database stats: {str(e)}", err=True)

@cli.command()
@click.option('--username', default='admin', help='Admin username (default: admin)')
def setupadmin(username):
    """Create default admin user with random password and API token"""
    try:
        from app.database import User
        db = next(get_db())
        
        # Generate a secure random password
        password_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(password_chars) for _ in range(16))
        
        # Check if user exists
        user = db.query(User).filter(User.username == username).first()
        if user:
            click.echo(f"User {username} already exists!", err=True)
            if click.confirm('Do you want to reset the password and generate a new token?'):
                user.set_password(password)
                token = user.generate_token()
            else:
                return
        else:
            # Create new user
            user = User(username=username)
            user.set_password(password)
            db.add(user)
            token = user.generate_token()
        
        db.commit()
        
        # Prepare credentials data
        credentials = {
            "username": username,
            "password": password,
            "api_token": token,
            "created_at": datetime.utcnow().isoformat(),
            "auth_enabled": settings.AUTH_ENABLED
        }
        
        # Save credentials to JSON file in data folder
        credentials_file = settings.DATA_FOLDER / 'admin_credentials.json'
        with open(credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        click.echo(f"\nDefault admin user setup complete:")
        click.echo(f"Username: {username}")
        click.echo(f"Password: {password}")
        click.echo(f"API Token: {token}")
        click.echo(f"Credentials saved to: {credentials_file.absolute()}")
        
        # Show warning if authentication is disabled
        if not settings.AUTH_ENABLED:
            click.echo("\nWarning: Authentication is currently disabled!")
            click.echo("Run 'python manage.py auth enable' to enable authentication")
            
        # Show example curl command
        click.echo("\nExample API call:")
        click.echo(f"curl -H 'Authorization: Bearer {token}' http://localhost:8000/api/status")
            
    except Exception as e:
        click.echo(f"Error setting up admin user: {str(e)}", err=True)

if __name__ == '__main__':
    cli() 