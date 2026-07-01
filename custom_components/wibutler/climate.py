"""Climate platform for Wibutler integration."""

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import WibutlerEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wibutler climate devices from a config entry."""
    # Hub klassisch laden - passend zu deiner __init__.py
    hub = hass.data[DOMAIN]["hub"]
    devices = hub.devices

    climate_entities = []
    for device_id, device in devices.items():
        if device.get("type") in ["RoomOperatingPanels"]:
            climate_entities.append(WibutlerClimate(hub, device))

    async_add_entities(climate_entities, True)


class WibutlerClimate(WibutlerEntity, ClimateEntity):
    """Representation of a Wibutler Climate Device."""

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hub, device) -> None:
        """Initialize the climate device."""
        super().__init__(hub, device)
        
        # Explizit setzen, damit API-Requests (PATCH) nicht abstürzen
        self._hub = hub
        self._device_id = device["id"]
        
        self._attr_name = device["name"]
        self._attr_unique_id = device["id"]
        
        self._current_temperature = None
        self._target_temperature = None
        self._hvac_mode = HVACMode.HEAT
        self._saved_target_temp = 22.0
        self._fetch_state(device.get("components", []))

    @property
    def supported_features(self):
        """Return the list of supported features."""
        if self._hvac_mode == HVACMode.COOL:
            return ClimateEntityFeature(0)
        return ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the target temperature."""
        if self._hvac_mode == HVACMode.COOL:
            return 22.5
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        return self._hvac_mode

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode not in self.hvac_modes:
            return

        if hvac_mode == HVACMode.COOL:
            new_temp = int((30 - 10) * 2)
            data = {"type": "numeric", "value": str(new_temp)}
            url = f"devices/{self._device_id}/components/TSP"
            response = await self._hub._request("PATCH", url, data)
            if response:
                self._hvac_mode = hvac_mode
                self.async_write_ha_state()

        elif hvac_mode == HVACMode.HEAT:
            target = self._saved_target_temp if self._saved_target_temp else 22.0
            new_temp = int((target - 10) * 2)
            data = {"type": "numeric", "value": str(new_temp)}
            url = f"devices/{self._device_id}/components/TSP"
            response = await self._hub._request("PATCH", url, data)
            if response:
                self._hvac_mode = hvac_mode
                self._target_temperature = target
                self.async_write_ha_state()

        elif hvac_mode == HVACMode.OFF:
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the target temperature."""
        if self._hvac_mode == HVACMode.COOL:
            return

        if "temperature" not in kwargs:
            return

        new_temp = int((kwargs["temperature"] - 10) * 2)
        data = {"type": "numeric", "value": str(new_temp)}
        url = f"devices/{self._device_id}/components/TSP"
        response = await self._hub._request("PATCH", url, data)

        if response:
            self._target_temperature = kwargs["temperature"]
            self._saved_target_temp = kwargs["temperature"]
            self.async_write_ha_state()

    def _fetch_state(self, components) -> None:
        """Update state from device data."""
        for component in components:
            name = component.get("name")
            if name == "TMP":
                try:
                    self._current_temperature = int(component.get("value")) / 100
                except (TypeError, ValueError):
                    self._current_temperature = None
            elif name == "TSP":
                try:
                    val = (int(component.get("value")) / 2) + 10
                    
                    if val >= 30.0:
                        self._hvac_mode = HVACMode.COOL
                    elif self._hvac_mode != HVACMode.OFF:
                        self._hvac_mode = HVACMode.HEAT
                        self._target_temperature = val
                        self._saved_target_temp = val
                    else:
                        self._target_temperature = val
                        self._saved_target_temp = val
                except (TypeError, ValueError):
                    self._target_temperature = None
