# Changelog

All notable changes to this project will be documented in this file.

## [2.0.1] - 2025-11-09
### Added
- Added a proactive WebSocket reconnection strategy to avoid the server's 3-minute connection timeout. The client now reconnects after ~170 seconds to ensure continuity.
- Support for identifying devices by either `device_serial_number` or `product_serial_number` during initialization; allows setup flows where only one identifier is available.
- `product_serial_number` documented in README and examples.

### Fixed
- Improved availability check for water shutoff valve reporting.
- Various bug fixes around water shutoff valve state parsing and control behavior.
- Token refresh related bug fixes.

### Changed
- Bumped package version to 2.0.1.

## [2.0.0] - 2025-11-06
### Added
- Initial WebSocket support for real-time device updates.
- Water shutoff valve control methods (open/close) and regeneration commands (schedule/cancel/run now).
- Device discovery and enriched-data fallbacks.

### Notes
- See commit history for fine-grained changes. The recent commits through 2025-11-09 include several small bug fixes, documentation updates, and improvements to WebSocket stability.

---

(This changelog was generated from the git commit history.)
