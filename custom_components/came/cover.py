from typing import Optional

from homeassistant.components.cover import (
    CoverEntity,
    DEVICE_CLASS_WINDOW,  # Sostituisci con la device class corretta per le aperture
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from pycame.came_manager import CameManager
from pycame.devices import CameDevice

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity
from .your_opening_module import CameOpening, OPENING_STATE_OPEN, OPENING_STATE_CLOSED

class CameOpeningEntity(CameEntity, CoverEntity):
    """CAME opening device entity."""

    def __init__(self, device: CameOpening):
        """Init CAME opening device entity."""
        super().__init__(device)

    @property
    def current_cover_position(self) -> Optional[int]:
        """Return the current position of the cover."""
        return 100 if self._device.opening_state == OPENING_STATE_OPEN else 0

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return self._device.opening_state == OPENING_STATE_OPEN

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return self._device.opening_state == OPENING_STATE_CLOSED

    def open_cover(self, **kwargs) -> None:
        """Open the cover."""
        self._device.open()

    def close_cover(self, **kwargs) -> None:
        """Close the cover."""
        self._device.close()

    def set_cover_position(self, **kwargs) -> None:
        """Move the cover to a specific position."""
        position = kwargs.get("position")
        if position is None:
            return
        if position == 0:
            self.close_cover()
        elif position == 100:
            self.open_cover()

    async def async_update(self):
        """Update device state."""
        await self._device.update()
