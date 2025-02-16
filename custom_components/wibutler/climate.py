import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.const import UnitOfTemperature
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Wibutler climate devices from a config entry."""
    hub = hass.data[DOMAIN]["hub"]
    devices = hub.devices

    climate_entities = []
    for device_id, device in devices.items():
        if device.get("type") in ["RoomOperatingPanels"]:
            climate_entities.append(WibutlerClimate(hub, device))

    async_add_entities(climate_entities, True)

class WibutlerClimate(ClimateEntity):
    """Representation of a Wibutler Climate Device."""

    def __init__(self, hub, device):
        """Initialize the climate device."""
        self._hub = hub
        self._device = device
        self._device_id = device['id']
        self._attr_name = device['name']
        self._attr_unique_id = device['id']
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        self._current_temperature = None
        self._target_temperature = None
        self._fetch_state(device.get("components", []))

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return HVACMode.HEAT

    @property
    def icon(self):
        """Setzt ein passenderes Icon für das Gerät."""
        return "mdi:radiator"  # Beispiel für Fußbodenheizung oder Heizkörper

    async def async_set_temperature(self, **kwargs):
        """Setzt die Zieltemperatur über die API mit korrekter Umrechnung."""
        if "temperature" not in kwargs:
            return

        # Berechne den API-Wert
        new_temp = int((kwargs["temperature"] - 10) * 2)

        data = {
            "type": "numeric",
            "value": str(new_temp)
        }

        _LOGGER.debug(f"📡 PATCH-Request an API: URL=devices/{self._device_id}/components/TSP, Data={data}")

        url = f"devices/{self._device_id}/components/TSP"
        response = await self._hub._request("PATCH", url, data)

        if response:
            _LOGGER.info("🌡️ Temperatur für %s auf %s°C gesetzt (Gesendet: %s)", self._attr_name, kwargs["temperature"], new_temp)
            self._target_temperature = kwargs["temperature"]
            self.async_write_ha_state()
        else:
            _LOGGER.error("❌ Fehler beim Setzen der Temperatur für %s", self._attr_name)

    def _fetch_state(self, components):
        """Holt den neuen Zustand aus WebSocket-Daten und setzt den Status korrekt."""
        for component in components:
            if component.get("name") == "TMP":
                self._current_temperature = int(component.get("value")) / 100  # TMP / 100
            elif component.get("name") == "TSP":
                self._target_temperature = (int(component.get("value")) / 2) + 10  # Umrechnung rückgängig

    async def async_added_to_hass(self):
        """Register for WebSocket updates."""
        self._hub.register_listener(self)

    def handle_ws_update(self, device_id, components):
        """Process WebSocket update."""
        self._fetch_state(components)
        self.async_write_ha_state()