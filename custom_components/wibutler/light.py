"""Light platform for Wibutler integration."""

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import WibutlerEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1
BRIGHTNESS_SCALE = 255 / 100
MIN_PERCENT = 10


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wibutler dimmable lights from a config entry."""
    hub = hass.data[DOMAIN]["hub"]
    devices = hub.devices

    lights = []
    for device_id, device in devices.items():
        if device.get("type") == "DimminActuators":
            lights.append(WibutlerLight(hub, device))

    async_add_entities(lights, True)


class WibutlerLight(WibutlerEntity, LightEntity):
    """Representation of a Wibutler dimmable light."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature(0)

    def __init__(self, hub, device) -> None:
        """Initialize the light."""
        super().__init__(hub, device)
        self._attr_name = device["name"]
        self._attr_unique_id = device["id"]
        self._is_on = False
        self._brightness_pct = 0
        self._last_brightness_pct = 100
        self._fetch_state(device.get("components", []))

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._is_on

    @property
    def brightness(self):
        """Return the brightness of the light."""
        if self._brightness_pct < MIN_PERCENT:
            return 0
        return int(self._brightness_pct * BRIGHTNESS_SCALE)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        
        # Prüfen, ob eine spezifische Helligkeit über den Slider gewählt wurde
        if ATTR_BRIGHTNESS in kwargs:
            brightness_ha = kwargs[ATTR_BRIGHTNESS]
            brightness_pct = max(
                0, min(100, int(brightness_ha / BRIGHTNESS_SCALE))
            )
        else:
            # Wenn nur der "Ein"-Schalter gedrückt wurde, nehmen wir den letzten bekannten Wert
            brightness_pct = self._last_brightness_pct
            if brightness_pct < MIN_PERCENT:
                brightness_pct = 100  # Fallback auf 100%, falls kein alter Wert vorlag

        if brightness_pct < MIN_PERCENT:
            await self.async_turn_off()
            return

        # Bei einem Dimmer schicken wir NUR noch den Helligkeitswert (BRI_LVL),
        # um das kurze Aufblinken (durch einen vorausgehenden SWT=ON Befehl) zu verhindern.
        data_bri = {"type": "numeric", "value": str(brightness_pct)}
        url_bri = f"devices/{self._device_id}/components/BRI_LVL"
        resp_bri = await self._hub._request("PATCH", url_bri, data_bri)

        if resp_bri:
            self._is_on = True
            self._brightness_pct = brightness_pct
            self._last_brightness_pct = brightness_pct
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        if self._brightness_pct >= MIN_PERCENT:
            self._last_brightness_pct = self._brightness_pct

        # Beim Ausschalten reicht weiterhin der klassische Schalter-Befehl aus
        data = {"value": "OFF", "type": "switch"}
        url = f"devices/{self._device_id}/components/SWT"

        response = await self._hub._request("PATCH", url, data)
        if response:
            self._is_on = False
            self._brightness_pct = 0
            self.async_write_ha_state()

    def _fetch_state(self, components) -> None:
        """Update state from device data."""
        for component in components:
            name = component.get("name")
            if name == "STATE":
                self._is_on = component.get("value") != "0"
            elif name == "BRI_LVL":
                try:
                    pct = int(component.get("value"))
                    if pct < MIN_PERCENT:
                        self._brightness_pct = 0
                        self._is_on = False
                    else:
                        self._brightness_pct = pct
                        self._last_brightness_pct = pct
                except (TypeError, ValueError):
                    self._brightness_pct = 0
                    self._is_on = False
            elif name == "SWT":
                value = component.get("value")
                if value in ("0", "OFF"):
                    self._is_on = False
                elif self._brightness_pct >= MIN_PERCENT:
                    self._is_on = True

