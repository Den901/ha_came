"""Support for the CAME covers."""
import logging
from typing import List

from datetime import timedelta
from datetime import datetime, timezone
import asyncio

from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.cover import (
    ENTITY_ID_FORMAT,
    CoverEntity,
    ATTR_POSITION
)

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from .pycame.came_manager import CameManager
from .pycame.devices import CameDevice
from .pycame.devices.came_opening import OPENING_STATE_STOPED, OPENING_STATE_OPENNING, OPENING_STATE_CLOSING

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .const import COVER_CLOSING_TRAVEL_DURATION, COVER_OPENING_TRAVEL_DURATION
from .entity import CameEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up CAME openings devices dynamically through discovery."""
    from .const import DOMAIN, CONF_MANAGER
    manager = hass.data[DOMAIN][CONF_MANAGER]

    async def async_discover_sensor(manager, hass, dev_ids):
        devices = []
        for dev_id in dev_ids:
            device = await manager.get_device_by_id(dev_id)
            if device:
                devices.append(device)
        entities = await hass.async_add_executor_job(_setup_entities, hass, devices)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, SIGNAL_DISCOVERY_NEW.format(COVER_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(COVER_DOMAIN, [])
    await async_discover_sensor(manager, hass, devices_ids)


def _setup_entities(hass, devices):
    entities = []
    for device in devices:
        entities.append(CameCoverEntity(device))
    return entities


class CameCoverEntity(CameEntity, CoverEntity):
    """CAME opening device entity."""

    def __init__(self, device: CameDevice):
        """Init CAME opening device entity."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)
        self._attr_last_state = OPENING_STATE_STOPED
        self._attr_real_postion = 100.0
        self._attr_target_postion = 100.0
        self._attr_current_direction = 0 # 0: stop, 1: opening, -1: closing
        self._attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION

    @property
    def assumed_state(self):
        """Return True because covers can be stopped midway."""
        return True

    @property
    def is_closed(self):
        """Return something."""
        return self._attr_real_postion <= 5

    @property
    def is_closing(self):
        """Return true if the cover is closing."""
        return self._device.state == OPENING_STATE_CLOSING

    @property
    def is_opening(self):
        """Return true if the cover is openning."""
        return self._device.state == OPENING_STATE_OPENNING
    
    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        _LOGGER.debug("Set cover position")
        if ATTR_POSITION in kwargs:
            _LOGGER.debug("Set cover position %s to %s", self.entity_id, kwargs[ATTR_POSITION])
            self._attr_target_postion = kwargs[ATTR_POSITION]
            
            self.schedule_update_ha_state(True)
            
            await self.start_movement()
            
        
        
    @property
    def current_cover_position(self):
        """Return estimated something."""
        return round(self._attr_real_postion)

    async def async_stop_cover(self):
        """Instruct the cover to stop."""
        _LOGGER.debug("Stop the cover %s", self.entity_id)
        self._attr_last_state = OPENING_STATE_STOPED
        self._attr_current_direction = 0
        await self._device.stop()
        self.stop_auto_updater()
        

    async def async_open_cover(self):
        """Open the cover."""
        _LOGGER.debug("Open the cover %s", self.entity_id)
        self._attr_target_postion = 100.0
        self._attr_last_state = OPENING_STATE_OPENNING
        await self.start_movement()

    async def async_close_cover(self):
        """Instruct the cover to close."""
        _LOGGER.debug("Stop the cover %s", self.entity_id)
        self._attr_target_postion = 0.0
        self._attr_last_state = OPENING_STATE_CLOSING
        await self.start_movement()

    async def start_movement(self):
        """Start the movement of the cover."""
        
        self._last_known_position_timestamp = datetime.now(timezone.utc)
        _LOGGER.debug("Start movement of the cover %s", self.entity_id)
        if self._attr_target_postion == self._attr_real_postion:
            _LOGGER.debug("Cover %s is already at the target position", self.entity_id)
            return
        if self._attr_target_postion > self._attr_real_postion:
            self._attr_current_direction = 1
            await self._device.open()
        elif self._attr_target_postion < self._attr_real_postion:
            self._attr_current_direction = -1
            await self._device.close()
            
        interval = timedelta(seconds=0.1)
        
        self._unsubscribe_auto_updater = async_track_time_interval(
                self.hass, self.auto_updater_hook, interval)
    
    
    @callback
    async def auto_updater_hook(self, now):
        """Call for the autoupdater."""
        _LOGGER.debug('auto_updater_hook')
        
        newPos = self._attr_real_postion
        duration = (now - self._last_known_position_timestamp).total_seconds()
        
        _LOGGER.debug("duration: %s", duration)
        
        if(self._attr_current_direction == 1):
            newPos = self._attr_real_postion + (duration * 100 / COVER_OPENING_TRAVEL_DURATION) 
        elif(self._attr_current_direction == -1):
            newPos = self._attr_real_postion - (duration * 100 / COVER_CLOSING_TRAVEL_DURATION)
        
        if( newPos < 0):
            newPos = 0
        elif( newPos > 100):
            newPos = 100
            
        _LOGGER.debug("newPos: %s", newPos)
        _LOGGER.debug("current direction: %s", self._attr_current_direction)
        _LOGGER.debug("target position: %s", self._attr_target_postion)
            
        self._attr_real_postion = newPos
        self._last_known_position_timestamp = now
        
        
        if(self._attr_current_direction == -1):
            if self._attr_real_postion <= self._attr_target_postion:
                _LOGGER.debug('auto_updater_hook :: cover reached target position')
                self._attr_current_direction = 0
                if(self._attr_target_postion != 0):
                    await self._device.stop()
                self.stop_auto_updater()
                
                await asyncio.sleep(1) # Allow some time for the device to process the command
                
                self.schedule_update_ha_state(True)
        elif(self._attr_current_direction == 1):
            if self._attr_real_postion >= self._attr_target_postion:
                _LOGGER.debug('auto_updater_hook :: cover reached target position')
                self._attr_current_direction = 0
                if(self._attr_target_postion != 100):
                    await self._device.stop()   
                self.stop_auto_updater()
                
                await asyncio.sleep(1) # Allow some time for the device to process the command
                
                self.schedule_update_ha_state(True)
        else:
            _LOGGER.debug('auto_updater_hook :: cover is stopped')
            self._attr_current_direction = 0
            self.stop_auto_updater()
            
            await asyncio.sleep(1) # Allow some time for the device to process the command
            
            self.schedule_update_ha_state(True)
        
        
        self.async_schedule_update_ha_state()
        
    def stop_auto_updater(self):
        """Stop the autoupdater."""
        _LOGGER.debug('stop_auto_updater')
        if self._unsubscribe_auto_updater is not None:
            self._unsubscribe_auto_updater()
            self._unsubscribe_auto_updater = None

    async def async_update(self):
        """Fetch new state data for this cover from the device."""
        _LOGGER.debug("update called for %s", self.entity_id)
        await self._device.update()