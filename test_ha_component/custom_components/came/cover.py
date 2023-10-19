"""Support for the CAME lights."""
import logging
from typing import List


from homeassistant.components.light import COVER as COVER_DOMAIN
from homeassistant.components.light import (
    ENTITY_ID_FORMAT,
    CoverEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pycame.came_manager import CameManager
from pycame.devices import CameDevice
from pycame.devices.came_light import OPENING_STATE_OPEN

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
        hass, SIGNAL_DISCOVERY_NEW.format(OPENING_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(COVER_DOMAIN, [])
    await async_discover_sensor(devices_ids)


def _setup_entities(hass, dev_ids: List[str]):
    """Set up CAME opening device."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue
        entities.append(CameOpeningEntity(device))
    return entities


class CameCoverEntity(CameEntity, CoverEntity):
    """CAME opening device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME opening device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)



    @property
    def is_open(self):
        """Return true if cover is open."""
        return self._device.state == OPENING_STATE_OPEN

    def open(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("Open the cover %s", self.entity_id)
        self._device.open()


    def stop(self, **kwargs):
        """Instruct the cover to stop."""
        _LOGGER.debug("Stop the cover %s", self.entity_id)
        self._device.stop()


    def close(self, **kwargs):
        """Instruct the cover to close."""
        _LOGGER.debug("Stop the cover %s", self.entity_id)
        self._device.close()
