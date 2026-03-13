"""Sensor platform for Wibutler integration."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import WibutlerConfigEntry
from .entity import WibutlerEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WibutlerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wibutler sensors from a config entry."""
    hub = entry.runtime_data
    devices = hub.devices

    sensors = []
    for device_id, device in devices.items():
        if device.get("type") not in ["FloorHeatingController"]:
            continue

        outputs = {output["name"] for output in device.get("outputs", [])}

        for component in device.get("components", []):
            if component.get("readonly") is True and component.get("name") in outputs:
                sensors.append(WibutlerSensor(hub, device, component))

    async_add_entities(sensors, True)


class WibutlerSensor(WibutlerEntity, SensorEntity):
    """Representation of a Wibutler sensor."""

    def __init__(self, hub, device, component) -> None:
        """Initialize the sensor."""
        super().__init__(hub, device)
        self._component = component
        self._component_name = component["name"]
        self._attr_name = f"{device['name']} - {component['text']}"
        self._attr_unique_id = f"{device['id']}_{component['name']}"

        text_lower = component.get("text", "").lower()
        raw_value = component.get("value")

        if "temperature" in text_lower:
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            try:
                self._attr_native_value = int(raw_value) / 100
            except (TypeError, ValueError):
                self._attr_native_value = None
        elif "switch-on time" in text_lower:
            self._attr_native_unit_of_measurement = PERCENTAGE
            try:
                self._attr_native_value = int(raw_value)
            except (TypeError, ValueError):
                self._attr_native_value = None
        elif "humidity" in text_lower:
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_native_value = raw_value
        else:
            self._attr_native_unit_of_measurement = None
            self._attr_native_value = raw_value

    def _fetch_state(self, components) -> None:
        """Update state from device data."""
        for component in components:
            if component.get("name") == self._component_name:
                raw_value = component.get("value")
                text_lower = self._component.get("text", "").lower()

                if "temperature" in text_lower:
                    try:
                        self._attr_native_value = int(raw_value) / 100
                    except (TypeError, ValueError):
                        self._attr_native_value = None
                elif "switch-on time" in text_lower:
                    try:
                        self._attr_native_value = int(raw_value)
                    except (TypeError, ValueError):
                        self._attr_native_value = None
                else:
                    self._attr_native_value = raw_value
