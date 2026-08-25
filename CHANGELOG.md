# Changelog

All notable changes to this project will be documented in this file. The format
is based on Keep a Changelog, and the project uses Semantic Versioning.

## [Unreleased]

## [0.2.0] - 2026-08-25

### Added

- Added a separate test-upload control that validates current mapped data and
  credentials without changing normal upload status or counters.
- Added native Station ID and Station Key reconfiguration while preserving
  entity mappings and operational options.
- Added classified mapped-entity problem tracking and actionable Home Assistant
  Repairs issues for persistent failures.
- Added a configurable per-station maximum source age with a backward-compatible
  60-minute default.

### Changed

- Grouped each station's controls and operational sensors under one stable Home
  Assistant device, including migration of released registry identities.
- Allowed both sensor entities and numeric helpers in mapping and repair
  selectors without vendor or device-class restrictions.
- Improved license badge rendering across GitHub and HACS.

## [0.1.2] - 2026-08-23

### Changed

- Enabled complete HACS validation of integration-local brand assets without
  ignored checks.
- Prepared the repository for submission to the default HACS integration
  catalog.

## [0.1.1] - 2026-08-23

### Fixed

- Fixed the initial configuration form failing to open in the Home Assistant
  frontend.

### Changed

- Improved release pages with curated summaries and categorized generated
  changelogs.
- Added structured contribution templates and concise contributor guidance.
- Improved mapping onboarding, kept unmapped stations idle, and started mapped
  stations immediately.

## [0.1.0] - 2026-08-22

### Added

- Initial Home Assistant 2026.7+ custom integration and UI setup flow.
- Multiple independent virtual Weather Underground station entries.
- Entity mapping, validation, unit normalization, and calculated dew point.
- Scheduled and manual uploads with operational status entities.
- Credential reauthentication and secret-safe diagnostics.
- English and Czech translations.
- Automated tests, CI, hassfest, HACS validation, and release automation.

[Unreleased]: https://github.com/pokornyIt/home-assistant-weather-underground-uploader/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/pokornyIt/home-assistant-weather-underground-uploader/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/pokornyIt/home-assistant-weather-underground-uploader/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/pokornyIt/home-assistant-weather-underground-uploader/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/pokornyIt/home-assistant-weather-underground-uploader/releases/tag/v0.1.0
