"""Supporto per le coperture CAME."""
import logging
from typing import List

from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.cover import (
    ENTITY_ID_FORMAT,
    CoverEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .pycame.came_manager import CameManager
from .pycame.devices import CameDevice
from .pycame.devices.came_opening import (
    OPENING_STATE_OPEN,
    OPENING_STATE_CLOSE,
    OPENING_STATE_STOP,
)

from .const import CONF_MANAGER, CONF_PENDING, DOMAIN, SIGNAL_DISCOVERY_NEW
from .entity import CameEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Configura i dispositivi di apertura CAME tramite scoperta dinamica."""

    async def async_discover_sensor(dev_ids):
        """Scopri e aggiungi dispositivi di apertura CAME trovati."""
        if not dev_ids:
            return

        entities = await hass.async_add_executor_job(_setup_entities, hass, dev_ids)
        async_add_entities(entities)

    async_dispatcher_connect(
        hass, SIGNAL_DISCOVERY_NEW.format(COVER_DOMAIN), async_discover_sensor
    )

    devices_ids = hass.data[DOMAIN][CONF_PENDING].pop(COVER_DOMAIN, [])
    await async_discover_sensor(devices_ids)

def _setup_entities(hass, dev_ids: List[str]):
    """Configura i dispositivi di apertura CAME."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    entities = []
    for dev_id in dev_ids:
        device = manager.get_device_by_id(dev_id)
        if device is None:
            continue
        entities.append(CameCoverEntity(device))
    return entities


class CameCoverEntity(CameEntity, CoverEntity):
    """Entità del dispositivo di apertura CAME."""

    def __init__(self, device: CameDevice):
        """Inizializza l'entità del dispositivo di apertura CAME."""
        super().__init__(device)
        self.entity_id = ENTITY_ID_FORMAT.format(self.unique_id)
        self._last_command = None  # "open" o "close"
        self._attr_assumed_state = True  # Nessun feedback, assumiamo lo stato

    @property
    def is_closed(self):
        """Restituisce True se la copertura è chiusa."""
        if self._device.state == OPENING_STATE_OPEN:
            return False
        elif self._device.state == OPENING_STATE_CLOSE:
            return True
        elif self._device.state == OPENING_STATE_STOP:
            if self._last_command == "open":
                return False
            elif self._last_command == "close":
                return True
        return None  # Stato sconosciuto

    @property
    def is_opened(self):
        """Restituisce True se la copertura è aperta."""
        if self._device.state == OPENING_STATE_CLOSE:
            return False
        elif self._device.state == OPENING_STATE_OPEN:
            return True
        elif self._device.state == OPENING_STATE_STOP:
            if self._last_command == "close":
                return False
            elif self._last_command == "open":
                return True
        return None  # Stato sconosciuto

    @property
    def is_opening(self) -> bool:
        """Restituisce True se la copertura è attualmente in apertura."""
        return self._device.state == OPENING_STATE_OPEN

    @property
    def is_closing(self) -> bool:
        """Restituisce True se la copertura è attualmente in chiusura."""
        return self._device.state == OPENING_STATE_CLOSE

    def open_cover(self):
        """Apri la copertura."""
        _LOGGER.debug("Apertura della copertura %s", self.entity_id)
        self._last_command = "open"
        try:
            self._device.open()
        except Exception as e:
            _LOGGER.error("Errore durante l'apertura della copertura %s: %s", self.entity_id, e)

    def close_cover(self):
        """Chiudi la copertura."""
        _LOGGER.debug("Chiusura della copertura %s", self.entity_id)
        self._last_command = "close"
        try:
            self._device.close()
        except Exception as e:
            _LOGGER.error("Errore durante la chiusura della copertura %s: %s", self.entity_id, e)

    def stop_cover(self):
        """Ferma la copertura."""
        _LOGGER.debug("Fermare la copertura %s", self.entity_id)
        try:
            self._device.stop()
        except Exception as e:
            _LOGGER.error("Errore durante il fermo della copertura %s: %s", self.entity_id, e)
