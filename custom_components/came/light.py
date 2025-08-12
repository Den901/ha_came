"""Support for the CAME lights."""
import logging
from typing import List

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

    async def async_discover_sensor(dev_ids):
        """Discover and add a discovered CAME light devices."""
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

        # Debug: Log delle funzionalità supportate dal dispositivo
        _LOGGER.debug(
            f"Initializing light entity {self.entity_id}. "
            f"Support brightness: {getattr(self._device, 'support_brightness', False)}, "
            f"Support color: {getattr(self._device, 'support_color', False)}"
        )

        # Imposta le funzionalità supportate
        self._attr_supported_features = 0  # Inizialmente nessuna funzionalità supportata

        # Aggiungi supporto per la luminosità solo se esplicitamente richiesto
        if getattr(self._device, 'support_brightness', False):
            self._attr_supported_features |= SUPPORT_BRIGHTNESS

        # Aggiungi supporto per il colore solo se esplicitamente richiesto
        if getattr(self._device, 'support_color', False):
            self._attr_supported_features |= SUPPORT_COLOR

        # Debug: Log delle funzionalità finali
        _LOGGER.debug(
            f"Final supported features for {self.entity_id}: {self._attr_supported_features}"
        )

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._device.state == LIGHT_STATE_ON

    def turn_on(self, **kwargs):
        """Turn on or control the light."""
        _LOGGER.debug("Turn on light %s", self.entity_id)

        # Controlla se il dispositivo supporta la luminosità e se è stato passato un valore
        if ATTR_BRIGHTNESS in kwargs and hasattr(self._device, 'set_brightness'):
            brightness = kwargs[ATTR_BRIGHTNESS]
            self._device.set_brightness(round(brightness * 100 / 255))  # Converti da 0-255 a 0-100

        # Controlla se il dispositivo supporta il colore e se è stato passato un valore
        if ATTR_HS_COLOR in kwargs and hasattr(self._device, 'set_hs_color'):
            hs_color = kwargs[ATTR_HS_COLOR]
            self._device.set_hs_color(hs_color)

        # Se non ci sono comandi specifici, accendi semplicemente la luce
        if not kwargs:
            self._device.turn_on()

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        _LOGGER.debug("Turn off light %s", self.entity_id)
        self._device.turn_off()

    @property
    def brightness(self):
        """Return the brightness of the light."""
        # Verifica se il dispositivo supporta la luminosità
        if not hasattr(self._device, 'brightness') or not getattr(self._device, 'support_brightness', False):
            return None
        return round(self._device.brightness * 255 / 100)  # Converti da 0-100 a 0-255

    @property
    def hs_color(self):
        """Return the hs_color of the light."""
        # Verifica se il dispositivo supporta il colore
        if not hasattr(self._device, 'hs_color') or not getattr(self._device, 'support_color', False):
            return None
        return tuple(self._device.hs_color)
