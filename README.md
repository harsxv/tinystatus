<div align="center">
  <h1>StatusWatch</h1>
  <p>A modern, FastAPI-powered status page with unified monitoring capabilities</p>
</div>

## Features

- 🚀 Async monitoring with FastAPI
- 🔒 Authentication and API token support
- 📊 Unified monitoring system
- 🔍 Multiple check types (HTTP, Ping, Port)
- 📈 Time-series history tracking
- 🌐 RESTful API endpoints
- 📱 Responsive web interface
- 🔄 Real-time status updates
- 📊 Uptime calculations
- 🎯 Service grouping
- ⚡ Performance optimizations
- 🌓 Dark mode support

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/statuswatch.git
cd statuswatch
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your environment:
```env
MONITOR_CONTINUOUSLY=True
CHECK_INTERVAL=30
MAX_HISTORY_ENTRIES=100
LOG_LEVEL=INFO
PRIMARY_DATABASE_URL=sqlite:///status_history.db
AUTH_ENABLED=True
```

4. Initialize the database and create an admin user:
```bash
python manage.py initdb
python manage.py auth setup
```

## Authentication

StatusWatch supports two types of authentication:
- Basic Authentication for web interface
- Token Authentication for API access

### Managing Authentication

Enable/disable authentication:
```bash
# Show current auth status
python manage.py auth status

# Enable authentication
python manage.py auth enable

# Disable authentication
python manage.py auth disable

# Interactive setup
python manage.py auth setup
```

### User Management

Create and manage users:
```bash
# Create a new user
python manage.py createuser

# Create API token
python manage.py token create username --expires 30

# Revoke token
python manage.py token revoke username

# Show token info
python manage.py token info username

# List all users and tokens
python manage.py token list
```

### API Authentication

Use Bearer token authentication for API requests:
```bash
curl -H "Authorization: Bearer your-api-token" http://localhost:8000/api/status
```

### Web Authentication

Use Basic authentication for web interface:
```bash
curl -u username:password http://localhost:8000/
```

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/status` | GET | Token | Current status of all services |
| `/api/history` | GET | Token | Historical data for all services |
| `/api/history/{group_name}` | GET | Token | Historical data for a group |
| `/health` | GET | None | Service health check |

## Management Commands

### Database Management
```bash
# Initialize database
python manage.py initdb

# Reset database
python manage.py resetdb

# Backup data
python manage.py backup data.json

# Restore from backup
python manage.py restore data.json
```

### Token Management
```bash
# Create token with 30-day expiry
python manage.py token create username --expires 30

# Create permanent token
python manage.py token create username

# List all tokens
python manage.py token list

# Show token details
python manage.py token info username

# Revoke token
python manage.py token revoke username
```

### Configuration Management
```bash
# Validate configuration
python manage.py checkconfig

# Start interactive shell
python manage.py shell
```

## Service Configuration

Configure services in `checks.yaml`:
```yaml
- title: 'Infrastructure'
  checks:
    - name: Main Website
      type: http
      host: https://example.com
      expected_code: 200

    - name: Database
      type: port
      host: db.example.com
      port: 5432
```

## Docker Support

Run with Docker:
```bash
docker-compose up -d
```

Environment variables can be configured in `docker-compose.yml` or `.env` file.

## Development

### Project Structure
```
statuswatch/
├── app/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration
│   ├── database.py       # Database models
│   ├── auth.py          # Authentication
│   └── services/
│       ├── monitor.py    # Monitoring logic
│       └── checks.py     # Check implementations
├── manage.py            # CLI management
├── checks.yaml          # Service configuration
└── incidents.md         # Incident reports
```

### Running Tests
```bash
pytest tests/
```

## Browser Support
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## License
MIT License - see [LICENSE](LICENSE) for details
