"""ETI/Domo digitalin device."""

import logging
from typing import Optional

from .base import TYPE_DIGITALIN, CameDevice, DeviceState, StateType

_LOGGER = logging.getLogger(__name__)

# Binary Sensor states
BINARY_SENSOR_STATE_OFF = 0
BINARY_SENSOR_STATE_ON = 1


class CameDigitalIn(CameDevice):
    """ETI/Domo digitalin  device class."""

    def __init__(
        self,
        manager,
        device_info: DeviceState,
        device_class: Optional[str] = "switch",
    ):  
        """Init instance."""
        super().__init__(
            manager, TYPE_DIGITALIN, device_info, device_class=device_class)

    def update(self):
        """Update device state."""
        self._force_update(self._update_cmd_base, self._update_src_field)


    @property
    def is_on(self) -> StateType:
        """Return the current device state."""
        return self._device_info.get("status")

