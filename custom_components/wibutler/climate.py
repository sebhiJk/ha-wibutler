"""Climate platform for Wibutler integration."""

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WibutlerConfigEntry
from .entity import WibutlerEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WibutlerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wibutler climate devices from a config entry."""
    hub = entry.runtime_data
    devices = hub.devices

    climate_entities = []
    for device_id, device in devices.items():
        # VOCsensors hinzugefügt
        if device.get("type") in ["RoomOperatingPanels", "VOCsensors"]:
            climate_entities.append(WibutlerClimate(hub, device))

    async_add_entities(climate_entities, True)


class WibutlerClimate(WibutlerEntity, ClimateEntity):
    """Representation of a Wibutler Climate Device."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hub, device) -> None:
        """Initialize the climate device."""
        super().__init__(hub, device)
        self._attr_name = device["name"]
        self._attr_unique_id = device["id"]
        self._current_temperature = None
        self._target_temperature = None
        self._current_humidity = None  # Neu: Luftfeuchtigkeit
        self._fetch_state(device.get("components", []))

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the target temperature."""
        return self._target_temperature

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._current_humidity

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return HVACMode.HEAT

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the target temperature."""
        if "temperature" not in kwargs:
            return

        # Einheitliche Skalierung für alle Wibutler-Climate-Geräte
        new_temp = int((kwargs["temperature"] - 10) * 2)
            
        data = {"type": "numeric", "value": str(new_temp)}
        url = f"devices/{self._device_id}/components/TSP"
        response = await self._hub._request("PATCH", url, data)

        if response:
            self._target_temperature = kwargs["temperature"]
            self.async_write_ha_state()

    def _fetch_state(self, components) -> None:
        """Update state from device data."""
        for component in components:
            name = component.get("name")
            val = component.get("value")
            
            # RTMP und TMP abfangen
            if name in ("TMP", "RTMP"):
                try:
                    self._current_temperature = int(val) / 100
                except (TypeError, ValueError):
                    pass
            elif name == "TSP":
                try:
                    # Einheitliche Umrechnung für alle (auch VOCsensors)
                    self._target_temperature = (int(val) / 2) + 10
                except (TypeError, ValueError):
                    pass
            elif name == "HUM":
                try:
                    self._current_humidity = int(val) / 100
                except (TypeError, ValueError):
                    pass
                    
