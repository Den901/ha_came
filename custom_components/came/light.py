"""Support for the CAME lights."""
import logging
from typing import List

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_HS_COLOR
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.light import LightEntityFeature
from homeassistant.components.light import ENTITY_ID_FORMAT, LightEntity

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
        support_brightness = getattr(self._device, 'support_brightness', False)
        support_color = getattr(self._device, 'support_color', False)

        _LOGGER.debug(
            f"Initializing light entity {self.entity_id}. "
            f"Support brightness: {support_brightness}, Support color: {support_color}"
        )

        # Definisci solo i supported_color_modes (richiesto da HA 2025.3)
        if support_color:
            self._attr_supported_color_modes = {"hs"}
        elif support_brightness:
            self._attr_supported_color_modes = {"brightness"}
        else:
            self._attr_supported_color_modes = {"onoff"}

        # Debug finale
        _LOGGER.debug(
            f"Final supported color modes for {self.entity_id}: {self._attr_supported_color_modes}"
        )


    @property
    def is_on(self):
        """Return true if light is on."""
        return self._device.state == LIGHT_STATE_ON

    def turn_on(self, **kwargs):
        """Turn on or control the light senza bloccare HA."""
        _LOGGER.debug("[DEBUG DIMMER] %s → richiesto turn_on con brightness=%s",
                        self.entity_id, kwargs.get(ATTR_BRIGHTNESS))

        brightness_pct = None
        if ATTR_BRIGHTNESS in kwargs and hasattr(self._device, 'set_brightness'):
            brightness_pct = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)

        if self._device.state == LIGHT_STATE_ON:
            # Luce già accesa → applico subito brightness
            if brightness_pct is not None:
                self._device.set_brightness(brightness_pct)
                _LOGGER.debug("[DEBUG DIMMER] %s → luce già ON, applico subito brightness %s",
                              self.entity_id, brightness_pct)
        else:
            # Luce spenta → prima ON, poi brightness al prossimo update
            self._pending_brightness = brightness_pct
            self._device.turn_on()
            _LOGGER.debug("[DEBUG DIMMER] %s → comando turn_on inviato,"
                          " attendo conferma ETI per applicare brightness %s",
                          self.entity_id, brightness_pct)

        # Aggiorno subito HA (UI reattiva)
        self.schedule_update_ha_state()
        
    def update(self):
        """Aggiornamento dello stato dal device."""
        if getattr(self, "_pending_brightness", None) is not None and self._device.state == LIGHT_STATE_ON:
            _LOGGER.debug("[DEBUG DIMMER] %s → ETI ha confermato ON, applico brightness %s",
                          self.entity_id, self._pending_brightness)
            self._device.set_brightness(self._pending_brightness)
            self._pending_brightness = None
        


    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        _LOGGER.debug("Turn off light %s", self.entity_id)
        self._pending_brightness = None
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
        
    @property
    def color_mode(self):
        """Return the current color mode of the light."""
        if getattr(self._device, 'support_color', False):
            return "hs"
        elif getattr(self._device, 'support_brightness', False):
            return "brightness"
        else:
            return "onoff"
