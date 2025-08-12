"""ETI/Domo relay device."""

import logging
from typing import Dict, List, Optional

from .base import TYPE_OPENING, CameDevice, DeviceState
from ..exceptions import ETIDomoUnmanagedDeviceError

_LOGGER = logging.getLogger(__name__)


# opening states
OPENING_STATE_STOPED = 0
OPENING_STATE_OPENNING = 1
OPENING_STATE_CLOSING = 2

#   "wanted_status" : <0/1/2/3/4>  // stop/open/close/slat open/slat close OR


class CameOpening(CameDevice):
    """ETI/Domo relay device class."""

    def __init__(self, manager, device_info: DeviceState):
        """Init instance."""
        super().__init__(manager, TYPE_OPENING, device_info)


    async def opening(self, state: int = None):
        """Switch opening to new state."""
        if state is None:
            raise ValueError("At least one parameter is required")

        self._check_act_id()

        cmd = {
            "cmd_name": "opening_move_req",
            "act_id": self.act_id,
            "wanted_status": state if state is not None else self.state,
        }
        log = {}
        if state is not None:
            log["status"] = cmd["wanted_status"]


        _LOGGER.debug('Set new state for the opening "%s": %s', self.name, log)

        await self._manager.application_request(cmd)

    async def open(self): #APERTURA
        """Open the window."""
        await self.opening(OPENING_STATE_OPENNING)

    @property
    def act_id(self) -> Optional[int]:
        """Return the action ID for device."""
        return self._device_info.get("open_act_id")

    def _check_act_id(self):
        """Check for act ID availability."""
        if not self.act_id:
            raise ETIDomoUnmanagedDeviceError()

    async def close(self): #CHIUSURA
        """Close the window."""
        await self.opening(OPENING_STATE_CLOSING)

    async def stop(self): #STOP
        """Stop the window."""
        await self.opening(OPENING_STATE_STOPED)


    async def update(self):
        """Update device state."""
        _LOGGER.debug('Updating state for opening "%s"', self.name)
        await self._force_update("openings")
