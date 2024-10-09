"""Support for the CAME climate devices."""

from typing import Optional

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import (
    ENTITY_ID_FORMAT,
    HVACMode,  # Sostituisce le vecchie costanti HVAC_MODE_*
    ClimateEntity,
    ClimateEntityFeature,  # Per sostituire SUPPORT_* vecchie costanti
)
from homeassistant.components.climate.const import (
    HVACMode,  # Nuovo: sostituisce HVAC_MODE_*
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    UnitOfTemperature,  # Sostituisce TEMP_CELSIUS
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

# Vecchie costanti HVAC_MODE sostituite con le nuove HVACMode.*
CAME_MODE_TO_HA = {
    THERMO_MODE_OFF: HVACMode.OFF,  # HVAC_MODE_OFF deprecato
    THERMO_MODE_AUTO: HVACMode.AUTO,  # HVAC_MODE_AUTO deprecato
    THERMO_MODE_JOLLY: HVACMode.AUTO,  # HVAC_MODE_AUTO deprecato
}

# Vecchie costanti HVAC_MODE sostituite con le nuove HVACMode.*
CAME_SEASON_TO_HA = {
    THERMO_SEASON_OFF: HVACMode.OFF,  # HVAC_MODE_OFF deprecato
    THERMO_SEASON_WINTER: HVACMode.HEAT,  # HVAC_MODE_HEAT deprecato
    THERMO_SEASON_SUMMER: HVACMode.COOL,  # HVAC_MODE_COOL deprecato
}


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up CAME sensors dynamically through discovery."""

    async def async_discover_sensor(dev_ids):
        """Discover and add a discovered CAME sensor."""
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
    """Set up CAME Climate device."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue
        entities.append(CameClimateEntity(device))
    return entities


class CameClimateEntity(CameEntity, ClimateEntity):
    """CAME climate device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME climate device entity."""
        super().__init__(device)

        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

        # Modificato: Sostituite le vecchie costanti SUPPORT_* con ClimateEntityFeature.*
        self._attr_supported_features = (
            (
                ClimateEntityFeature.TARGET_TEMPERATURE  # Sostituisce SUPPORT_TARGET_TEMPERATURE
                if self._device.support_target_temperature
                else 0
            )
            | (ClimateEntityFeature.TARGET_HUMIDITY  # Sostituisce SUPPORT_TARGET_HUMIDITY
               if self._device.support_target_humidity else 0)
            | (ClimateEntityFeature.FAN_MODE  # Sostituisce SUPPORT_FAN_MODE
               if self._device.support_fan_speed else 0)
        )
        # Modificato: Sostituito PRECISION_TENTHS con il nuovo attributo
        self._attr_target_temperature_step = PRECISION_TENTHS
        # Modificato: Sostituito TEMP_CELSIUS con UnitOfTemperature.CELSIUS
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self._device.current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        return self._device.target_temperature

    @property
    def target_humidity(self) -> Optional[int]:
        """Return the humidity we try to reach."""
        return self._device.target_humidity

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        if not self._device.state:
            # Modificato: Sostituito HVAC_MODE_OFF con HVACMode.OFF
            return HVACMode.OFF
        # else State = ON

        if self._device.mode in CAME_MODE_TO_HA:
            return CAME_MODE_TO_HA[self._device.mode]
        # else Mode = Manual

        if self._device.dehumidifier_state == THERMO_DEHUMIDIFIER_ON:
            # Modificato: Sostituito HVAC_MODE_DRY con HVACMode.DRY
            return HVACMode.DRY

        return CAME_SEASON_TO_HA[self._device.season]

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        # Modificato: Sostituite le vecchie costanti HVAC_MODE_* con HVACMode.*
        operations = [
            HVACMode.OFF,  # Sostituisce HVAC_MODE_OFF
            HVACMode.AUTO,  # Sostituisce HVAC_MODE_AUTO
            HVACMode.HEAT,  # Sostituisce HVAC_MODE_HEAT
            HVACMode.COOL,  # Sostituisce HVAC_MODE_COOL
        ]
        if self._device.support_target_humidity:
            # Modificato: Sostituito HVAC_MODE_DRY con HVACMode.DRY
            operations.append(HVACMode.DRY)
        return operations

    def set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            self._device.set_target_temperature(kwargs[ATTR_TEMPERATURE])

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        # Modificato: Sostituito HVAC_MODE_* con HVACMode.*
        if hvac_mode == HVACMode.OFF:  # Sostituisce HVAC_MODE_OFF
            self._device.zone_config(mode=THERMO_MODE_OFF)

        elif hvac_mode == HVACMode.HEAT:  # Sostituisce HVAC_MODE_HEAT
            self._device.zone_config(
                mode=THERMO_MODE_MANUAL, season=THERMO_SEASON_WINTER
            )
        elif hvac_mode == HVACMode.COOL:  # Sostituisce HVAC_MODE_COOL
            self._device.zone_config(
                mode=THERMO_MODE_MANUAL, season=THERMO_SEASON_SUMMER
            )
        # pylint: disable=fixme
        # todo: Set up dehumidifier when hvac_mode == HVACMode.DRY

        else:
            # Modificato: Sostituito HVAC_MODE_AUTO con HVACMode.AUTO
            self._device.zone_config(mode=THERMO_MODE_AUTO)
