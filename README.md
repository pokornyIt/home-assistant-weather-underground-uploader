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
- optional entity mappings configured through the options flow;
- metric and imperial unit normalization for Weather Underground fields;
- validation and graceful omission of unavailable mapped values;
- explicit or calculated dew point support;
- independent scheduled uploads for every configured station;
- operational status sensors and a manual upload button;
- Station Key repair through Home Assistant reauthentication;
- secret-safe Home Assistant diagnostics;
- automated tests with enforced coverage, type, lint, and format checks;
- GitHub Actions validation with CI, hassfest, and HACS;
- English translations and focused config-flow tests.

Release packaging and end-user installation documentation are tracked in
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

## Entity mapping and normalization

Mappings are configured independently for each station through its Home
Assistant options flow. Sensor entities and numeric helpers are supported, so
template entities can adapt unusual sources without introducing a dependency on
a particular device or vendor.

The integration reads each mapped entity when an observation is built. Numeric
values are converted from their declared Home Assistant units to the Weather
Underground protocol units: Fahrenheit, inches of mercury, miles per hour, and
inches of rain. Humidity, wind direction, UV index, and solar radiation retain
their protocol-native units. Values that are missing, unknown, unavailable,
non-numeric, non-finite, physically invalid, use an unsupported unit, or have
not reported for more than one hour are omitted individually.

All mappings are optional. The minimum upload payload is one valid mapped
measurement; an empty observation is not sent. When no dew-point entity is
mapped, dew point is calculated from valid temperature and relative humidity
values. An explicitly mapped dew point always takes precedence.

## Upload operation

Each configured station has an independent asynchronous uploader. The default
upload interval is five minutes and can be changed in station options from 60 to
3,600 seconds. Saving options reloads only that config entry and applies the new
schedule without restarting Home Assistant.

Observations are rebuilt immediately before every upload. Uploads for the same
station are serialized, including requests made with the **Upload now** button,
so a slow request cannot overlap the next one. Temporary service or network
failures leave the integration loaded and retry on the next scheduled cycle.
Repeated failures produce only one warning until uploads recover. Rejected
credentials start Home Assistant's reauthentication flow for replacing the
Station Key.

The virtual station exposes sensors for upload status, the last attempt, the
last successful upload, and consecutive failures. These remain available when
an upload fails, allowing the problem to be seen without reading logs.

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
require live credentials. The test suite enforces at least 95% statement
coverage for the integration package.

## Security

Treat the Weather Underground Station Key as a secret. Do not include real keys
in bug reports, logs, diagnostics, screenshots, tests, or example files.
Downloaded Home Assistant diagnostics redact the Station Key and include only
selected configuration and operational state.

## License

This project is licensed under the [MIT License](LICENSE).
