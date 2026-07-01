"""Switch platform for Wibutler integration."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up Wibutler switches from a config entry."""
    hub = hass.data[DOMAIN]["hub"]
    devices = hub.devices

    switches = []
    for device_id, device in devices.items():
        if device.get("type") == "SwitchingRelays":
            switches.append(WibutlerSwitch(hub, device))

    async_add_entities(switches, True)


class WibutlerSwitch(WibutlerEntity, SwitchEntity):
    """Representation of a Wibutler switch."""

    def __init__(self, hub, device) -> None:
        """Initialize the switch."""
        super().__init__(hub, device)
        self._attr_name = device["name"]
        self._attr_unique_id = f"{device['id']}_{device['name']}"
        self._state = None
        self._fetch_state(device.get("components", []))

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self._state

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        data = {"value": "ON", "type": "switch"}
        url = f"devices/{self._device_id}/components/SWT"
        response = await self._hub._request("PATCH", url, data)

        if response:
            self._state = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        data = {"value": "OFF", "type": "switch"}
        url = f"devices/{self._device_id}/components/SWT"
        response = await self._hub._request("PATCH", url, data)

        if response:
            self._state = False
            self.async_write_ha_state()

    def _fetch_state(self, components) -> None:
        """Update state from device data."""
        for component in components:
            name = component.get("name")
            if name == "STATE":
                self._state = component.get("value") == "1"
            elif name == "SWT":
                value = component.get("value")
                if value in ("ON", "1"):
                    self._state = True
                elif value in ("OFF", "0"):
                    self._state = False
