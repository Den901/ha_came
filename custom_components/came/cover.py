"""Support for the CAME openings (covers) devices."""

from homeassistant.components.cover import CoverEntity

class CameOpeningEntity(CoverEntity):
    """CAME openings (covers) device entity."""

    def __init__(self, device):
        """Initialize the cover entity."""
        self._device = device  # Assuming you have a CameDevice instance

    @property
    def name(self):
        """Return the name of the cover."""
        return self._device.name

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._device.is_closed  # Implement this based on your device's logic

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        return self._device.current_cover_position  # Implement this based on your device's logic

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._device.open_cover()  # Implement this based on your device's logic

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        await self._device.close_cover()  # Implement this based on your device's logic

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get('position')
        await self._device.set_cover_position(position)  # Implement this based on your device's logic

    @property
    def supported_features(self):
        """Return the supported features of the cover."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION  # Adjust based on your device's capabilities
