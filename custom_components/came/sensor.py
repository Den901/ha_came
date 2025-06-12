"""Support for the CAME analog sensors."""

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorEntity,
)
from homeassistant.components.sensor import SensorStateClass  # Importa la classe di stato corretta
from homeassistant.config_entries import ConfigEntry  # Aggiungi questa importazione
from homeassistant.const import (
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import StateType
from homeassistant.util.unit_system import PRESSURE_UNITS, TEMPERATURE_UNITS
from .pycame.came_manager import CameManager
from .pycame.devices import CameDevice

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity
# Importa le classi di dispositivo corrette
from homeassistant.components.sensor import SensorDeviceClass  # Aggiungi questo

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
    """Set up CAME analog sensor device."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue
        entities.append(CameSensorEntity(device))
    return entities


class CameSensorEntity(CameEntity, SensorEntity):
    """CAME analog sensor device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME analog sensor device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)

        # Modifica qui per utilizzare SensorStateClass
        self._attr_state_class = SensorStateClass.MEASUREMENT  # Nuovo
        # Sostituisci le vecchie costanti con SensorDeviceClass.*
        self._attr_device_class = self._device.device_class or (
            SensorDeviceClass.TEMPERATURE  # Sostituisci DEVICE_CLASS_TEMPERATURE (deprecato)
            if self._device.unit_of_measurement in TEMPERATURE_UNITS
            else SensorDeviceClass.HUMIDITY  # Sostituisci DEVICE_CLASS_HUMIDITY (deprecato)
            if self._device.unit_of_measurement == PERCENTAGE
            else SensorDeviceClass.PRESSURE  # Sostituisci DEVICE_CLASS_PRESSURE (deprecato)
            if self._device.unit_of_measurement in PRESSURE_UNITS
            else None
        )
        self._attr_unit_of_measurement = self._device.unit_of_measurement

    @property
    def state(self) -> StateType:
        """Return the state of the entity."""
        return self._device.state
