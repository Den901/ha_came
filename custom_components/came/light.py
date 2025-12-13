"""Support for the CAME lights."""
import asyncio
from typing import List

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_HS_COLOR
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.light import (
    ENTITY_ID_FORMAT,
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


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    async def async_discover_sensor(dev_ids):
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
    manager = hass.data[DOMAIN][CONF_MANAGER]
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue
        entities.append(CameLightEntity(device))
    return entities


class CameLightEntity(CameEntity, LightEntity):

    def __init__(self, device: CameDevice):
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

        # anti-rimbalzo brightness
        self._pending_brightness = None

        # anti-rimbalzo colore
        self._pending_hs_color = None

        if getattr(self._device, "support_color", False):
            color_modes = {"hs"}
        elif getattr(self._device, "support_brightness", False):
            color_modes = {"brightness"}
        else:
            color_modes = {"onoff"}

        self._attr_supported_color_modes = color_modes

    @property
    def is_on(self):
        return self._device.state == LIGHT_STATE_ON

    async def _wait_for_on(self, path_label):
        """
        Attesa per ETI/Domo: prima che la luce sia disponibile
        per ricevere comandi (brightness / color).
        """
        for step in range(5):
            if self._device.state == LIGHT_STATE_ON:
                await asyncio.sleep(0.20)
                break

            await asyncio.sleep(0.3)

    async def async_turn_on(self, **kwargs):

        brightness_request = ATTR_BRIGHTNESS in kwargs
        color_request = ATTR_HS_COLOR in kwargs

        # CASO COMBINATO: COLOR + BRIGHTNESS da automazioni
        if brightness_request and color_request:

            brightness = kwargs[ATTR_BRIGHTNESS]
            percent = round(brightness * 100 / 255)
            hs = kwargs[ATTR_HS_COLOR]

            self._pending_brightness = percent
            self._pending_hs_color = hs

            await self.hass.async_add_executor_job(self._device.turn_on)
            await self._wait_for_on("combo")

            await self.hass.async_add_executor_job(self._device.set_hs_color, hs)

            await asyncio.sleep(0.6)

            await self.hass.async_add_executor_job(
                self._device.set_brightness, percent
            )

            self.async_write_ha_state()
            return

        # BRIGHTNESS PATH (solo brightness)
        if brightness_request and hasattr(self._device, "set_brightness"):

            brightness = kwargs[ATTR_BRIGHTNESS]
            percent = round(brightness * 100 / 255)
            self._pending_brightness = percent

            await self.hass.async_add_executor_job(self._device.turn_on)
            await self._wait_for_on("bri")

            await self.hass.async_add_executor_job(self._device.set_brightness, percent)

            self.async_write_ha_state()
            return

        # COLOR PATH (solo colore)
        if color_request and hasattr(self._device, "set_hs_color"):

            hs = kwargs[ATTR_HS_COLOR]
            self._pending_hs_color = hs

            await self.hass.async_add_executor_job(self._device.turn_on)
            await self._wait_for_on("color")

            await self.hass.async_add_executor_job(self._device.set_hs_color, hs)

            self.async_write_ha_state()
            return

        # SOLO ACCENSIONE
        if not kwargs:
            await self.hass.async_add_executor_job(self._device.turn_on)
            self.async_write_ha_state()
            return

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self._device.turn_off)

        self._pending_brightness = None
        self._pending_hs_color = None

        self.async_write_ha_state()

    # REFRESH INIZIALE DOPO RIAVVIO HA
    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Allinea subito la UI al colore reale ETI/Domo
        self.async_write_ha_state()

    # BRIGHTNESS GETTER
    @property
    def brightness(self):

        real = getattr(self._device, "brightness", None)

        if self._pending_brightness is not None:

            pending_255 = round(self._pending_brightness * 255 / 100)
            real_255 = None
            if real is not None:
                real_255 = round(real * 255 / 100)

            if real_255 == pending_255:
                self._pending_brightness = None
                return real_255

            return pending_255

        if real is None or not getattr(self._device, "support_brightness", False):
            return None

        val = round(real * 255 / 100)
        return val

    # COLOR GETTER
    @property
    def hs_color(self):

        real = getattr(self._device, "hs_color", None)

        if self._pending_hs_color is not None:

            if real == list(self._pending_hs_color):
                val = tuple(real)
                self._pending_hs_color = None
                return val

            return tuple(self._pending_hs_color)

        if real is not None:
            return tuple(real)

        return None

    @property
    def color_mode(self):
        return next(iter(self._attr_supported_color_modes))

