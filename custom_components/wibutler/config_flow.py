"""Config flow für die Wibutler Integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL, CONF_USE_SSL

_LOGGER = logging.getLogger(__name__)

# Definition des Eingabeformulars für die Erstkonfiguration
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=8081): int,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_VERIFY_SSL, default=False): bool,
        vol.Required(CONF_USE_SSL, default=False): bool,
    }
)


class WibutlerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle die Konfigurations-UI für Wibutler."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Erster Schritt der Konfiguration."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        _LOGGER.debug(f"🎛️ Wibutler wird mit {user_input} konfiguriert")

        return self.async_create_entry(title="Wibutler", data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        """Optionen für die Konfiguration bereitstellen."""
        return WibutlerOptionsFlowHandler(entry)


class WibutlerOptionsFlowHandler(config_entries.OptionsFlow):
    """Optionen für die Wibutler Integration."""

    def __init__(self, entry):
        """Speichere die aktuelle Konfiguration."""
        self.entry = entry

    async def async_step_init(self, user_input=None):
        """Zeige die Optionen an und erlaube Änderungen."""
        if user_input is not None:
            _LOGGER.debug(f"🔄 Neue Wibutler-Konfiguration: {user_input}")

            # Erstelle den neuen Eintrag mit den aktualisierten Werten
            return self.async_create_entry(title="", data=user_input)

        # Aktuelle Werte abrufen
        current_options = self.entry.options if self.entry.options else self.entry.data

        # Formular mit aktuellen Werten als Standardwerte
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_options.get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=current_options.get(CONF_PORT, 8081)): int,
                vol.Required(CONF_PASSWORD, default=current_options.get(CONF_PASSWORD, "")): str,
                vol.Required(CONF_USERNAME, default=current_options.get(CONF_USERNAME, "")): str,
                vol.Required(CONF_VERIFY_SSL, default=current_options.get(CONF_VERIFY_SSL, False)): bool,
                vol.Required(CONF_USE_SSL, default=current_options.get(CONF_USE_SSL, False)): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
