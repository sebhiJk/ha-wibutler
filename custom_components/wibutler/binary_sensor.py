"""Binary sensor platform for Wibutler integration."""

import logging
import time
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN
from .const import EVENT_WIBUTLER_BUTTON
from .entity import WibutlerEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0
LONG_PRESS_THRESHOLD = 0.4

BUTTON_MAPPING = {
    "SWT": ["BTN_0", "BTN_1"],
    "SWT_A": ["BTN_A0", "BTN_A1"],
    "SWT_B": ["BTN_B0", "BTN_B1"],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wibutler binary sensors from a config entry."""
    hub = hass.data[DOMAIN]["hub"]
    devices = hub.devices

    binary_sensors = []
    for device_id, device in devices.items():
        for component in device.get("components", []):
            name = component.get("name", "")
            if name.startswith("BTN"):
                binary_sensors.append(WibutlerBinarySensor(hub, device, component))

    async_add_entities(binary_sensors, True)


class WibutlerBinarySensor(WibutlerEntity, BinarySensorEntity):
    """Representation of a Wibutler button as binary sensor."""

    def __init__(self, hub, device, component) -> None:
        """Initialize the binary sensor."""
        super().__init__(hub, device)
        self._component = component
        self._original_name = component.get("name", "")
        self._component_names = BUTTON_MAPPING.get(
            self._original_name, [self._original_name]
        )
        self._attr_name = f"{device['name']} - {component.get('text', self._original_name)}"
        self._attr_unique_id = f"{device['id']}_{self._original_name}"
        self._attr_is_on = False
        self._press_time: float | None = None
        self._long_press_timer = None
        self._long_press_fired = False

    @property
    def is_on(self) -> bool:
        """Return true if the button is pressed."""
        return self._attr_is_on

    def _build_event_data(self, action: str) -> dict:
        """Build event data for a button action."""
        return {
            "device_id": self._device_id,
            "device_name": self._device.get("name", ""),
            "button": self._original_name,
            "action": action,
        }

    @callback
    def _fire_event(self, action: str) -> None:
        """Fire a wibutler_button event (must be called from event loop)."""
        self._hub.hass.bus.async_fire(
            EVENT_WIBUTLER_BUTTON, self._build_event_data(action)
        )

    @callback
    def _on_long_press_timer(self, _now) -> None:
        """Handle long press timer expiry."""
        self._long_press_fired = True
        self._long_press_timer = None
        self._fire_event("long_press_start")

    @callback
    def _handle_press(self) -> None:
        """Handle button press in event loop."""
        self._press_time = time.monotonic()
        self._long_press_fired = False
        self._fire_event("press")
        if self._long_press_timer is not None:
            self._long_press_timer()
        self._long_press_timer = async_call_later(
            self._hub.hass,
            LONG_PRESS_THRESHOLD,
            self._on_long_press_timer,
        )

    @callback
    def _handle_release(self) -> None:
        """Handle button release in event loop."""
        if self._long_press_timer is not None:
            self._long_press_timer()
            self._long_press_timer = None
        if self._long_press_fired:
            self._fire_event("long_press_release")
        else:
            self._fire_event("short_press")
        self._fire_event("release")
        self._press_time = None

    async def async_will_remove_from_hass(self) -> None:
        """Clean up timer on removal."""
        if self._long_press_timer is not None:
            self._long_press_timer()
            self._long_press_timer = None

    def _fetch_state(self, components) -> None:
        """Update state from device data."""
        for component in components:
            comp_name = component.get("name", "")
            if comp_name not in BUTTON_MAPPING:
                continue

            expected_buttons = BUTTON_MAPPING[comp_name]
            if self._original_name not in expected_buttons:
                continue

            new_value = component.get("value", "")
            if len(new_value) < 2:
                continue

            button_index = new_value[0]
            button_state = new_value[-1]

            if comp_name == "SWT":
                expected_btn = f"BTN_{button_index}"
            else:
                expected_btn = (
                    f"BTN_A{button_index}"
                    if f"BTN_A{button_index}" in expected_buttons
                    else f"BTN_B{button_index}"
                )

            if expected_btn != self._original_name:
                continue

            was_on = self._attr_is_on
            self._attr_is_on = button_state == "D"

            if button_state == "D" and not was_on:
                self._hub.hass.loop.call_soon_threadsafe(self._handle_press)
            elif button_state == "U" and was_on:
                self._hub.hass.loop.call_soon_threadsafe(self._handle_release)
