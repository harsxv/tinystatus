# Changelog

All notable changes to StatusWatch will be documented in this file.

## [2.0.0] - 2024-02-19

### Added
- 🔒 Authentication System
  - Basic Auth for web interface
  - Token-based API authentication
  - Configurable authentication toggle
  - Token expiration support
  - User management system
  - CLI commands for auth management

- 🛠️ Management CLI
  - User management commands
  - Token management commands
  - Database cleanup utilities
  - Configuration validation
  - Interactive setup
  - Backup and restore functionality

- 📊 Enhanced Monitoring
  - Server IP integration in group names
  - Better group organization
  - Improved status tracking
  - Enhanced error handling
  - Better data consistency

- 🎨 UI Improvements
  - Modern design refresh
  - Dark mode support
  - Better mobile responsiveness
  - Interactive charts with ApexCharts
  - Dynamic data updates
  - Improved error displays

- 🔧 Database Features
  - Database cleanup commands
  - Entry management by group/service
  - Historical data pruning
  - Database statistics
  - Better data organization

### Changed
- Switched to FastAPI for better async support
- Improved database schema and handling
- Enhanced API responses with more details
- Better error handling and logging
- Updated documentation with new features
- Improved chart visualizations
- Better status display and grouping
- Changed group separator to '#' for better compatibility
- Improved token management system
- Enhanced security features

### Fixed
- Chart rendering issues
- Database connection handling
- Time zone handling in charts
- Modal display issues
- Dark mode inconsistencies
- Mobile layout issues
- Error data parsing
- Response time accuracy
- Group name handling
- Authentication edge cases

## [1.0.0] - Initial Release

### Features
- Basic status monitoring
- Service grouping
- Simple history tracking
- Basic UI
- HTTP, Ping, and Port checks
- SQLite database storage
- Basic API endpoints

### Technical
- FastAPI implementation
- Async support
- Basic monitoring
- SQLite database
- Simple templating
- Basic API endpoints