"""Constants for Weather Underground Uploader."""

from typing import Final

DOMAIN: Final = "weather_underground_uploader"

CONF_STATION_ID: Final = "station_id"
CONF_STATION_KEY: Final = "station_key"

CONF_TEMPERATURE: Final = "temperature_entity"
CONF_HUMIDITY: Final = "humidity_entity"
CONF_PRESSURE: Final = "pressure_entity"
CONF_DEW_POINT: Final = "dew_point_entity"
CONF_WIND_DIRECTION: Final = "wind_direction_entity"
CONF_WIND_SPEED: Final = "wind_speed_entity"
CONF_WIND_GUST: Final = "wind_gust_entity"
CONF_HOURLY_RAIN: Final = "hourly_rain_entity"
CONF_DAILY_RAIN: Final = "daily_rain_entity"
CONF_UV_INDEX: Final = "uv_index_entity"
CONF_SOLAR_RADIATION: Final = "solar_radiation_entity"
CONF_UPLOAD_INTERVAL: Final = "upload_interval"

DEFAULT_UPLOAD_INTERVAL_SECONDS: Final = 300
MIN_UPLOAD_INTERVAL_SECONDS: Final = 60
MAX_UPLOAD_INTERVAL_SECONDS: Final = 3600
