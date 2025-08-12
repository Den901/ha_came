"""Python client for ETI/Domo."""

import json
import logging
from typing import List, Optional

import aiohttp
import asyncio

from .const import DEBUG_DEEP, STARTUP_MESSAGE, VERSION
from .devices import get_featured_devices
from .devices.base import CameDevice, DeviceState
from .devices.came_scenarios import ScenarioManager
from .exceptions import (
    ETIDomoConnectionError,
    ETIDomoConnectionTimeoutError,
    ETIDomoError,
)
from .models import Floor, Room
from homeassistant.helpers.dispatcher import async_dispatcher_send

_LOGGER = logging.getLogger(__name__)

_STARTUP = []


class CameManager:
    """Main class for handling connections with an ETI/Domo device."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        token: str,
        hass: Optional["HomeAssistant"] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        """Initialize connection with the ETI/Domo."""
        if not _STARTUP:
            _LOGGER.info(STARTUP_MESSAGE)
            _STARTUP.append(True)

        if token is None or token == "":
            _LOGGER.error("Access token is REQUIRED.")
            raise ValueError("Access token is REQUIRED.")

        _LOGGER.debug("Setup ETI/Domo API for %s@%s", username, host)

        self._host = host
        self._username = username
        self._password = password
        self._token = token
        self._hass = hass
        self._session = session or aiohttp.ClientSession()
        self._api_url = f"http://{self._host}/domo/"

        self._client_id = None
        self._swver = None
        self._serial = None
        self._keycode = None
        self._features = []
        self._floors = None
        self._rooms = None
        self._devices = None
        self.scenario_manager = ScenarioManager(self)
        
    @property
    def software_version(self) -> Optional[str]:
        """Return a software version of ETI/Domo."""
        return self._swver

    @property
    def serial(self) -> Optional[str]:
        """Return a serial number of ETI/Domo."""
        return self._serial

    @property
    def keycode(self) -> Optional[str]:
        """Return a keycode for ETI/Domo."""
        return self._keycode

    async def _request(self, command: dict, resp_command: str = None) -> dict:
        """Handle a request to an ETI/Domo device."""
        url = self._api_url
        headers = {
            "User-Agent": f"PythonCameManager/{VERSION}",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"access_token {self._token}",
        }



        try:
            if DEBUG_DEEP:
                _LOGGER.debug("Send API request: %s", command)
            else:
                _LOGGER.debug("Sending network request to %s with command: %s", url, command)

            data = {"command": json.dumps(command)}
            async with self._session.post(url, data=data, headers=headers, timeout=30) as response:
                _LOGGER.debug("Request sent. Awaiting response...")
                response.raise_for_status()
                text = await response.text()
                _LOGGER.debug("Received response: %s", text)
        except asyncio.TimeoutError as exception:
            _LOGGER.error("Timeout occurred while connecting to ETI/Domo device: %s", exception)
            raise ETIDomoConnectionTimeoutError(
                "Timeout occurred while connecting to ETI/Domo device."
            ) from exception
        except aiohttp.ClientError as exception:
            _LOGGER.error("Error occurred while communicating with ETI/Domo device: %s", exception)
            raise ETIDomoConnectionError(
                "Error occurred while communicating with ETI/Domo device."
            ) from exception

        try:
            resp_json = json.loads(text)
            ack_reason = resp_json.get("sl_data_ack_reason")

            if ack_reason == 0:
                cmd_name = resp_json.get("sl_cmd")
                if resp_command is not None and cmd_name != resp_command:
                    _LOGGER.error("Invalid server response. Expected %s. Actual %s", resp_command, cmd_name)
                    raise ETIDomoError(
                        "Invalid server response. Expected {}. Actual {}".format(
                            repr(resp_command), repr(cmd_name)
                        )
                    )
                _LOGGER.debug("Request successful, response: %s", resp_json)
                return resp_json

            errors = {
                1: "Invalid user.",
                3: "Too many sessions during login.",
                4: "Error occurred in JSON Syntax.",
                5: "No session layer command tag.",
                6: "Unrecognized session layer command.",
                7: "No client ID in request.",
                8: "Wrong client ID in request.",
                9: "Wrong application command.",
                10: "No reply to application command, maybe service down.",
                11: "Wrong application data.",
            }

            if ack_reason in errors:
                _LOGGER.error("ETIDomoError: %s (errno: %s)", errors[ack_reason], ack_reason)
                raise ETIDomoError(errors[ack_reason], errno=ack_reason)

            _LOGGER.error("Unknown error (ack_reason: %s)", ack_reason)
            raise ETIDomoError(
                f"Unknown error (#{ack_reason}).",
                errno=ack_reason,
            )

        except ValueError as ex:
            _LOGGER.error("Error in sl_data_ack_reason, can't find value: %s", ex)
            raise ETIDomoError("Error in sl_data_ack_reason, can't find value.") from ex

    @property
    def connected(self) -> bool:
        """Return True if entity is available."""
        #_LOGGER.debug("Checking connection status: %s", self._client_id is not None)
        return self._client_id is not None

    async def login(self) -> None:
        """Login function for access to ETI/Domo."""
        if self._client_id:
            _LOGGER.debug("Already logged in with client_id: %s", self._client_id)
            return

        _LOGGER.debug("Login attempt for user: %s", self._username)
        response = await self._request(
            {
                "sl_cmd": "sl_registration_req",
                "sl_login": self._username,
                "sl_pwd": self._password,
            },
            "sl_registration_ack",
        )

        try:
            if response["sl_client_id"]:
                _LOGGER.debug("Successful authorization. Client ID: %s", response.get("sl_client_id"))
                self._client_id = response.get("sl_client_id")
                self._features = []
                self._devices = None
            else:
                _LOGGER.error("Error in sl_client_id, can't get value.")
                raise ETIDomoError("Error in sl_client_id, can't get value.")
        except KeyError as ex:
            _LOGGER.error("Error in sl_client_id, can't find value: %s", ex)
            raise ETIDomoError("Error in sl_client_id, can't find value.") from ex

    async def application_request(
        self, command: dict, resp_command: str = "generic_reply"
    ) -> dict:
        """Handle a request to application layer to ETI/Domo."""
        await self.login()

        if DEBUG_DEEP:
            _LOGGER.debug("Send application layer API request: %s", command)
        else:
            _LOGGER.debug("Sending application layer request: %s", command)

        cmd = command.copy()

        try:
            response = await self._request(
                {
                    "sl_cmd": "sl_data_req",
                    "sl_client_id": self._client_id,
                    "sl_appl_msg": cmd,
                },
            )
        except ETIDomoConnectionError as err:
            _LOGGER.debug("Server goes offline.")
            self._client_id = None
            raise err

        if resp_command is not None and response.get("cmd_name") != resp_command:
            _LOGGER.error(
                "Invalid server response. Expected %s. Actual %s",
                resp_command, response.get("cmd_name")
            )
            raise ETIDomoError(
                "Invalid server response. Expected {}. Actual {}".format(
                    repr(resp_command), repr(response.get("cmd_name"))
                )
            )

        _LOGGER.debug("Application request successful, response: %s", response)
        return response

    async def _get_features(self) -> list:
        """Get list of available features."""
        if self._features:
            _LOGGER.debug("Features already cached: %s", self._features)
            return self._features

        cmd = {
            "cmd_name": "feature_list_req",
        }
        _LOGGER.debug("Requesting feature list with command: %s", cmd)
        response = await self.application_request(cmd, "feature_list_resp")
        self._swver = response.get("swver")
        self._serial = response.get("serial")
        self._keycode = response.get("keycode")
        self._features = response.get("list")
        _LOGGER.debug("Features received: %s", self._features)
        return self._features

    async def get_all_floors(self) -> List[Floor]:
        """Get list of available floors."""
        if self._floors is not None:
            _LOGGER.debug("Floors already cached: %s", self._floors)
            return self._floors

        cmd = {
            "cmd_name": "floor_list_req",
            "topologic_scope": "plant",
        }
        _LOGGER.debug("Requesting floor list with command: %s", cmd)
        response = await self.application_request(cmd, "floor_list_resp")
        self._floors = []
        for floor in response.get("floor_list", []):
            self._floors.append(Floor.from_dict(floor))
        _LOGGER.debug("Floors received: %s", self._floors)
        return self._floors

    async def get_all_rooms(self) -> List[Room]:
        """Get list of available rooms."""
        if self._rooms is not None:
            _LOGGER.debug("Rooms already cached: %s", self._rooms)
            return self._rooms

        cmd = {
            "cmd_name": "room_list_req",
            "topologic_scope": "plant",
        }
        _LOGGER.debug("Requesting room list with command: %s", cmd)
        response = await self.application_request(cmd, "room_list_resp")
        self._rooms = []
        for room in response.get("room_list", []):
            self._rooms.append(Room.from_dict(room))
        _LOGGER.debug("Rooms received: %s", self._rooms)
        return self._rooms

    async def _update_devices(self) -> Optional[List[CameDevice]]:
        """Update devices info."""
        if self._devices is None:
            _LOGGER.debug("Update devices info: fetching from network")

            devices = []
            for feature in await self._get_features():
                _LOGGER.debug("Getting featured devices for feature: %s", feature)
                devices.extend(await get_featured_devices(self, feature))

            self._devices = devices
            _LOGGER.debug("Devices updated: %s", self._devices)
        else:
            _LOGGER.debug("Update devices info: Use cached data")

        return self._devices

    async def get_all_devices(self) -> Optional[List[CameDevice]]:
        """Get list of all discovered devices."""
        _LOGGER.debug("Getting all devices")
        return await self._update_devices()

    async def get_device_by_id(self, device_id: str) -> Optional[CameDevice]:
        """Get device by unique ID."""
        _LOGGER.debug("Getting device by id: %s", device_id)
        for device in await self.get_all_devices():
            if device.unique_id == device_id:
                _LOGGER.debug("Device found: %s", device)
                return device

        _LOGGER.warning("Device with id %s not found", device_id)
        return None

    async def get_device_by_act_id(self, act_id: int) -> Optional[CameDevice]:
        """Get device by device's act ID."""
        _LOGGER.debug("Getting device by act_id: %s", act_id)
        for device in await self.get_all_devices():
            if device.act_id == act_id:
                _LOGGER.debug("Device found: %s", device)
                return device

        _LOGGER.warning("Device with act_id %s not found", act_id)
        return None

    async def get_device_by_name(self, name: str) -> Optional[CameDevice]:
        """Get device by name."""
        _LOGGER.debug("Getting device by name: %s", name)
        for device in await self.get_all_devices():
            if device.name == name:
                _LOGGER.debug("Device found: %s", device)
                return device

        _LOGGER.warning("Device with name %s not found", name)
        return None

    async def get_devices_by_floor(self, floor_id: int) -> List[CameDevice]:
        """Get a list of devices on a floor."""
        _LOGGER.debug("Getting devices by floor_id: %s", floor_id)
        devices = []
        for device in await self.get_all_devices():
            if device.floor_id == floor_id:
                devices.append(device)

        _LOGGER.debug("Devices found for floor_id %s: %s", floor_id, devices)
        return devices

    async def get_devices_by_room(self, room_id: int) -> List[CameDevice]:
        """Get a list of devices in a room."""
        _LOGGER.debug("Getting devices by room_id: %s", room_id)
        devices = []
        for device in await self.get_all_devices():
            if device.room_id == room_id:
                devices.append(device)

        _LOGGER.debug("Devices found for room_id %s: %s", room_id, devices)
        return devices

    async def status_update(self, timeout: Optional[int] = None) -> bool:
        """Long polling method which read status updates."""
        _LOGGER.debug("Starting status update with timeout: %s", timeout)
        if self._devices is None:
            _LOGGER.debug("Devices not cached, updating devices first")
            await self._update_devices()
            return True

        cmd = {
            "cmd_name": "status_update_req",
        }
        if timeout is not None:
            cmd["timeout"] = timeout
        _LOGGER.debug("Sending status update request: %s", cmd)
        response = await self.application_request(cmd, "status_update_resp")

        updated = False

        for device_info in response.get("result", []):  # type: DeviceState
            if device_info.get("cmd_name", "").startswith("scenario_"):
                self.scenario_manager.handle_update(self._hass, device_info)  
            
            if device_info.get("cmd_name") == "plant_update_ind":
                _LOGGER.debug("Plant update indication received, refreshing devices")
                self._devices = None
                await self._update_devices()
                return True

            act_id = device_info.get("act_id")
            if act_id:
                device = await self.get_device_by_act_id(act_id)
                if device is not None:
                    updated |= device.update_state(device_info)
                    _LOGGER.debug("Device %s state updated: %s", act_id, device_info)

        _LOGGER.debug("Status update finished, updated: %s", updated)
        return updated
