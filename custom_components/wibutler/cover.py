"""Cover platform for Wibutler integration."""

import logging

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
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
    """Set up Wibutler cover devices from a config entry."""
    hub = hass.data[DOMAIN]["hub"]
    devices = hub.devices

    covers = []
    for device_id, device in devices.items():
        if device.get("type") == "Blind":
            covers.append(WibutlerCover(hub, device))

    async_add_entities(covers, True)


class WibutlerCover(WibutlerEntity, CoverEntity):
    """Representation of a Wibutler Cover Device."""

    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, hub, device) -> None:
        """Initialize the cover device."""
        super().__init__(hub, device)
        self._state = None
        self._attr_name = device["name"]
        self._attr_unique_id = device["id"]
        self._position = None
        self._fetch_state(device.get("components", []))

    def _fetch_state(self, components) -> None:
        """Update state from device data, preferring CURPOS over POS."""
        curpos_found = False
        for component in components:
            name = component.get("name")
            if name == "CURPOS":
                try:
                    self._position = int(component.get("value"))
                    curpos_found = True
                except (ValueError, TypeError):
                    pass
            elif name == "POS" and not curpos_found:
                try:
                    self._position = int(component.get("value"))
                except (ValueError, TypeError):
                    pass
            elif name == "STATE":
                self._state = component.get("value")

    @property
    def current_cover_position(self):
        """Return the position of the cover (inverted for Home Assistant)."""
        if self._position is None:
            return None
        return 100 - self._position

    @property
    def is_opening(self) -> bool | None:
        """Return true if cover is opening."""
        return self._state == "Opening"

    @property
    def is_closing(self) -> bool | None:
        """Return true if cover is closing."""
        return self._state == "Closing"

    @property
    def is_closed(self) -> bool | None:
        """Return true if cover is fully closed."""
        return self._position == 100

    async def async_set_cover_position(self, **kwargs) -> None:
        """Set the cover position (inverted for Wibutler)."""
        if "position" not in kwargs:
            return

        new_position = 100 - int(kwargs["position"])
        data = {"value": str(new_position), "type": "numeric"}
        url = f"devices/{self._device_id}/components/POS"
        response = await self._hub._request("PATCH", url, data)

        if response:
            self._position = new_position
            self.async_write_ha_state()

    async def async_open_cover(self, **kwargs) -> None:
        """Open the cover fully."""
        data = {"value": "ON", "type": "switch"}
        url = f"devices/{self._device_id}/components/SWT_POS"
        response = await self._hub._request("PATCH", url, data)

        if response:
            self.async_write_ha_state()

    async def async_close_cover(self, **kwargs) -> None:
        """Close the cover fully."""
        data = {"value": "OFF", "type": "switch"}
        url = f"devices/{self._device_id}/components/SWT_POS"
        response = await self._hub._request("PATCH", url, data)

        if response:
            self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs) -> None:
        """Stop the cover based on current movement state."""
        if self._state == "Opening":
            data = {"value": "ON", "type": "switch"}
            url = f"devices/{self._device_id}/components/SWT_POS"
            await self._hub._request("PATCH", url, data)
        elif self._state == "Closing":
            data = {"value": "OFF", "type": "switch"}
            url = f"devices/{self._device_id}/components/SWT_POS"
            await self._hub._request("PATCH", url, data)
        elif self._position is not None:
            data = {"value": str(self._position), "type": "numeric"}
            url = f"devices/{self._device_id}/components/POS"
            await self._hub._request("PATCH", url, data)
        else:
            _LOGGER.warning("Cannot stop cover: no movement state or position known")
            return
        self.async_write_ha_state()
