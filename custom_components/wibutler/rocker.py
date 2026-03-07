"""Rocker controller for Wibutler button-to-entity bindings."""

import asyncio
import logging

from homeassistant.core import Event, HomeAssistant

from .const import EVENT_WIBUTLER_BUTTON

_LOGGER = logging.getLogger(__name__)

DIM_INTERVAL = 0.2
DEFAULT_DIM_DURATION = 5.0


class RockerController:
    """Consumes wibutler_button events and controls bound entities."""

    def __init__(
        self, hass: HomeAssistant, bindings: list[dict], dim_duration: float = DEFAULT_DIM_DURATION
    ) -> None:
        """Initialize with a list of bindings."""
        self._hass = hass
        self._bindings = bindings
        self._dim_step = max(1, round(255 / (dim_duration / DIM_INTERVAL)))
        self._unsub = None
        self._active_tasks: dict[str, asyncio.Task] = {}

    def start(self) -> None:
        """Start listening for button events."""
        self._unsub = self._hass.bus.async_listen(
            EVENT_WIBUTLER_BUTTON, self._handle_event
        )

    def stop(self) -> None:
        """Stop listening and cancel running tasks."""
        if self._unsub:
            self._unsub()
            self._unsub = None
        for task in self._active_tasks.values():
            task.cancel()
        self._active_tasks.clear()

    async def _handle_event(self, event: Event) -> None:
        """Dispatch button event to the correct handler."""
        data = event.data
        device_id = data.get("device_id")
        button = data.get("button")
        action = data.get("action")
        _LOGGER.debug("Rocker event: %s %s %s", device_id, button, action)

        for binding in self._bindings:
            if binding["device_id"] != device_id or binding["button"] != button:
                continue

            entity_ids = binding.get(
                "target_entity_ids",
                [binding["target_entity_id"]] if "target_entity_id" in binding else [],
            )
            mode = binding["mode"]
            task_key = f"{device_id}_{button}"

            for entity_id in entity_ids:
                if mode in ("dim_up", "dim_down"):
                    await self._handle_dim(task_key, entity_id, mode, action)
                elif mode in ("cover_open", "cover_close"):
                    await self._handle_cover(task_key, entity_id, mode, action)
                elif mode == "toggle":
                    await self._handle_toggle(entity_id, action)
                elif mode == "turn_off":
                    await self._handle_service(entity_id, action, "turn_off")
                elif mode == "turn_on":
                    await self._handle_service(entity_id, action, "turn_on")

    async def _handle_dim(
        self, task_key: str, entity_id: str, mode: str, action: str
    ) -> None:
        """Handle dimming actions."""
        _LOGGER.debug("Dim: %s %s %s %s", task_key, entity_id, mode, action)
        if action == "short_press":
            await self._hass.services.async_call(
                "light", "toggle", {"entity_id": entity_id}
            )
        elif action == "long_press_start":
            step = self._dim_step if mode == "dim_up" else -self._dim_step
            _LOGGER.debug("Starting dim loop: %s step=%s", entity_id, step)
            task = self._hass.async_create_task(
                self._dim_loop(entity_id, step)
            )
            self._active_tasks[task_key] = task
        elif action in ("release", "long_press_release"):
            task = self._active_tasks.pop(task_key, None)
            _LOGGER.debug("Stopping dim: task=%s", task)
            if task:
                task.cancel()

    async def _dim_loop(self, entity_id: str, step: int) -> None:
        """Repeatedly step brightness until cancelled."""
        try:
            while True:
                state = self._hass.states.get(entity_id)
                if state is None:
                    _LOGGER.debug("Dim loop: entity %s not found", entity_id)
                    break
                current = state.attributes.get("brightness", 0) or 0
                target = max(0, min(255, current + step))
                _LOGGER.debug("Dim loop: %s current=%s target=%s step=%s", entity_id, current, target, step)
                if target <= 0:
                    await self._hass.services.async_call(
                        "light", "turn_off", {"entity_id": entity_id}
                    )
                    break
                await self._hass.services.async_call(
                    "light",
                    "turn_on",
                    {"entity_id": entity_id, "brightness": target},
                )
                if target >= 255:
                    break
                await asyncio.sleep(DIM_INTERVAL)
        except asyncio.CancelledError:
            pass

    async def _handle_cover(
        self, task_key: str, entity_id: str, mode: str, action: str
    ) -> None:
        """Handle cover actions."""
        if action == "short_press":
            service = "open_cover" if mode == "cover_open" else "close_cover"
            await self._hass.services.async_call(
                "cover", service, {"entity_id": entity_id}
            )
        elif action == "long_press_start":
            service = "open_cover" if mode == "cover_open" else "close_cover"
            await self._hass.services.async_call(
                "cover", service, {"entity_id": entity_id}
            )
        elif action in ("release", "long_press_release"):
            await self._hass.services.async_call(
                "cover", "stop_cover", {"entity_id": entity_id}
            )

    async def _handle_toggle(self, entity_id: str, action: str) -> None:
        """Handle toggle on short press."""
        if action == "short_press":
            domain = entity_id.split(".")[0]
            await self._hass.services.async_call(
                domain, "toggle", {"entity_id": entity_id}
            )

    async def _handle_service(
        self, entity_id: str, action: str, service: str
    ) -> None:
        """Handle turn_on/turn_off on short press."""
        if action == "short_press":
            domain = entity_id.split(".")[0]
            await self._hass.services.async_call(
                domain, service, {"entity_id": entity_id}
            )
