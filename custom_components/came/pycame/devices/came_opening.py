"""ETI/Domo relay device."""

import logging
from typing import Dict, List, Optional

from .base import TYPE_OPENING, CameDevice, DeviceState
from ..exceptions import ETIDomoUnmanagedDeviceError

_LOGGER = logging.getLogger(__name__)


# opening states
OPENING_STATE_STOP = 0
OPENING_STATE_OPEN = 1
OPENING_STATE_CLOSE = 2




#   "wanted_status" : <0/1/2/3/4>  // stop/open/close/slat open/slat close OR


class CameOpening(CameDevice):
    """ETI/Domo relay device class."""

    def __init__(self, manager, device_info: DeviceState):
        """Init instance."""
        super().__init__(manager, TYPE_OPENING, device_info)


    def opening(self, state: int = None):
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

        self._manager.application_request(cmd)

    def open(self): #APERTURA
        """Open the window."""
        self.opening(OPENING_STATE_OPEN)

    @property
    def act_id(self) -> Optional[int]:
        """Return the action ID for device."""
        return self._device_info.get("open_act_id")

    def _check_act_id(self):
        """Check for act ID availability."""
        if not self.act_id:
            raise ETIDomoUnmanagedDeviceError()

    def close(self): #CHIUSURA
        """Close the window."""
        self.opening(OPENING_STATE_CLOSE)

    def stop(self): #STOP
        """Stop the window."""
        self.opening(OPENING_STATE_STOP)


    def update(self):
        """Update device state."""
        self._force_update("opening")
