"""Support for the CAME analog sensors."""

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_ENERGY_STORAGE,
    DEVICE_CLASS_VOLTAGE,
    DEVICE_CLASS_POWER_FACTOR,
    DEVICE_CLASS_POWER,
    PERCENTAGE,

)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import StateType
from homeassistant.util.unit_system import PRESSURE_UNITS, TEMPERATURE_UNITS, ENERGY_UNITS #da vedere
from pycame.came_manager import CameManager
from pycame.devices import CameDevice

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up CAME analog sensors dynamically through discovery."""

    async def async_discover_sensor(dev_ids):
        """Discover and add a discovered CAME sensor."""
        if not dev_ids:
            return

        entities = await hass.async_add_executor_job(_setup_entities, hass, dev_ids)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, SIGNAL_DISCOVERY_NEW.format(SENSOR_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(SENSOR_DOMAIN, [])
    await async_discover_sensor(devices_ids)


def _setup_entities(hass, dev_ids):
    """Set up CAME sensor device."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue
        if 'meter_type' in device.data:
            entities.append(CameEnergySensorEntity(device))
        else:
            entities.append(CameSensorEntity(device))
    return entities


class CameSensorEntity(CameEntity, SensorEntity):
    """CAME analog sensor device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME analog sensor device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

        self._attr_state_class = STATE_CLASS_MEASUREMENT
        self._attr_device_class = self._device.device_class or (
            DEVICE_CLASS_TEMPERATURE
            if self._device.unit_of_measurement in TEMPERATURE_UNITS #da vedere per energy
            else DEVICE_CLASS_HUMIDITY
            if self._device.unit_of_measurement == PERCENTAGE
            else DEVICE_CLASS_PRESSURE
            if self._device.unit_of_measurement in PRESSURE_UNITS
            else None
        )
        self._attr_unit_of_measurement = self._device.unit_of_measurement

class CameEnergySensorEntity(CameEntity, SensorEntity):
    """CAME energy sensor device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME energy sensor device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

        self._attr_state_class = STATE_CLASS_MEASUREMENT

        # Based on the meter_type, set the appropriate device class.
        meter_type = device.data.get("meter_type", None)
        if meter_type == 1:  # Electricity
            self._attr_device_class = DEVICE_CLASS_POWER
    #    elif meter_type == 2:  # Water
            # Set an appropriate device class for Water, if one exists in HA.
    #    elif meter_type == 3:  # Gas
            # Similarly, set a class for Gas.
    #    elif meter_type == 4:  # Heat
            # And for Heat.
        else: None # Other
            # Set a default or other class for 'Other' types.

        # Now, based on the unit from the device data, set the unit of measurement.
        self._attr_unit_of_measurement = device.data.get("unit", None)


    @property
    def state(self) -> StateType:
        """Return the state of the entity."""
        return self._device.state
