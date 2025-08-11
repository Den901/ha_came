"""Support for the CAME digitalin."""
import logging
from typing import List

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .pycame.came_manager import CameManager
from .pycame.devices import CameDevice
from .pycame.devices.came_digitalin import BINARY_SENSOR_STATE_OFF

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up CAME digitalin devices dynamically through discovery."""
    from .const import DOMAIN, CONF_MANAGER
    manager = hass.data[DOMAIN][CONF_MANAGER]

    async def async_discover_sensor(dev_ids):
        """Discover and add a discovered CAME digitalin devices."""
        if not dev_ids:
            return

        devices = []
        for dev_id in dev_ids:
            device = await manager.get_device_by_id(dev_id)
            if device:
                devices.append(device)
        entities = await hass.async_add_executor_job(_setup_entities, hass, devices)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, SIGNAL_DISCOVERY_NEW.format(BINARY_SENSOR_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(BINARY_SENSOR_DOMAIN, [])
    await async_discover_sensor(devices_ids)


def _setup_entities(hass, devices):
    """Set up CAME digitalin device."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for device in devices:
        entities.append(CameDigitalInEntity(device))
    return entities


class CameDigitalInEntity(CameEntity, BinarySensorEntity):
    """CAME digitalin device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME digitalin device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._device.state == BINARY_SENSOR_STATE_OFF

    async def async_update(self):
        """Fetch new state data for this digitalIn from the device."""
        _LOGGER.debug("update called for %s", self.entity_id)
        await self._device.update()