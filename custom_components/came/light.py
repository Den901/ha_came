"""Support for the CAME lights."""
import logging
from typing import List, Optional

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pycame.came_manager import CameManager
from pycame.devices import CameDevice
from pycame.devices.came_light import LIGHT_STATE_ON

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity

_LOGGER = logging.getLogger(__name__)

# Definisci l'ENTITY_ID_FORMAT qui
ENTITY_ID_FORMAT = "light.came_{}"

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up CAME light devices dynamically through discovery."""
    async def async_discover_sensor(dev_ids):
        """Discover and add discovered CAME light devices."""
        if not dev_ids:
            return

        entities = await hass.async_add_executor_job(_setup_entities, hass, dev_ids)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, SIGNAL_DISCOVERY_NEW.format(LIGHT_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(LIGHT_DOMAIN, [])
    await async_discover_sensor(devices_ids)

def _setup_entities(hass, dev_ids: List[str]):
    """Set up CAME light device."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue
        entities.append(CameLightEntity(device))
    return entities

class CameLightEntity(CameEntity, LightEntity):
    """CAME light device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME light device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

        # Imposta i color modes
        self._attr_supported_color_modes = set()
        self._attr_color_mode: Optional[ColorMode] = None

        # Controlla se il dispositivo supporta la luminosità
        if self._device.support_brightness:
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)

        # Controlla se il dispositivo supporta il colore
        if self._device.support_color:
            self._attr_supported_color_modes.add(ColorMode.HS)
            self._attr_color_mode = ColorMode.HS
        else:
            # Se non supporta il colore, imposta un modo di default
            self._attr_color_mode = ColorMode.BRIGHTNESS

        # Se non ci sono color modes supportati, imposta un modo predefinito
        if not self._attr_supported_color_modes:
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)  # Assicurati di avere un modo valido

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

    @property
    def color_mode(self) -> Optional[ColorMode]:
        """Return the color mode of the light."""
        return self._attr_color_mode
