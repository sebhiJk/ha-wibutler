import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Wibutler binary sensors from a config entry."""
    hub = hass.data[DOMAIN]["hub"]
    devices = hub.devices

    binary_sensors = []
    for device_id, device in devices.items():
        for component in device.get("components", []):
            name = component["name"]

            # Nur `BTN_*`-Komponenten als Taster registrieren
            if name.startswith("BTN"):
                binary_sensors.append(WibutlerBinarySensor(hub, device, component))

    async_add_entities(binary_sensors, True)

BUTTON_MAPPING = {
    "SWT": ["BTN_0", "BTN_1"],  # Single Rocker Switch
    "SWT_A": ["BTN_A0", "BTN_A1"],  # Left side Rocker
    "SWT_B": ["BTN_B0", "BTN_B1"],  # Right side Rocker
}


class WibutlerBinarySensor(BinarySensorEntity):
    """Representation of a Wibutler button (which acts like a binary sensor)."""

    def __init__(self, hub, device, component):
        """Initialize the binary sensor."""
        self._hub = hub
        self._device = device
        self._component = component
        self._device_id = device["id"]
        self._original_name = component["name"]
        self._component_names = BUTTON_MAPPING.get(self._original_name, [self._original_name])
        self._attr_name = f"{device['name']} - {component['text']}"
        self._attr_unique_id = f"{device['id']}_{component['name']}"
        self._attr_is_on = False  # Standardmäßig aus

    def _fetch_state(self, components):
        """Holt den neuen Zustand aus WebSocket-Daten und setzt den Status korrekt."""
        _LOGGER.debug(f"🔄 {self._attr_name} wird aktualisiert... {self._component_names}")

        for component in components:
            if component["name"] in BUTTON_MAPPING:
                expected_buttons = BUTTON_MAPPING[component["name"]]

                if self._original_name in expected_buttons:
                    new_value = component["value"]

                    # Extrahiere den Nummernteil (0 oder 1)
                    button_index = new_value[0]  # Erstes Zeichen ist die Nummer (0 = oben, 1 = unten)
                    button_state = new_value[-1]  # Letztes Zeichen ist U oder D

                    # 🔹 **Sonderfall für einfache Schalter (`SWT`)**
                    if component["name"] == "SWT":
                        expected_btn = f"BTN_{button_index}"
                    else:
                        expected_btn = f"BTN_A{button_index}" if f"BTN_A{button_index}" in expected_buttons else f"BTN_B{button_index}"

                    # Überprüfen, ob die aktuelle Entität die richtige ist
                    if expected_btn == self._original_name:
                        self._attr_is_on = button_state == "D"  # ON wenn gedrückt (D), OFF wenn losgelassen (U)

                        self.async_write_ha_state()  # Home Assistant sofort aktualisieren

    @property
    def is_on(self) -> bool:
        """Return true if the button is pressed."""
        return self._attr_is_on

    async def async_added_to_hass(self):
        """Register for WebSocket updates."""
        self._hub.register_listener(self)

    def handle_ws_update(self, device_id, components):
        """Process WebSocket update."""
        self._fetch_state(components)
        self.async_write_ha_state()