"""Constants for the Wibutler integration."""

from homeassistant.const import Platform

DOMAIN = "wibutler"
EVENT_WIBUTLER_BUTTON = "wibutler_button"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
CONF_USE_SSL = "use_ssl"

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]
