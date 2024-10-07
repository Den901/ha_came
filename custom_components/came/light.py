"""Support for the CAME lights."""

import logging
from typing import List
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_HS_COLOR
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.light import (
    LightEntity,
    LightEntityFeature,
    COLOR_MODE_BRIGHTNESS,
    COLOR_MODE_HS
)
from homeassistant.helpers.entity import ENTITY_ID_FORMAT
from pycame.devices import CameDevice
from pycame.devices.came_light import LIGHT_STATE_ON

from .entity import CameEntity  # Assicurati che questo venga importato correttamente
from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW

_LOGGER = logging.getLogger(__name__)

class CameLightEntity(CameEntity, LightEntity):
    """CAME light device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME light device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

        self._attr_supported_features = 0
        if self._device.support_brightness:
            self._attr_supported_features |= LightEntityFeature.BRIGHTNESS
        if self._device.support_color:
            self._attr_supported_features |= LightEntityFeature.COLOR

    @property
    def supported_color_modes(self):
        """Return the supported color modes."""
        modes = set()
        if self._device.support_brightness:
            modes.add(COLOR_MODE_BRIGHTNESS)
        if self._device.support_color:
            modes.add(COLOR_MODE_HS)
        return modes

    @property
    def color_mode(self):
        """Return the current color mode."""
        if self._device.support_color:
            return COLOR_MODE_HS
        if self._device.support_brightness:
            return COLOR_MODE_BRIGHTNESS
        return None

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._device.state == LIGHT_STATE_ON

    def turn_on(self, **kwargs):
        """Turn on or control the light."""
        _LOGGER.debug("Turn on light %s", self.entity_id)
        if ATTR_BRIGHTNESS not in kwargs and ATTR_HS_COLOR not in kwargs:
            self._device.turn_on()
        else:
            if ATTR_BRIGHTNESS in kwargs:
                self._device.set_brightness(round(kwargs[ATTR_BRIGHTNESS] * 100 / 255))
            if ATTR_HS_COLOR in kwargs:
                self._device.set_hs_color(kwargs[ATTR_HS_COLOR])

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        _LOGGER.debug("Turn off light %s", self.entity_id)
        self._device.turn_off()

    @property
    def brightness(self):
        """Return the brightness of the light."""
        if not self._device.support_brightness:
            return None
        return round(self._device.brightness * 255 / 100)

    @property
    def hs_color(self):
        """Return the hs_color of the light."""
        if not self._device.support_color:
            return None
        return tuple(self._device.hs_color)
