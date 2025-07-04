"""Support for the CAME covers."""
import logging
from typing import List

from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.cover import (
    ENTITY_ID_FORMAT,
    CoverEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .pycame.came_manager import CameManager
from .pycame.devices import CameDevice
from .pycame.devices.came_opening import (
    OPENING_STATE_OPEN,
    OPENING_STATE_CLOSE,
    OPENING_STATE_STOP,
)

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up CAME openings devices dynamically through discovery."""

    async def async_discover_sensor(dev_ids):
        """Discover and add a discovered CAME openings devices."""
        if not dev_ids:
            return

        entities = await hass.async_add_executor_job(_setup_entities, hass, dev_ids)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, SIGNAL_DISCOVERY_NEW.format(COVER_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(COVER_DOMAIN, [])
    await async_discover_sensor(devices_ids)


def _setup_entities(hass, dev_ids: List[str]):
    """Set up CAME opening devices."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue
        entities.append(CameCoverEntity(device))
    return entities


class CameCoverEntity(CameEntity, CoverEntity):
    """CAME opening device entity."""

    def __init__(self, device: CameDevice):
        """Initialize CAME opening device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)
        self._last_command = None  # "open" or "close"
        self._attr_assumed_state = True  # No feedback, we assume state

    @property
    def is_closed(self):
        """Return True if cover is closed."""
        if self._device.state == OPENING_STATE_OPEN:
            return False
        elif self._device.state == OPENING_STATE_CLOSE:
            return True
        elif self._device.state == OPENING_STATE_STOP:
            if self._last_command == "open":
                return False
            elif self._last_command == "close":
                return True
        return None  # Unknown state

    def open_cover(self):
        """Open the cover."""
        _LOGGER.debug("Open the cover %s", self.entity_id)
        self._last_command = "open"
        self._device.open()

    def close_cover(self):
        """Close the cover."""
        _LOGGER.debug("Close the cover %s", self.entity_id)
        self._last_command = "close"
        self._device.close()

    def stop_cover(self):
        """Stop the cover."""
        _LOGGER.debug("Stop the cover %s", self.entity_id)
        self._device.stop()
