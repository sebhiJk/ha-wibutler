"""Config flow for the Wibutler integration."""

import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .api import WibutlerHub
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=8081): int,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_VERIFY_SSL, default=False): bool,
        vol.Required(CONF_USE_SSL, default=False): bool,
    }
)

ROCKER_MODES = {
    "dim_up": "Dim Up",
    "dim_down": "Dim Down",
    "cover_open": "Cover Open",
    "cover_close": "Cover Close",
    "toggle": "Toggle",
    "turn_on": "Turn On",
    "turn_off": "Turn Off",
}


class WibutlerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Wibutler."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            hub = WibutlerHub(
                self.hass,
                user_input[CONF_HOST],
                user_input.get(CONF_PORT, 8081),
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input.get(CONF_VERIFY_SSL, False),
                user_input.get(CONF_USE_SSL, False),
            )

            try:
                if await hub.authenticate():
                    await self.async_set_unique_id(user_input[CONF_HOST])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Wibutler", data=user_input
                    )
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow handler."""
        return WibutlerOptionsFlowHandler()


class WibutlerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Wibutler options."""

    async def async_step_init(self, user_input=None):
        """Show main options menu."""
        if user_input is not None:
            next_step = user_input.get("next_step")
            if next_step == "rocker_menu":
                return await self.async_step_rocker_menu()
            return await self.async_step_connection()

        data_schema = vol.Schema(
            {
                vol.Required("next_step", default="connection"): vol.In(
                    {
                        "connection": "Connection Settings",
                        "rocker_menu": "Rocker Bindings",
                    }
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)

    async def async_step_connection(self, user_input=None):
        """Manage connection settings."""
        if user_input is not None:
            data = dict(self.config_entry.options)
            data.update(user_input)
            return self.async_create_entry(title="", data=data)

        current = self.config_entry.options or self.config_entry.data

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=current.get(CONF_HOST, "")
                ): str,
                vol.Required(
                    CONF_PORT, default=current.get(CONF_PORT, 8081)
                ): int,
                vol.Required(
                    CONF_USERNAME, default=current.get(CONF_USERNAME, "")
                ): str,
                vol.Required(
                    CONF_PASSWORD, default=current.get(CONF_PASSWORD, "")
                ): str,
                vol.Required(
                    CONF_VERIFY_SSL,
                    default=current.get(CONF_VERIFY_SSL, False),
                ): bool,
                vol.Required(
                    CONF_USE_SSL,
                    default=current.get(CONF_USE_SSL, False),
                ): bool,
            }
        )

        return self.async_show_form(step_id="connection", data_schema=data_schema)

    async def async_step_rocker_menu(self, user_input=None):
        """Show existing bindings and option to add/remove."""
        bindings = list(
            self.config_entry.options.get("rocker_bindings", [])
        )

        if user_input is not None:
            dim_duration = user_input.get("dim_duration", 5.0)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={**self.config_entry.options, "dim_duration": dim_duration},
            )

            action = user_input.get("action")
            if action == "add":
                return await self.async_step_add_binding()
            if action and action.startswith("remove_"):
                idx = int(action.split("_", 1)[1])
                bindings.pop(idx)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options={**self.config_entry.options, "rocker_bindings": bindings},
                )
                return await self.async_step_rocker_menu()

        current_duration = self.config_entry.options.get("dim_duration", 5.0)

        actions = {"add": "Add Binding"}
        for i, b in enumerate(bindings):
            entities = b.get("target_entity_ids", [b["target_entity_id"]] if "target_entity_id" in b else [])
            label = f"{b.get('device_name', b['device_id'])} {b['button']} -> {', '.join(entities)} ({b['mode']})"
            actions[f"remove_{i}"] = f"Remove: {label}"

        data_schema = vol.Schema(
            {
                vol.Required("dim_duration", default=current_duration): vol.All(
                    vol.Coerce(float), vol.Range(min=1.0, max=30.0)
                ),
                vol.Required("action"): vol.In(actions),
            }
        )

        return self.async_show_form(
            step_id="rocker_menu",
            data_schema=data_schema,
        )

    async def async_step_add_binding(self, user_input=None):
        """Add a new rocker binding."""
        if user_input is not None:
            bindings = list(
                self.config_entry.options.get("rocker_bindings", [])
            )

            hub = self.config_entry.runtime_data
            device = hub.devices.get(user_input["device_button"].split("|")[0], {})

            bindings.append(
                {
                    "device_id": user_input["device_button"].split("|")[0],
                    "device_name": device.get("name", ""),
                    "button": user_input["device_button"].split("|")[1],
                    "target_entity_ids": user_input["target_entity_ids"],
                    "mode": user_input["mode"],
                }
            )
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={**self.config_entry.options, "rocker_bindings": bindings},
            )
            return await self.async_step_rocker_menu()

        hub = self.config_entry.runtime_data
        bindings = self.config_entry.options.get("rocker_bindings", [])
        bound_keys = {f"{b['device_id']}|{b['button']}" for b in bindings}

        button_options = {}
        for device_id, device in hub.devices.items():
            for comp in device.get("components", []):
                name = comp.get("name", "")
                if name.startswith("BTN"):
                    key = f"{device_id}|{name}"
                    if key in bound_keys:
                        continue
                    label = f"{device.get('name', device_id)} - {comp.get('text', name)}"
                    button_options[key] = label

        if not button_options:
            return await self.async_step_rocker_menu()

        data_schema = vol.Schema(
            {
                vol.Required("device_button"): vol.In(button_options),
                vol.Required("target_entity_ids"): EntitySelector(
                    EntitySelectorConfig(multiple=True)
                ),
                vol.Required("mode"): vol.In(ROCKER_MODES),
            }
        )

        return self.async_show_form(
            step_id="add_binding",
            data_schema=data_schema,
        )
