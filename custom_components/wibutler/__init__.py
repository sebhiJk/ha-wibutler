import asyncio
import logging
from typing import Any, Dict, Optional
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN, PLATFORMS  # Hier wird DOMAIN aus const.py importiert
from .api import WibutlerHub

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setze die Konfigurationsdatei ein (configuration.yaml)."""
    _LOGGER.debug("🔄 async_setup() in __init__.py wurde aufgerufen!")
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setze die Konfiguration über die UI ein."""
    _LOGGER.debug("🚀 async_setup_entry() wurde aufgerufen! Registriere Plattformen...")

    hub = WibutlerHub(
        hass,
        entry.data["host"],
        entry.data.get("port", 8081),
        entry.data["username"],
        entry.data["password"]
    )

    if not await hub.authenticate():
        _LOGGER.error("❌ Authentifizierung fehlgeschlagen!")
        return False

    hass.data[DOMAIN]["hub"] = hub

    _LOGGER.debug("📝 API Response (Authentifizierung): %s", hub.token)

    hub.devices = await hub.get_devices()

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    )
    _LOGGER.debug("✅ Plattformen erfolgreich registriert!")
    hass.loop.create_task(hub.connect_websocket())

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entferne eine Konfiguration."""
    _LOGGER.debug("🔄 async_unload_entry() wurde aufgerufen!")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok