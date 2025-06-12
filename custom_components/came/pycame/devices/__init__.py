"""ETI/Domo devices subpackage."""

import logging
from typing import List

from .pycame.devices.came_analog_sensor import CameAnalogSensor
from .pycame.devices.came_energy_sensor import CameEnergySensor

from .base import CameDevice
from .came_light import CameLight
from .came_thermo import CameThermo
from .came_relay import CameRelay
from .came_opening import CameOpening
from .came_digitalin import CameDigitalIn

_LOGGER = logging.getLogger(__name__)

def get_featured_devices(manager, feature: str) -> List[CameDevice]:
    """Get device implementations for the given feature."""
    devices = []

    if feature == "lights":
        cmd_name = "light_list_req"
        response_name = "light_list_resp"
    elif feature == "openings":
        cmd_name = "openings_list_req"
        response_name = "openings_list_resp"
    elif feature == "relays":
        cmd_name = "relays_list_req"
        response_name = "relays_list_resp"
    elif feature == "thermoregulation":
        cmd_name = "thermo_list_req"
        response_name = "thermo_list_resp"
    elif feature == "energy":
        cmd_name = "meters_list_req"
        response_name = "meters_list_resp"
    elif feature == "digitalin":
        cmd_name = "digitalin_list_req"
        response_name = "digitalin_list_resp"
    else:
        _LOGGER.warning("Unsupported feature type: %s", feature)
        return devices

    cmd = {
        "cmd_name": cmd_name,
        "topologic_scope": "plant",
    }
    response = manager.application_request(cmd, response_name)

    for device_info in response.get("array", []):
        if feature == "lights":
            devices.append(CameLight(manager, device_info))
        elif feature == "openings":
            devices.append(CameOpening(manager, device_info))
        elif feature == "relays":
            devices.append(CameRelay(manager, device_info))
        elif feature == "thermoregulation":
            devices.append(CameThermo(manager, device_info))
        elif feature == "energy":
            devices.append(CameEnergySensor(manager, device_info))
        elif feature == "digitalin":
            devices.append(CameDigitalIn(manager, device_info))

    if feature == "thermoregulation":
        for sensor in ["temperature", "humidity", "pressure"]:
            res = response.get(sensor)
            if res is not None:
                devices.append(
                    CameAnalogSensor(
                        manager, res, "thermo", sensor, device_class=sensor
                    )
                )

    return devices
