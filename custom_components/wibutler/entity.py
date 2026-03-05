"""Base entity for Wibutler integration."""

import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class WibutlerEntity(Entity):
    """Base class for all Wibutler entities."""

    def __init__(self, hub, device) -> None:
        """Initialize the Wibutler entity."""
        self._hub = hub
        self._device = device
        self._device_id = device["id"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["id"])},
            name=device["name"],
            manufacturer=device.get("manufacturer", "Wibutler"),
            model=device.get("productName", device.get("type")),
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._hub.available

    async def async_added_to_hass(self) -> None:
        """Register for WebSocket updates and schedule cleanup."""
        self._hub.register_listener(self)
        self.async_on_remove(lambda: self._hub.remove_listener(self))

    def handle_ws_update(self, device_id, components) -> None:
        """Process WebSocket update."""
        self._fetch_state(components)
        self.async_write_ha_state()

    def _fetch_state(self, components) -> None:
        """Update state from device components. Override in subclasses."""
        raise NotImplementedError
