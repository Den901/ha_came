"""
The CAME Integration Component.

For more details about this platform, please refer to the documentation at
https://github.com/lrzdeveloper/ha-came
"""
import asyncio
import logging
import threading
from time import sleep
from typing import List

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_ENTITIES,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send, dispatcher_send
from homeassistant.helpers.typing import ConfigType
from pycame.came_manager import CameManager
from pycame.devices import CameDevice
from pycame.exceptions import ETIDomoConnectionError, ETIDomoConnectionTimeoutError

from .const import (
    CONF_CAME_LISTENER,
    CONF_ENTRY_IS_SETUP,
    CONF_MANAGER,
    CONF_PENDING,
    DATA_YAML,
    DOMAIN,
    SERVICE_FORCE_UPDATE,
    SERVICE_PULL_DEVICES,
    SIGNAL_DELETE_ENTITY,
    SIGNAL_DISCOVERY_NEW,
    SIGNAL_UPDATE_ENTITY,
    STARTUP_MESSAGE,
)

_LOGGER = logging.getLogger(__name__)

ACCOUNT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_TOKEN): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema({DOMAIN: ACCOUNT_SCHEMA}, extra=vol.ALLOW_EXTRA)


CAME_TYPE_TO_HA = {
    "Light": LIGHT,
    "Thermostat": CLIMATE,
    "Analog Sensor": SENSOR,
}


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up this integration using YAML."""
    # Print startup message
    if DOMAIN not in hass.data:
        _LOGGER.info(STARTUP_MESSAGE)
        hass.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    hass.data[DATA_YAML] = config[DOMAIN]
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data={}
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    if entry.source == SOURCE_IMPORT:
        config = hass.data[DATA_YAML]
    else:
        config = entry.data.copy()
        config.update(entry.options)

    manager = CameManager(
        config.get(CONF_HOST),
        config.get(CONF_USERNAME),
        config.get(CONF_PASSWORD),
        config.get(CONF_TOKEN),
    )

    def initial_update():
        manager.get_all_floors()
        manager.get_all_rooms()
        return manager.get_all_devices()

    try:
        devices = await hass.async_add_executor_job(initial_update)
    except ETIDomoConnectionTimeoutError as exc:
        raise ConfigEntryNotReady from exc

    thread = threading.Thread(
        target=_came_update_listener, args=(hass, manager), daemon=True
    )

    hass.data[DOMAIN] = {
        CONF_MANAGER: manager,
        CONF_ENTITIES: {},
        CONF_ENTRY_IS_SETUP: set(),
        CONF_PENDING: {},
        CONF_CAME_LISTENER: thread,
    }

    thread.start()

    async def async_load_devices(devices: List[CameDevice]):
        """Load new devices."""
        dev_types = {}
        for device in devices:
            if (
                device.type in CAME_TYPE_TO_HA
                and device.unique_id not in hass.data[DOMAIN][CONF_ENTITIES]
            ):
                ha_type = CAME_TYPE_TO_HA[device.type]
                dev_types.setdefault(ha_type, [])
                dev_types[ha_type].append(device.unique_id)
                hass.data[DOMAIN][CONF_ENTITIES][device.unique_id] = None

        for ha_type, dev_ids in dev_types.items():
            config_entries_key = f"{ha_type}.{DOMAIN}"
            if config_entries_key not in hass.data[DOMAIN][CONF_ENTRY_IS_SETUP]:
                hass.data[DOMAIN][CONF_PENDING][ha_type] = dev_ids
                hass.async_create_task(
                    hass.config_entries.async_forward_entry_setup(entry, ha_type)
                )
                hass.data[DOMAIN][CONF_ENTRY_IS_SETUP].add(config_entries_key)
            else:
                async_dispatcher_send(
                    hass, SIGNAL_DISCOVERY_NEW.format(ha_type), dev_ids
                )

    await async_load_devices(devices)

    # pylint: disable=unused-argument
    async def async_update_devices(event_time):
        """Pull new devices list from server."""
        _LOGGER.debug("Update devices")

        # Add new discover device
        devices = await hass.async_add_executor_job(manager.get_all_devices)
        await async_load_devices(devices)

        # Delete not exist device
        newlist_ids = []
        for device in devices:
            newlist_ids.append(device.unique_id)
        for dev_id in list(hass.data[DOMAIN][CONF_ENTITIES]):
            if dev_id not in newlist_ids:
                async_dispatcher_send(hass, SIGNAL_DELETE_ENTITY, dev_id)
                hass.data[DOMAIN][CONF_ENTITIES].pop(dev_id)

    hass.services.async_register(DOMAIN, SERVICE_PULL_DEVICES, async_update_devices)

    async def async_force_update(call):
        """Force all devices to pull data."""
        async_dispatcher_send(hass, SIGNAL_UPDATE_ENTITY)

    hass.services.async_register(DOMAIN, SERVICE_FORCE_UPDATE, async_force_update)

    return True


def _came_update_listener(hass: HomeAssistant, manager: CameManager):
    """Run infinity loop with devices status update requests."""
    while hass.data.get(DOMAIN):
        try:
            if manager.status_update():
                _LOGGER.debug("Received devices status update.")
                dispatcher_send(hass, SIGNAL_UPDATE_ENTITY)
        except ETIDomoConnectionError:
            _LOGGER.debug("Server goes offline. Reconnecting...")
            sleep(1)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unloading the CAME platforms."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(
                    entry, platform.split(".", 1)[0]
                )
                for platform in hass.data[DOMAIN][CONF_ENTRY_IS_SETUP]
            ]
        )
    )
    if unload_ok:
        hass.services.async_remove(DOMAIN, SERVICE_FORCE_UPDATE)
        hass.services.async_remove(DOMAIN, SERVICE_PULL_DEVICES)

        thread = hass.data[DOMAIN][CONF_CAME_LISTENER]  # type: threading.Thread

        hass.data.pop(DOMAIN)

        thread.join()

    return unload_ok
