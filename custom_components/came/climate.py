"""Support for the CAME climate devices."""

import logging
from typing import Optional, Any, Dict

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import (
    ENTITY_ID_FORMAT,
    HVACMode,
    ClimateEntity,
    ClimateEntityFeature,
)
from homeassistant.components.climate.const import HVACAction
from .pycame.devices.came_thermo import (
    THERMO_FAN_SPEED_SLOW,
    THERMO_FAN_SPEED_MEDIUM,
    THERMO_FAN_SPEED_FAST,
    THERMO_FAN_SPEED_AUTO,
    THERMO_DEHUMIDIFIER_ON,
    THERMO_MODE_AUTO,
    THERMO_MODE_JOLLY,
    THERMO_MODE_MANUAL,
    THERMO_MODE_OFF,
    THERMO_SEASON_OFF,
    THERMO_SEASON_SUMMER,
    THERMO_SEASON_WINTER,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .pycame.came_manager import CameManager
from .pycame.devices import CameDevice

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
        self._attr_target_temperature_step = PRECISION_TENTHS
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        self._attr_supported_features = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        if device.support_target_humidity:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_HUMIDITY

    @property
    def supported_features(self) -> ClimateEntityFeature:
        feat = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | (ClimateEntityFeature.TARGET_HUMIDITY if self._device.support_target_humidity else 0)
        )
        # cursore temperatura SOLO in HEAT / COOL (valido per tutti)
        if self.hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
            feat |= ClimateEntityFeature.TARGET_TEMPERATURE

        # FAN_MODE solo per i fan-coil (hanno _attr_fan_modes) e solo fuori OFF
        if hasattr(self, "_attr_fan_modes") and self.hvac_mode != HVACMode.OFF:
            feat |= ClimateEntityFeature.FAN_MODE
        return feat
        
    @property
    def current_temperature(self) -> Optional[float]:
        return self._device.current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        if self._device.mode == THERMO_MODE_AUTO:
            reason = self._device.reason
            if reason is None or reason not in (1, 2, 3):
                return None
            idx = reason - 1
            val = [self._device.t1, self._device.t2, self._device.t3][idx]
            return val / 10 if val is not None else None
        return self._device.target_temperature

    @property
    def target_humidity(self) -> Optional[int]:
        return self._device.target_humidity

    @property
    def hvac_mode(self):
        if self._device.mode in CAME_MODE_TO_HA:
            return CAME_MODE_TO_HA[self._device.mode]
        if self._device.dehumidifier_state == THERMO_DEHUMIDIFIER_ON:
            return HVACMode.DRY
        return CAME_SEASON_TO_HA.get(self._device.season, HVACMode.OFF)

    @property
    def hvac_action(self) -> Optional[HVACAction]:
        if self._device.mode == THERMO_MODE_OFF:
            return HVACAction.OFF
        if self._device.state == 1:
            if self._device.season == THERMO_SEASON_WINTER:
                return HVACAction.HEATING
            elif self._device.season == THERMO_SEASON_SUMMER:
                return HVACAction.COOLING
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def hvac_modes(self) -> list[HVACMode]:
        if self._device.season == THERMO_SEASON_OFF:
            return []
        base = [HVACMode.OFF, HVACMode.AUTO]
        if self._device.season == THERMO_SEASON_WINTER:
            base.append(HVACMode.HEAT)
        elif self._device.season == THERMO_SEASON_SUMMER:
            base.append(HVACMode.COOL)
        if self._device.support_target_humidity:
            base.append(HVACMode.DRY)
        return base

    def set_temperature(self, **kwargs) -> None:
        if self._device.mode == THERMO_MODE_AUTO:
            _LOGGER.info("Richiesta temperatura ignorata: %s è in modalità AUTO", self.name)
            return
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._device.set_target_temperature(temp)

    def set_hvac_mode(self, hvac_mode: str) -> None:
        if hvac_mode == HVACMode.OFF:
            self._device.zone_config(mode=THERMO_MODE_OFF)
        elif hvac_mode == HVACMode.HEAT:
            self._device.zone_config(mode=THERMO_MODE_MANUAL, season=THERMO_SEASON_WINTER)
        elif hvac_mode == HVACMode.COOL:
            self._device.zone_config(mode=THERMO_MODE_MANUAL, season=THERMO_SEASON_SUMMER)
        elif hvac_mode == HVACMode.AUTO:
            self._device.zone_config(mode=THERMO_MODE_AUTO)
        else:
            self._device.zone_config(mode=THERMO_MODE_AUTO)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        dev = self._device
        return {
            "act_id": dev.act_id,
            "floor_ind": dev.floor_ind,
            "room_ind": dev.room_ind,
            "status": dev.status,
            "mode": dev.mode,
            "fan_speed": dev.fan_speed,
            "set_point": dev.set_point / 10 if dev.set_point is not None else None,
            "season": dev.season,
            "antifreeze": dev.antifreeze / 10 if dev.antifreeze is not None else None,
            "t1": dev.t1 / 10 if dev.t1 is not None else None,
            "t2": dev.t2 / 10 if dev.t2 is not None else None,
            "t3": dev.t3 / 10 if dev.t3 is not None else None,
            "reason": dev.reason,
            "f3a": dev.f3a,
            "thermo_algo": dev.thermo_algo,
        }


class CameFancoilClimateEntity(CameClimateEntity):
    def __init__(self, device: CameDevice):
        super().__init__(device)
        self._attr_fan_modes = ["auto", "low", "medium", "high"]
        _LOGGER.info("🎛️ Fan coil %s: modalità disponibili %s", device.name, self._attr_fan_modes)

    @property
    def hvac_action(self) -> Optional[HVACAction]:
        if self._device.mode == THERMO_MODE_OFF:
            return HVACAction.OFF
        if self._device.state == 0:
            return HVACAction.IDLE
        if self._device.season == THERMO_SEASON_WINTER:
            return HVACAction.HEATING
        if self._device.season == THERMO_SEASON_SUMMER:
            return HVACAction.COOLING
        return HVACAction.IDLE

    @property
    def fan_mode(self) -> Optional[str]:
        if self.hvac_mode == HVACMode.OFF:
            return None
        return self._device.fan_mode_ha

    def set_fan_mode(self, fan_mode: str) -> None:
        if self.hvac_mode == HVACMode.OFF:
            _LOGGER.debug("Ignoro set_fan_mode: termostato OFF")
            return
        self._device.set_fan_mode_ha(fan_mode)
        
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        #_LOGGER.info("🔁 [ASYNC] Cambio velocità ventilatore: richiesta %s", fan_mode)
        await self.hass.async_add_executor_job(self.set_fan_mode, fan_mode)
        self.async_write_ha_state()
