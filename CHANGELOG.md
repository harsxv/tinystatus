# Changelog

All notable changes to StatusWatch will be documented in this file.

## 1.0.2
- Switch App name

## 1.0.1
- Move checks and incidents to a data folder

## [1.0.0] - 2024-02-19

### Added
- 🎨 New modern UI design with improved UX
  - Added navigation bar between pages
  - Improved dark mode support
  - Better mobile responsiveness
  - Enhanced visual hierarchy

- 📊 Enhanced History Page
  - Interactive time-series charts with ApexCharts
  - Configurable time ranges (1h, 6h, 12h, 24h, 3d, 7d)
  - Service-specific detailed views
  - Zoom and pan capabilities
  - Different line patterns for better service distinction
  - Tooltips with response times

- 🔍 Error Inspection Features
  - Detailed error modal view
  - Full error payload inspection
  - Response time tracking
  - Failure duration calculations
  - Service status history

- ⚡ Performance Improvements
  - Added response caching
  - Optimized database queries
  - Better error handling
  - Improved data loading

- 🔄 Auto-refresh Functionality
  - Configurable refresh intervals
  - Visual countdown timer
  - Manual refresh option
  - Persistent user preferences

### Changed
- Renamed project to StatusWatch
- Restructured project layout for better organization
- Improved database schema and handling
- Enhanced API responses with more details
- Better error handling and logging
- Updated documentation with new features
- Improved chart visualizations
- Better status display and grouping

### Fixed
- Chart rendering issues
- Database connection handling
- Time zone handling in charts
- Modal display issues
- Dark mode inconsistencies
- Mobile layout issues
- Error data parsing
- Response time accuracy

## [1.0.0] - Original Fork

### Features
- Basic status monitoring
- Service grouping
- Simple history tracking
- Basic UI
- HTTP, Ping, and Port checks
- SQLite database storage
- Basic API endpoints

### Technical Changes
- Migrated to FastAPI
- Added async support
- Implemented basic monitoring
- Added SQLite database
- Basic templating system
- Simple API endpoints 