"""Adds config flow for Came."""

from typing import Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from homeassistant.helpers.typing import ConfigType
from .pycame.came_manager import CameManager

from .const import DOMAIN  # pylint: disable=unused-import


class CameFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Came."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_import(self, platform_config: ConfigType):
        """Import a config entry.

        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data=platform_config)

    async def async_step_user(self, user_input: Optional[ConfigType] = None):
        """Handle a flow initialized by the user."""
        errors = {}

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._test_credentials(user_input)
            if valid:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )

            errors["base"] = "auth"

        return await self._show_config_form(user_input, errors)

    async def _show_config_form(
        self, cfg: ConfigType, errors
    ):  # pylint: disable=unused-argument
        """Show the configuration form to edit location data."""
        if cfg is None:
            cfg = {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=cfg.get(CONF_HOST)): cv.string,
                    vol.Required(
                        CONF_USERNAME, default=cfg.get(CONF_USERNAME)
                    ): cv.string,
                    vol.Required(
                        CONF_PASSWORD, default=cfg.get(CONF_PASSWORD)
                    ): cv.string,
                    vol.Required(CONF_TOKEN, default=cfg.get(CONF_TOKEN)): cv.string,
                }
            ),
            errors=errors,
        )

    async def _test_credentials(self, config: ConfigType):
        """Return true if credentials is valid."""
        try:
            manager = CameManager(
                config[CONF_HOST],
                config[CONF_USERNAME],
                config[CONF_PASSWORD],
                config[CONF_TOKEN],
            )
            await self.hass.async_add_executor_job(manager.login)
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False
