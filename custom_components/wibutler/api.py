import aiohttp
import asyncio
import json
import logging
from typing import Any, Dict, Optional, List, Callable
from urllib.parse import urlparse

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class WibutlerHub:
    """Verwaltet die Kommunikation mit der Wibutler API, inklusive WebSockets."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, username: str, password: str, verify_ssl: bool = False, use_ssl: bool = False):
        """Initialisiere Wibutler API-Verbindung."""
        self.hass = hass
        self.host = host
        self.port = port
        self.verify_ssl = verify_ssl
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.session = aiohttp.ClientSession()
        self.token: Optional[str] = None
        self.ws_task: Optional[asyncio.Task] = None
        self.listeners: List[Callable[[str, Any], None]] = []

        if self.use_ssl:
            self.schema = "https"
        else:
            self.schema = "http"

        # check if host has a scheme, if so set the baseUrl to the host without the scheme
        if urlparse(self.host).scheme:
            self.baseUrl = urlparse(self.host).hostname
        else:
            self.baseUrl = self.host

        if self.verify_ssl is False:
            _LOGGER.debug("🔓 SSL-Überprüfung ist deaktiviert (verify_ssl=False).")
            connector = aiohttp.TCPConnector(ssl=False)  # Deaktiviere SSL-Überprüfung
        else:
            _LOGGER.debug("🔒 SSL-Überprüfung ist aktiviert (verify_ssl=True).")
            connector = aiohttp.TCPConnector(ssl=True)  # Aktiviere SSL-Überprüfung

    async def authenticate(self) -> bool:
        """Authentifiziert sich bei der Wibutler API und speichert das Token."""
        url = f"{self.schema}://{self.baseUrl}:{self.port}/api/login"
        payload = {"username": self.username, "password": self.password}
        _LOGGER.info("✅ Start authenticate")
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data.get("sessionToken")
                    if not self.token:
                        _LOGGER.error("❌ API-Antwort enthält kein Token")
                        return False
                    _LOGGER.info("✅ Erfolgreich authentifiziert! %s", self.token)
                    return True
                else:
                    _LOGGER.error("❌ Authentifizierung fehlgeschlagen: %s", await response.text())
        except aiohttp.ClientError as err:
            _LOGGER.error("❌ Verbindungsfehler mit Wibutler API: %s", err)
        return False

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Sendet eine Anfrage an die Wibutler API."""
        if not self.token:
            _LOGGER.warning("Kein Token vorhanden, erneute Authentifizierung erforderlich.")
            if not await self.authenticate():
                return None

        url = f"{self.schema}://{self.baseUrl}:{self.port}/api/{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}"}
        _LOGGER.info("✅ Start request")
        _LOGGER.info("✅ url:  %s", url)
        _LOGGER.info("✅ headers:  %s", headers)
        try:
            async with self.session.request(method, url, headers=headers, json=data) as response:
                if response.status in (200, 201):
                    return await response.json()
                elif response.status == 401:
                    _LOGGER.warning("Token abgelaufen, erneute Authentifizierung erforderlich.")
                    self.token = None
                    return await self._request(method, endpoint, data)
                else:
                    _LOGGER.error("Fehlerhafte API-Antwort (%s): %s", response.status, await response.text())
        except aiohttp.ClientError as err:
            _LOGGER.error("Fehler bei der API-Anfrage: %s", err)
        return None

    async def get_devices(self) -> Optional[Dict[str, Any]]:
        """Holt die Liste der Geräte von der Wibutler API und gibt ein Dictionary zurück."""
        _LOGGER.info("✅ Start get_devices")
        response = await self._request("GET", "devices")
        if isinstance(response, dict):
            return response.get("devices", {})
        _LOGGER.error("❌ Erwartete Dictionary-Antwort, aber erhalten: %s", type(response))
        return {}

    async def connect_websocket(self):
        """Verbindet sich mit dem WebSocket und empfängt Echtzeit-Updates."""
        if not self.token:
            _LOGGER.error("❌ Kein gültiges Token, kann WebSocket nicht starten.")
            return

        ws_protocol = "wss" if self.schema == "https" else "ws"
        ws_url = f"{ws_protocol}://{self.host}:{self.port}/api/stream/{self.token}"
        _LOGGER.info("🔌 Verbindung zu WebSocket: %s", ws_url)

        try:
            async with self.session.ws_connect(ws_url) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            if "data" in data and "components" in data["data"]:
                                device_id = data["data"]["id"]
                                self._handle_ws_message(device_id, data["data"]["components"])
                        except json.JSONDecodeError:
                            _LOGGER.error("❌ Fehler beim Parsen der WebSocket-Nachricht: %s", msg.data)
        except aiohttp.ClientError as err:
            _LOGGER.error("❌ WebSocket-Verbindungsfehler: %s", err)

    def _handle_ws_message(self, device_id: str, components: List[Dict[str, Any]]):
        """Verarbeitet WebSocket-Nachrichten und benachrichtigt nur relevante Entitäten."""
        for listener in self.listeners:
            if listener._device_id == device_id:  # Nur relevante Entitäten aufrufen
                listener.handle_ws_update(device_id, components)

    def register_listener(self, entity):
        """Registriert eine Entität für WebSocket-Updates."""
        self.listeners.append(entity)

    async def close(self):
        """Schließt die HTTP-Sitzung und beendet WebSocket-Verbindung."""
        if self.ws_task:
            self.ws_task.cancel()
        await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
