"""ETI/Domo light device."""

import colorsys
import logging
from typing import List

from .base import TYPE_LIGHT, CameDevice, DeviceState

_LOGGER = logging.getLogger(__name__)

# Light types
LIGHT_TYPE_STEP_STEP = "STEP_STEP"
LIGHT_TYPE_DIMMER = "DIMMER"
LIGHT_TYPE_RGB = "RGB"

# Light states
LIGHT_STATE_OFF = 0
LIGHT_STATE_ON = 1
LIGHT_STATE_AUTO = 4


class CameLight(CameDevice):
    """ETI/Domo light device class."""

    def __init__(self, manager, device_info: DeviceState):
        """Init instance."""
        super().__init__(manager, TYPE_LIGHT, device_info)

    @property
    def light_type(self) -> str:
        """Get light type."""
        return self._device_info.get("type")

    @property
    def support_color(self) -> bool:
        """Return True if light support color as HS values."""
        # pylint: disable=fixme
        # todo: Which type is correct? "RGB" or "rgb"
        return self.light_type.upper() == LIGHT_TYPE_RGB

    @property
    def rgb_color(self) -> List[int]:
        """Return the RGB color of the light."""
        perc = int(self._device_info.get("perc", 100) * 255 / 100)
        return self._device_info.get("rgb", [perc, perc, perc])

    @property
    def _hsv_color(self) -> List[int]:
        """Return the HSV color of the light."""
        rgb = self.rgb_color
        hsv = colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2])
        return [round(hsv[0] * 360), round(hsv[1] * 100), round(hsv[2] * 100 / 255)]

    @property
    def hs_color(self) -> List[int]:
        """Return the HS color of the light."""
        return self._hsv_color[0:2]

    def set_rgb_color(self, rgb: List[int]):
        """Set RGB color of light."""
        if not self.support_color:
            return

        if rgb[0] < 0:
            rgb[0] = 0
        elif rgb[0] > 255:
            rgb[0] = 255
        if rgb[1] < 0:
            rgb[1] = 0
        elif rgb[1] > 255:
            rgb[1] = 255
        if rgb[2] < 0:
            rgb[2] = 0
        elif rgb[2] > 255:
            rgb[2] = 255

        self.switch(rgb=rgb)

    def set_hs_color(self, hs: List[float]):
        """Set HS color of light."""
        if not self.support_color:
            return

        if hs[0] < 0:
            hs[0] = 0
        elif hs[0] > 360:
            hs[0] = 360
        if hs[1] < 0:
            hs[1] = 0
        elif hs[1] > 100:
            hs[1] = 100

        if self.support_color:
            hsv = self._hsv_color
            self.switch(
                rgb=list(
                    map(
                        int,
                        colorsys.hsv_to_rgb(
                            hs[0] / 360, hs[1] / 100, hsv[2] * 255 / 100
                        ),
                    )
                )
            )

    @property
    def support_brightness(self) -> bool:
        """Return True if light support brightness in percents."""
        return self.light_type in (LIGHT_TYPE_DIMMER, LIGHT_TYPE_RGB)

    @property
    def brightness(self) -> int:
        """Get light brightness in percents."""
        if self.support_color:
            return self._hsv_color[2]

        return self._device_info.get("perc", 100)  # Applicable only for dimmers

    def set_brightness(self, brightness: int):
        """Set light brightness in percents."""
        if not self.support_brightness:
            return

        if brightness < 0:
            brightness = 0
        elif brightness > 100:
            brightness = 100

        if self.support_color:
            hsv = self._hsv_color
            self.switch(
                rgb=list(
                    map(
                        int,
                        colorsys.hsv_to_rgb(
                            hsv[0] / 360, hsv[1] / 100, brightness * 255 / 100
                        ),
                    )
                )
            )

        else:
            self.switch(brightness=brightness)

    def switch(self, state: int = None, brightness: int = None, rgb: List[int] = None):
        """Switch light to new state."""
        if state is None and brightness is None and rgb is None:
            raise ValueError("At least one parameter is required")

        self._check_act_id()

        cmd = {
            "cmd_name": "light_switch_req",
            "act_id": self.act_id,
            "wanted_status": state if state is not None else self.state,
        }
        log = {}
        if state is not None:
            log["status"] = cmd["wanted_status"]
        if brightness is not None:
            log["perc"] = cmd["perc"] = brightness
        if rgb is not None:
            log["rgb"] = cmd["rgb"] = rgb[0:3]

        _LOGGER.debug('Set new state for light "%s": %s', self.name, log)

        self._manager.application_request(cmd)

    def turn_off(self):
        """Turn off light."""
        self.switch(LIGHT_STATE_OFF)

    def turn_on(self):
        """Turn on light."""
        self.switch(LIGHT_STATE_ON)

    def turn_auto(self):
        """Switch light to automatic mode."""
        self.switch(LIGHT_STATE_AUTO)

    def update(self):
        """Update device state."""
        self._force_update("light")
