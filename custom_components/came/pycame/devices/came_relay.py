"""ETI/Domo relay device."""

import logging
from typing import List

from .base import TYPE_GENERIC_RELAY, CameDevice, DeviceState

_LOGGER = logging.getLogger(__name__)

# relay states
GENERIC_RELAY_STATE_OFF = 0
GENERIC_RELAY_STATE_ON = 1


class CameRelay(CameDevice):
    """ETI/Domo relay device class."""

    def __init__(self, manager, device_info: DeviceState):
        """Init instance."""
        super().__init__(manager, TYPE_GENERIC_RELAY, device_info)


    async def switch(self, state: int = None):
        """Switch relay to new state."""
        if state is None:
            raise ValueError("At least one parameter is required")

        self._check_act_id()

        cmd = {
            "cmd_name": "relay_activation_req",
            "act_id": self.act_id,
            "wanted_status": state if state is not None else self.state,
        }
        log = {}
        if state is not None:
            log["status"] = cmd["wanted_status"]


        _LOGGER.debug('Set new state for relay "%s": %s', self.name, log)

        await self._manager.application_request(cmd)

    async def turn_off(self):
        """Turn off relay."""
        await self.switch(GENERIC_RELAY_STATE_OFF)

    async def turn_on(self):
        """Turn on relay."""
        await self.switch(GENERIC_RELAY_STATE_ON)


    async def update(self):
        """Update device state."""
        _LOGGER.debug('Updating state for relay "%s"', self.name)
        await self._force_update("relay")
