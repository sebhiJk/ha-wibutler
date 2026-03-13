import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.util.unit_system import UnitOfTemperature
from homeassistant.util import dt as dt_util
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Wibutler sensors from a config entry."""
    hub = hass.data[DOMAIN]["hub"]
    devices = hub.devices

    sensors = []
    for device_id, device in devices.items():
        
        # 1. Global: Suche bei JEDEM Gerät nach Letztes Telegramm (LTEL) und VOC
        for component in device.get("components", []):
            if component.get("name") == "LTEL":
                sensors.append(WibutlerLTELSensor(hub, device, component))
            
            if device.get("type") == "VOCsensors" and component.get("name") == "VOC":
                sensors.append(WibutlerVOCSensor(hub, device, component))

        # 2. Spezifisch: Sensoren der Fußbodenheizung (FloorHeatingController)
        if device.get("type") == "FloorHeatingController":
            outputs = {output["name"] for output in device.get("outputs", [])}

            for component in device.get("components", []):
                if component.get("readonly") == True and component.get("name") in outputs:
                    sensors.append(WibutlerSensor(hub, device, component))

    async_add_entities(sensors, True)


class WibutlerSensor(SensorEntity):
    def __init__(self, hub, device, component):
        """Initialize the sensor."""
        self._hub = hub
        self._device = device
        self._component = component
        self._device_id = device['id']
        self._component_name = component['name']
        self._state = component['value']
        self._attr_name = f"{device['name']} - {component['text']}"
        self._attr_unique_id = f"{device['id']}_{component['name']}"
        self._attr_native_value = component.get("value")

        # Einheit bestimmen
        if "temperature" in component.get("text", "").lower():
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_native_value = int(self._attr_native_value) / 100
        elif "switch-on time" in component.get("text", "").lower():
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_native_value = int(self._attr_native_value)
        elif "humidity" in component.get("text", "").lower():
            self._attr_native_unit_of_measurement = PERCENTAGE
        else:
            self._attr_native_unit_of_measurement = None

    def _fetch_state(self, components):
        for component in components:
            if component.get("name") == self._component_name:
                self._state = component.get("value")
                self._attr_native_value = component.get("value")

    async def async_added_to_hass(self):
        self._hub.register_listener(self)

    def handle_ws_update(self, device_id, components):
        self._fetch_state(components)
        self.async_write_ha_state()


class WibutlerVOCSensor(WibutlerSensor):
    """Spezieller Sensor für die VOC Werte."""
    def __init__(self, hub, device, component):
        super().__init__(hub, device, component)
        self._attr_name = f"{device['name']} - Luftgüte (VOC)"
        self._attr_device_class = SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS
        self._attr_native_unit_of_measurement = "ppb" # Standard für Wibutler VOC
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_value = int(component.get("value")) / 100
        self._attr_icon = "mdi:air-filter"

    def _fetch_state(self, components):
        for component in components:
            if component.get("name") == self._component_name:
                self._attr_native_value = int(component.get("value")) / 100


class WibutlerLTELSensor(WibutlerSensor):
    """Spezieller Sensor für das letzte Telegramm zur Verbindungsüberwachung."""
    def __init__(self, hub, device, component):
        super().__init__(hub, device, component)
        self._attr_name = f"{device['name']} - Letztes Telegramm"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-out"
        self._parse_time(component.get("value"))

    def _parse_time(self, time_str):
        try:
            # Erwarte Format: 2026-03-12 23:46:15
            parsed_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            # HA erwartet Timezone-Aware Datetimes für TIMESTAMP Sensoren
            self._attr_native_value = parsed_dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        except (ValueError, TypeError):
            self._attr_native_value = None

    def _fetch_state(self, components):
        for component in components:
            if component.get("name") == "LTEL":
                self._parse_time(component.get("value"))