"""Binary sensor platform for Wibutler integration."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WibutlerConfigEntry
from .entity import WibutlerEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

BUTTON_MAPPING = {
    "SWT": ["BTN_0", "BTN_1"],
    "SWT_A": ["BTN_A0", "BTN_A1"],
    "SWT_B": ["BTN_B0", "BTN_B1"],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WibutlerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wibutler binary sensors from a config entry."""
    hub = entry.runtime_data
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

    @property
    def is_on(self) -> bool:
        """Return true if the button is pressed."""
        return self._attr_is_on

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

            if expected_btn == self._original_name:
                self._attr_is_on = button_state == "D"
