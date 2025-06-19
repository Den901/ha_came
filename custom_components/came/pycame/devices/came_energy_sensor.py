"""ETI/Domo energy sensor device."""

import logging
from typing import Optional
from ..exceptions import ETIDomoUnmanagedDeviceError  # <--- AGGIUNGI QUESTA RIGA

from .base import TYPE_ENERGY_SENSOR, CameDevice, DeviceState, StateType

_LOGGER = logging.getLogger(__name__)


class CameEnergySensor(CameDevice):
    """ETI/Domo energy sensor device class."""

    def __init__(
        self,
        manager,
        device_info: DeviceState,
        update_cmd_base: str = "meters",
        update_src_field: str = "array",
        device_class: Optional[str] = None,
    ):
        """Init instance."""
        super().__init__(
            manager, TYPE_ENERGY_SENSOR, device_info, device_class=device_class
        )

        self._update_cmd_base = update_cmd_base
        self._update_src_field = update_src_field

    def update(self):
        """Update device state."""
        try:
            self._force_update(self._update_cmd_base, self._update_src_field)
        except ETIDomoUnmanagedDeviceError:
            # Sensor is passive/read-only, just skip forced update
            _LOGGER.debug("Skipping unmanaged device: %s", self.name)

    def push_update(self, state: DeviceState):
        """Update from ETI/Domo push data."""
        _LOGGER.warning("🔁 push_update chiamato per %s", self.name)
        updated = self.update_state(state)
        if updated and hasattr(self, "hass_entity"):
            self.hass_entity.async_write_ha_state()

    @property
    def state(self) -> StateType:
        """Return the current power in W."""
        return self._device_info.get("instant_power")

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        return self._device_info.get("unit") or "W"

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes for the sensor."""
        return {
            "produced": self._device_info.get("produced"),
            "last_24h_avg": self._device_info.get("last_24h_avg"),
            "last_month_avg": self._device_info.get("last_month_avg"),
            "energy_unit": self._device_info.get("energy_unit"),
        }

