"""Support for the CAME lights."""
import logging
from typing import List

import asyncio

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_HS_COLOR
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.light import (
    ENTITY_ID_FORMAT,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .pycame.came_manager import CameManager
from .pycame.devices import CameDevice
from .pycame.devices.came_light import LIGHT_STATE_ON

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up CAME light devices dynamically through discovery."""
    from .const import DOMAIN, CONF_MANAGER

    manager = hass.data[DOMAIN][CONF_MANAGER]
    _LOGGER.debug("Setting up CAME Light platform with manager: %s", manager)

    async def async_discover_sensor(manager, hass, dev_ids):
        _LOGGER.debug("Discovering CAME light devices: %s", dev_ids)
        devices = []
        for dev_id in dev_ids:
            _LOGGER.debug("Fetching device by id: %s", dev_id)
            device = await manager.get_device_by_id(dev_id)
            if device:
                _LOGGER.debug("Device found: %s", device)
                devices.append(device)
            else:
                _LOGGER.warning("Device with id %s not found", dev_id)
        _LOGGER.debug("Passing devices to _setup_entities: %s", devices)
        entities = await hass.async_add_executor_job(_setup_entities, hass, devices)
        _LOGGER.debug("Entities created: %s", entities)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, SIGNAL_DISCOVERY_NEW.format(LIGHT_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(LIGHT_DOMAIN, [])
    _LOGGER.debug("Calling async_discover_sensor with devices_ids: %s", devices_ids)
    await async_discover_sensor(manager, hass, devices_ids)
    _LOGGER.debug("Finished async_discover_sensor for devices_ids: %s", devices_ids)


def _setup_entities(hass, devices):
    _LOGGER.debug("Setting up entities for devices: %s", devices)
    entities = []
    for device in devices:
        _LOGGER.debug("Creating CameLightEntity for device: %s", device)
        entities.append(CameLightEntity(device))
    _LOGGER.debug("All entities created: %s", entities)
    return entities


class CameLightEntity(CameEntity, LightEntity):
    """CAME light device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME light device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

        # Debug: Log the features supported by the device
        _LOGGER.debug(
            f"Initializing light entity {self.entity_id}. "
            f"Support brightness: {getattr(self._device, 'support_brightness', False)}, "
            f"Support color: {getattr(self._device, 'support_color', False)}"
        )

        # Set the supported features
        self._attr_supported_features = 0  # Initially no supported features

        # Add brightness support only if explicitly requested
        if getattr(self._device, 'support_brightness', False):
            self._attr_supported_features |= SUPPORT_BRIGHTNESS

        # Add color support only if explicitly requested
        if getattr(self._device, 'support_color', False):
            self._attr_supported_features |= SUPPORT_COLOR

        # Debug: Log the final supported features
        _LOGGER.debug(
            f"Final supported features for {self.entity_id}: {self._attr_supported_features}"
        )

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._device.state == LIGHT_STATE_ON

    @property
    def brightness(self):
        """Return the brightness of the light."""
        # Check if the device supports brightness
        if not hasattr(self._device, 'brightness') or not getattr(self._device, 'support_brightness', False):
            return None
        return round(self._device.brightness * 255 / 100)  # Convert from 0-100 to 0-255

    @property
    def hs_color(self):
        """Return the hs_color of the light."""
        # Check if the device supports color
        if not hasattr(self._device, 'hs_color') or not getattr(self._device, 'support_color', False):
            return None
        return tuple(self._device.hs_color)

    async def async_turn_on(self, **kwargs):
        """Turn on or control the light."""
        _LOGGER.debug("Turn on light %s", self.entity_id)

        # Check if the device supports brightness and if a value was provided
        if ATTR_BRIGHTNESS in kwargs and hasattr(self._device, 'set_brightness'):
            brightness = kwargs[ATTR_BRIGHTNESS]
            _LOGGER.debug("Setting brightness for %s to %s (HA 0-255 scale)", self.entity_id, brightness)
            self._device.set_brightness(round(brightness * 100 / 255))  # Convert from 0-255 to 0-100

        # Check if the device supports color and if a value was provided
        if ATTR_HS_COLOR in kwargs and hasattr(self._device, 'set_hs_color'):
            hs_color = kwargs[ATTR_HS_COLOR]
            _LOGGER.debug("Setting hs_color for %s to %s", self.entity_id, hs_color)
            self._device.set_hs_color(hs_color)

        # If there are no specific commands, simply turn on the light
        if not kwargs:
            _LOGGER.debug("No kwargs provided, turning on light %s", self.entity_id)
            await self._device.turn_on()
        else:
            _LOGGER.debug("Turn on called with kwargs for %s: %s", self.entity_id, kwargs)
        
        await asyncio.sleep(1) # Allow some time for the device to process the command
        
        self.schedule_update_ha_state(True)

    async def async_turn_off(self, **kwargs):
        """Turn off the light."""
        _LOGGER.debug("Async turn_off called for %s", self.entity_id)
        await self._device.turn_off()
        
        await asyncio.sleep(1) # Allow some time for the device to process the command
        
        self.schedule_update_ha_state(True)

    async def async_update(self):
        """Fetch new state data for this light from the device."""
        _LOGGER.debug("update called for %s", self.entity_id)
        await self._device.update()

