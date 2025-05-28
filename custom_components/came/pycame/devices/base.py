"""ETI/Domo abstract devices."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from _sha1 import sha1

from ..exceptions import ETIDomoUnmanagedDeviceError
from ..models import Floor, Room

_LOGGER = logging.getLogger(__name__)


TYPE_LIGHT = 0
TYPE_THERMOSTAT = 2
TYPE_ANALOG_SENSOR = -1
TYPE_GENERIC_RELAY = 11
TYPE_OPENING = 1
TYPE_ENERGY_SENSOR = -2 #energy measurement
TYPE_DIGITALIN = 14

TYPES = {
    # Internal types
    -2: "Energy Sensor",
    -1: "Analog Sensor",
    0: "Light",
    1: "Opening",
    2: "Thermostat",
    3: "Page",
    4: "Scenario",
    5: "Camera",
    6: "Security Panel",
    7: "Security Area",
    8: "Security Scenario",
    9: "Security Input",
    10: "Security output",
    11: "Generic relay",
    12: "Generic text",  # currently disabled
    13: "Sound zone",
    14: "Digital input",  # technical alarm
}

StateType = Union[None, str, int, float]
DeviceState = Dict[str, Any]


class CameDevice(ABC):
    """ETI/Domo abstract device class."""

    @abstractmethod
    def __init__(
        self,
        manager,
        type_id: int,
        device_info: DeviceState,
        device_class: Optional[str] = "",
    ):
        """Init instance."""
        self._manager = manager
        self._type_id = type_id
        self._device_info = device_info

        self._device_class = device_class if device_class != "" else self.type.lower()

    @property
    def unique_id(self) -> str:
        """Return the unique ID of device."""
        return "-".join(
            [str(self._type_id), sha1(self.name.encode("utf-8")).hexdigest()]
        )

    @property
    def type_id(self) -> int:
        """Return the type ID of device."""
        return self._type_id

    @property
    def type(self) -> str:
        """Return the type of device."""
        return TYPES[self._type_id]

    @property
    def name(self) -> Optional[str]:
        """Return the name of device."""
        return self._device_info.get("name")

    @property
    def act_id(self) -> Optional[int]:
        """Return the action ID for device."""
        return self._device_info.get("act_id")

    def _check_act_id(self):
        """Check for act ID availability."""
        if not self.act_id:
            raise ETIDomoUnmanagedDeviceError()

    @property
    def floor_id(self) -> Optional[int]:
        """Return the device's floor ID."""
        return self._device_info.get("floor_ind")

    @property
    def floor(self) -> Optional[Floor]:
        """Return the device's floor instance."""
        for floor in self._manager.get_all_floors():
            if floor.id == self.floor_id:
                return floor

        return Floor(id=self.floor_id, name=f"Floor #{self.floor_id}")

    @property
    def room_id(self) -> Optional[int]:
        """Return the device's room ID."""
        return self._device_info.get("room_ind")

    @property
    def room(self) -> Optional[Room]:
        """Return the device's room instance."""
        for room in self._manager.get_all_rooms():
            if room.id == self.room_id:
                return room

        return Room(
            id=self.room_id, name=f"Room #{self.room_id}", floor_id=self.floor_id
        )

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self._manager.connected

    @property
    def state(self) -> StateType:
        """Return the current device state."""
        return self._device_info.get("status")

    def update_state(self, state: DeviceState) -> bool:
        """Update device state."""
        if state.get("act_id") != self.act_id:
            return False

        if state.get("cmd_name"):
            state.pop("cmd_name")

        log = {}
        for k, val in state.items():
            if self._device_info.get(k) != val:
                log[k] = val
        if log:
            _LOGGER.debug(
                'Received new state for %s "%s": %s',
                self.type.lower(),
                self.name,
                log,
            )

        self._device_info = state

        return bool(log)

    def _force_update(self, cmd_base: str, field: str = "array"):
        """Force update device state."""
        self._check_act_id()

        cmd = {
            "cmd_name": f"{cmd_base}_list_req",
            "topologic_scope": "act",
            "value": self.act_id,
        }
        res = self._manager.application_request(cmd, f"{cmd_base}_list_resp").get(
            field, []
        )
        if not isinstance(res, list):
            res = [res]
        for device_info in res:  # type: DeviceState
            if device_info.get("act_id") == self.act_id:
                self.update_state(device_info)
                return

    @abstractmethod
    def update(self):
        """Update device state."""
        raise NotImplementedError

    @property
    def device_class(self) -> Optional[str]:
        """Return the class of this device."""
        return self._device_class
