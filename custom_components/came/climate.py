"""Support for the CAME climate devices."""

import logging
from typing import Optional

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import (
    ENTITY_ID_FORMAT,
    HVACMode,
    ClimateEntity,
    ClimateEntityFeature,
)
from homeassistant.components.climate.const import HVACAction
from pycame.devices.came_thermo import (
    THERMO_FAN_SPEED_SLOW,
    THERMO_FAN_SPEED_MEDIUM,
    THERMO_FAN_SPEED_FAST,
    THERMO_FAN_SPEED_AUTO,
    THERMO_MODE_OFF,
)


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from pycame.came_manager import CameManager
from pycame.devices import CameDevice
from pycame.devices.came_thermo import (
    THERMO_DEHUMIDIFIER_ON,
    THERMO_MODE_AUTO,
    THERMO_MODE_JOLLY,
    THERMO_MODE_MANUAL,
    THERMO_MODE_OFF,
    THERMO_SEASON_OFF,
    THERMO_SEASON_SUMMER,
    THERMO_SEASON_WINTER,
)

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity

_LOGGER = logging.getLogger(__name__)

CAME_MODE_TO_HA = {
    THERMO_MODE_OFF: HVACMode.OFF,
    THERMO_MODE_AUTO: HVACMode.AUTO,
    THERMO_MODE_JOLLY: HVACMode.AUTO,
}

CAME_SEASON_TO_HA = {
    THERMO_SEASON_OFF: HVACMode.OFF,
    THERMO_SEASON_WINTER: HVACMode.HEAT,
    THERMO_SEASON_SUMMER: HVACMode.COOL,
}


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    async def async_discover_sensor(dev_ids):
        if not dev_ids:
            return
        entities = await hass.async_add_executor_job(_setup_entities, hass, dev_ids)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, SIGNAL_DISCOVERY_NEW.format(CLIMATE_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(CLIMATE_DOMAIN, [])
    await async_discover_sensor(devices_ids)


def _setup_entities(hass, dev_ids):
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue

        if getattr(device, "support_fan_speed", False):
            _LOGGER.info(
                "💨 Fan coil rilevato: %s → entità CameFancoilClimateEntity",
                device.name,
            )
            entities.append(CameFancoilClimateEntity(device))
        else:
            _LOGGER.info(
                "🌡️ Termostato rilevato: %s → entità CameClimateEntity", device.name
            )
            entities.append(CameClimateEntity(device))
    return entities


class CameClimateEntity(CameEntity, ClimateEntity):
    def __init__(self, device: CameDevice):
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

        self._attr_supported_features = (
            (
                ClimateEntityFeature.TARGET_TEMPERATURE
                if device.support_target_temperature
                else 0
            )
            | (
                ClimateEntityFeature.TARGET_HUMIDITY
                if device.support_target_humidity
                else 0
            )
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

        self._attr_target_temperature_step = PRECISION_TENTHS
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> Optional[float]:
        return self._device.current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        return self._device.target_temperature

    @property
    def target_humidity(self) -> Optional[int]:
        return self._device.target_humidity

    @property
    def hvac_mode(self):
        """Return current HVAC mode set by user (not current action)."""

        if self._device.mode in CAME_MODE_TO_HA:
            return CAME_MODE_TO_HA[self._device.mode]
        if self._device.dehumidifier_state == THERMO_DEHUMIDIFIER_ON:
            return HVACMode.DRY
        return CAME_SEASON_TO_HA.get(self._device.season, HVACMode.OFF)

    @property
    def hvac_action(self) -> Optional[HVACAction]:
        """Return the current running hvac operation for thermostats."""
        _LOGGER.debug(
            "🛠️ HVAC Action - Stato attuale: state=%s, active=%s, season=%s",
            self._device.state,
            getattr(self._device, "active", "N/A"),
            self._device.season,
        )

        if self._device.mode == THERMO_MODE_OFF:
            return HVACAction.OFF

        if self._device.state == 1:
            if self._device.season == THERMO_SEASON_WINTER:
                return HVACAction.HEATING
            elif self._device.season == THERMO_SEASON_SUMMER:
                return HVACAction.COOLING
            return HVACAction.HEATING  # fallback in caso di stagione non definita

        return HVACAction.IDLE

    @property
    def hvac_modes(self):
        ops = [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT, HVACMode.COOL]
        if self._device.support_target_humidity:
            ops.append(HVACMode.DRY)
        return ops

    def set_temperature(self, **kwargs) -> None:
        if ATTR_TEMPERATURE in kwargs:
            self._device.set_target_temperature(kwargs[ATTR_TEMPERATURE])

    def set_hvac_mode(self, hvac_mode: str) -> None:
        if hvac_mode == HVACMode.OFF:
            self._device.zone_config(mode=THERMO_MODE_OFF)
        elif hvac_mode == HVACMode.HEAT:
            self._device.zone_config(
                mode=THERMO_MODE_MANUAL, season=THERMO_SEASON_WINTER
            )
        elif hvac_mode == HVACMode.COOL:
            self._device.zone_config(
                mode=THERMO_MODE_MANUAL, season=THERMO_SEASON_SUMMER
            )
        elif hvac_mode == HVACMode.AUTO:
            self._device.zone_config(mode=THERMO_MODE_AUTO)
        else:
            self._device.zone_config(mode=THERMO_MODE_AUTO)


class CameFancoilClimateEntity(CameClimateEntity):
    def __init__(self, device: CameDevice):
        super().__init__(device)
        self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
        self._attr_fan_modes = ["auto", "low", "medium", "high"]
        _LOGGER.info(
            "🎛️ Fan coil %s: modalità disponibili %s", device.name, self._attr_fan_modes
        )

    @property
    def hvac_action(self) -> Optional[HVACAction]:
        """Return the current running HVAC action for fan coil."""
        if self._device.mode == THERMO_MODE_OFF:
            return HVACAction.OFF
        if self._device.fan_speed in [
            THERMO_FAN_SPEED_SLOW,
            THERMO_FAN_SPEED_MEDIUM,
            THERMO_FAN_SPEED_FAST,
            THERMO_FAN_SPEED_AUTO,
        ]:
            return HVACAction.FAN
        return HVACAction.IDLE

    @property
    def fan_mode(self) -> Optional[str]:
        # Legge la velocità attuale dal dispositivo
        fan_mode = getattr(self._device, "fan_mode", None)
        if fan_mode is not None:
            # Normalizza in minuscolo per Home Assistant
            return fan_mode.lower()
        return None

    def set_fan_mode(self, fan_mode: str) -> None:
        _LOGGER.info("🔁 Cambio velocità ventilatore: richiesta %s", fan_mode)
        if fan_mode in self._attr_fan_modes:
            if hasattr(self._device, "set_fan_speed"):
                # Invia al dispositivo il fan_mode in MAIUSCOLO (perché CAME usa MAIUSCOLO)
                self._device.set_fan_speed(fan_mode.upper())
            else:
                _LOGGER.warning(
                    "⛔ Il dispositivo %s NON supporta set_fan_speed", self._device.name
                )
        else:
            _LOGGER.warning("🚫 Modalità ventilatore non valida: %s", fan_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode asynchronously."""
        _LOGGER.info("🔁 [ASYNC] Cambio velocità ventilatore: richiesta %s", fan_mode)
        await self.hass.async_add_executor_job(self.set_fan_mode, fan_mode)
        self.async_write_ha_state()
