# Home Assistant Weather Underground Uploader

Build a virtual Weather Underground Personal Weather Station from any
combination of Home Assistant entities.

## Overview

This repository contains a Home Assistant custom integration that will upload
weather observations to a Weather Underground Personal Weather Station (PWS).
It is designed around a virtual-station model: each Weather Underground field
may come from a different Home Assistant entity, device, or source integration.

For example, temperature may come from a Zigbee sensor, pressure from ESPHome,
wind from Ecowitt, and rainfall from a Home Assistant helper. The integration
does not depend on any specific weather-station hardware or vendor.

One Home Assistant config entry represents one Weather Underground station.
Multiple independent stations can be configured in the same Home Assistant
instance.

## Development status

The project is under active development and is not ready for production use.
The current implementation provides the initial integration foundation:

- a Home Assistant 2026.7+ custom integration structure;
- UI-only setup through a config flow;
- Station ID and Station Key configuration;
- duplicate Station ID protection;
- support for multiple station config entries;
- config-entry setup, reload, and unload lifecycle;
- an asynchronous, credential-safe Weather Underground upload client;
- an options-flow foundation for later settings;
- English translations and focused config-flow tests.

Automatic Weather Underground uploads are not implemented yet. Entity mapping,
unit normalization, scheduling, operational entities, diagnostics, and release
packaging are tracked as separate roadmap stages in
[GitHub issues](https://github.com/pokornyIt/home-assistant-weather-underground-uploader/issues).

## Planned measurements

The initial release is expected to support optional mappings for:

- outdoor temperature and relative humidity;
- barometric pressure and dew point;
- wind direction, speed, and gust;
- hourly and daily rainfall;
- UV index and solar radiation.

Unavailable optional measurements will not prevent otherwise valid values from
being uploaded. Qualitative sensors are not treated as quantitative
measurements; for example, a binary wet sensor cannot provide a rainfall amount
by itself.

## Repository layout

```text
custom_components/weather_underground_uploader/  Home Assistant integration
tests/                                           Automated tests
pyproject.toml                                   Tool and dependency configuration
uv.lock                                          Reproducible development environment
```

## Development

The project uses Python 3.14 and [uv](https://docs.astral.sh/uv/) for dependency
and environment management.

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pre-commit run --all-files
```

Tests use synthetic station data and do not contact Weather Underground or
require live credentials.

## Security

Treat the Weather Underground Station Key as a secret. Do not include real keys
in bug reports, logs, diagnostics, screenshots, tests, or example files.

## License

This project is licensed under the [MIT License](LICENSE).
