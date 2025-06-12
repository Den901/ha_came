"""Python client for ETI/Domo."""

import json
import logging
from typing import List, Optional

import requests

from .pycame.const import DEBUG_DEEP, STARTUP_MESSAGE, VERSION
from .pycame.devices import get_featured_devices
from .pycame.devices.base import CameDevice, DeviceState
from .pycame.exceptions import (
    ETIDomoConnectionError,
    ETIDomoConnectionTimeoutError,
    ETIDomoError,
)
from .pycame.models import Floor, Room

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
        session: Optional[requests.Session] = None,
    ):
        """Initialize connection with the ETI/Domo."""
        if not _STARTUP:
            _LOGGER.info(STARTUP_MESSAGE)
            _STARTUP.append(True)

        if token is None or token == "":
            raise ValueError("Access token is REQUIRED.")

        _LOGGER.debug("Setup ETI/Domo API for %s@%s", username, host)

        self._host = host
        self._username = username
        self._password = password
        self._token = token
        self._session = session or requests.Session()

        self._client_id = None
        self._swver = None
        self._serial = None
        self._keycode = None
        self._features = []
        self._floors = None
        self._rooms = None
        self._devices = None

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

    def _request(self, command: dict, resp_command: str = None) -> dict:
        """Handle a request to an ETI/Domo device."""
        url = f"http://{self._host}/domo/"
        headers = {
            "User-Agent": f"PythonCameManager/{VERSION}",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"access_token {self._token}",
        }

        try:
            if DEBUG_DEEP:
                _LOGGER.debug("Send API request: %s", command)

            response = self._session.post(
                url, data={"command": json.dumps(command)}, headers=headers
            )
            response.raise_for_status()

            if DEBUG_DEEP:
                _LOGGER.debug("Response: %s", response.text)

        except requests.exceptions.ConnectTimeout as exception:
            raise ETIDomoConnectionTimeoutError(
                "Timeout occurred while connecting to ETI/Domo device."
            ) from exception

        except (
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.BaseHTTPError,
        ) as exception:
            raise ETIDomoConnectionError(
                "Error occurred while communicating with ETI/Domo device."
            ) from exception

        try:
            resp_json = response.json()
            ack_reason = resp_json.get("sl_data_ack_reason")

            if ack_reason == 0:
                cmd_name = resp_json.get("sl_cmd")
                if resp_command is not None and cmd_name != resp_command:
                    raise ETIDomoError(
                        "Invalid server response. Expected {}. Actual {}".format(
                            repr(resp_command), repr(cmd_name)
                        )
                    )

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
                raise ETIDomoError(errors[ack_reason], errno=ack_reason)

            raise ETIDomoError(
                f"Unknown error (#{ack_reason}).",
                errno=ack_reason,
            )

        except ValueError as ex:
            raise ETIDomoError("Error in sl_data_ack_reason, can't find value.") from ex

    @property
    def connected(self) -> bool:
        """Return True if entity is available."""
        return self._client_id is not None

    def login(self) -> None:
        """Login function for access to ETI/Domo."""
        if self._client_id:
            return

        _LOGGER.debug("Login attempt")
        response = self._request(
            {
                "sl_cmd": "sl_registration_req",
                "sl_login": self._username,
                "sl_pwd": self._password,
            },
            "sl_registration_ack",
        )

        try:
            if response["sl_client_id"]:
                _LOGGER.debug("Successful authorization.")
                self._client_id = response.get("sl_client_id")
                self._features = []
                self._devices = None
            else:
                raise ETIDomoError("Error in sl_client_id, can't get value.")
        except KeyError as ex:
            raise ETIDomoError("Error in sl_client_id, can't find value.") from ex

    def application_request(
        self, command: dict, resp_command: str = "generic_reply"
    ) -> dict:
        """Handle a request to application layer to ETI/Domo."""
        self.login()

        if DEBUG_DEEP:
            _LOGGER.debug("Send application layer API request: %s", command)

        cmd = command.copy()

        try:
            response = self._request(
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
            raise ETIDomoError(
                "Invalid server response. Expected {}. Actual {}".format(
                    repr(resp_command), repr(response.get("cmd_name"))
                )
            )

        return response

    def _get_features(self) -> list:
        """Get list of available features."""
        if self._features:
            return self._features

        cmd = {
            "cmd_name": "feature_list_req",
        }
        response = self.application_request(cmd, "feature_list_resp")
        self._swver = response.get("swver")
        self._serial = response.get("serial")
        self._keycode = response.get("keycode")
        self._features = response.get("list")
        return self._features

    def get_all_floors(self) -> List[Floor]:
        """Get list of available floors."""
        if self._floors is not None:
            return self._floors

        cmd = {
            "cmd_name": "floor_list_req",
            "topologic_scope": "plant",
        }
        response = self.application_request(cmd, "floor_list_resp")
        self._floors = []
        for floor in response.get("floor_list", []):
            self._floors.append(Floor.from_dict(floor))
        return self._floors

    def get_all_rooms(self) -> List[Room]:
        """Get list of available rooms."""
        if self._rooms is not None:
            return self._rooms

        cmd = {
            "cmd_name": "room_list_req",
            "topologic_scope": "plant",
        }
        response = self.application_request(cmd, "room_list_resp")
        self._rooms = []
        for room in response.get("room_list", []):
            self._rooms.append(Room.from_dict(room))
        return self._rooms

    def _update_devices(self) -> Optional[List[CameDevice]]:
        """Update devices info."""
        if self._devices is None:
            _LOGGER.debug("Update devices info")

            devices = []
            for feature in self._get_features():
                devices.extend(get_featured_devices(self, feature))

            self._devices = devices

        else:
            _LOGGER.debug("Update devices info: Use cached data")

        return self._devices

    def get_all_devices(self) -> Optional[List[CameDevice]]:
        """Get list of all discovered devices."""
        return self._update_devices()

    def get_device_by_id(self, device_id: str) -> Optional[CameDevice]:
        """Get device by unique ID."""
        for device in self.get_all_devices():
            if device.unique_id == device_id:
                return device

        return None

    def get_device_by_act_id(self, act_id: int) -> Optional[CameDevice]:
        """Get device by device's act ID."""
        for device in self.get_all_devices():
            if device.act_id == act_id:
                return device

        return None

    def get_device_by_name(self, name: str) -> Optional[CameDevice]:
        """Get device by name."""
        for device in self.get_all_devices():
            if device.name == name:
                return device

        return None

    def get_devices_by_floor(self, floor_id: int) -> List[CameDevice]:
        """Get a list of devices on a floor."""
        devices = []
        for device in self.get_all_devices():
            if device.floor_id == floor_id:
                devices.append(device)

        return devices

    def get_devices_by_room(self, room_id: int) -> List[CameDevice]:
        """Get a list of devices in a room."""
        devices = []
        for device in self.get_all_devices():
            if device.room_id == room_id:
                devices.append(device)

        return devices

    def status_update(self, timeout: Optional[int] = None) -> bool:
        """Long polling method which read status updates."""
        if self._devices is None:
            self._update_devices()
            return True

        cmd = {
            "cmd_name": "status_update_req",
        }
        if timeout is not None:
            cmd["timeout"] = timeout
        response = self.application_request(cmd, "status_update_resp")

        updated = False

        for device_info in response.get("result", []):  # type: DeviceState
            if device_info.get("cmd_name") == "plant_update_ind":
                self._devices = None
                self._update_devices()
                return True

            act_id = device_info.get("act_id")
            if act_id:
                device = self.get_device_by_act_id(act_id)
                if device is not None:
                    updated |= device.update_state(device_info)

        return updated


# Scenari

    def get_scenarios(self):
        """Richiede la lista degli scenari."""
        response = self._session.post(self._api_url, json={"cmd_name": "scenarios_list_req"})
        return response.json().get("array", [])

    def activate_scenario(self, scenario_id):
        """Attiva uno scenario."""
        self._session.post(self._api_url, json={
            "cmd_name": "scenario_activation_req_",
            "id": scenario_id
        })

    def create_scenario(self, name):
        """Inizia la registrazione di un nuovo scenario."""
        return self._session.post(self._api_url, json={
            "cmd_name": "scenario_registration_start",
            "name": name
        })

    def delete_scenario(self, scenario_id):
        """Elimina uno scenario esistente."""
        self._session.post(self._api_url, json={
            "cmd_name": "scenario_delete_req",
            "id": scenario_id
        })
