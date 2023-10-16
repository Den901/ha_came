"""Support for the CAME relays."""
import logging
from typing import List

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    SwitchEntity,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pycame.came_manager import CameManager
from pycame.devices import CameDevice
from pycame.devices.came_relay import GENERIC_RELAY_STATE_ON

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up CAME relay devices dynamically through discovery."""

    async def async_discover_sensor(dev_ids):
        """Discover and add a discovered CAME relay devices."""
        if not dev_ids:
            return

        entities = await hass.async_add_executor_job(_setup_entities, hass, dev_ids)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, SIGNAL_DISCOVERY_NEW.format(SWITCH_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(SWITCH_DOMAIN, [])
    await async_discover_sensor(devices_ids)


def _setup_entities(hass, dev_ids: List[str]):
    """Set up CAME switch device."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue
        entities.append(CameRelayEntity(device))
    return entities


class CameRelayEntity(CameEntity, RelayEntity):
    """CAME relay device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME switch device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)


    @property
    def is_on(self):
        """Return true if relay is on."""
        return self._device.state == GENERIC_RELAY_STATE_ON

    def turn_on(self, **kwargs):
        """Turn on or control the relay."""
        _LOGGER.debug("Turn on relay %s", self.entity_id)
        self._device.turn_on()


    def turn_off(self, **kwargs):
        """Instruct the relay to turn off."""
        _LOGGER.debug("Turn off relay %s", self.entity_id)
        self._device.turn_off()
