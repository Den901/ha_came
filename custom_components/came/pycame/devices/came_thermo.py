"""ETI/Domo thermoregulation device."""

import logging
from typing import Optional

from .base import TYPE_THERMOSTAT, CameDevice, DeviceState

_LOGGER = logging.getLogger(__name__)


# Thermoregulation devices states
THERMO_STATE_OFF = 0
THERMO_STATE_ON = 1

# Thermoregulation devices modes
THERMO_MODE_OFF = 0
THERMO_MODE_MANUAL = 1
THERMO_MODE_AUTO = 2
THERMO_MODE_JOLLY = 3

# Thermoregulation devices seasons
THERMO_SEASON_OFF = "plant_off"
THERMO_SEASON_WINTER = "winter"
THERMO_SEASON_SUMMER = "summer"

# Thermoregulation devices dehumidifier states
THERMO_DEHUMIDIFIER_OFF = 0
THERMO_DEHUMIDIFIER_ON = 1

# Thermoregulation devices fan speeds
THERMO_FAN_SPEED_OFF = 0
THERMO_FAN_SPEED_SLOW = 1
THERMO_FAN_SPEED_MEDIUM = 2
THERMO_FAN_SPEED_FAST = 3
THERMO_FAN_SPEED_AUTO = 4


class CameThermo(CameDevice):
    """ETI/Domo thermoregulation device class."""

    def __init__(self, manager, device_info: DeviceState):
        """Init instance."""
        super().__init__(manager, TYPE_THERMOSTAT, device_info)
        #self.raw_zone = device_info

    @property
    def mode(self) -> Optional[int]:
        """Get current mode."""
        return self._device_info.get("mode")

    @property
    def season(self) -> Optional[str]:
        """Get current season mode."""
        return self._device_info.get("season")

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        temp = self._device_info.get("temp", self._device_info.get("temp_dec"))
        return temp / 10 if temp is not None else None

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        temp = self._device_info.get("set_point")
        return temp / 10 if temp is not None else None

    @property
    def support_target_temperature(self) -> bool:
        """Return True if device can change target temperature."""
        return True

    @property
    def dehumidifier_state(self) -> Optional[int]:
        """Return the state of dehumidifier."""
        dehumidifier = self._device_info.get("dehumidifier", {})
        return dehumidifier.get("enabled")

    @property
    def target_humidity(self) -> Optional[int]:
        """Return the humidity we try to reach."""
        dehumidifier = self._device_info.get("dehumidifier", {})
        return dehumidifier.get("setpoint")

    @property
    def support_target_humidity(self) -> bool:
        """Return True if device can change target humidity."""
        return self.target_humidity is not None

    @property
    def fan_speed(self) -> Optional[int]:
        """Get current fan speed."""
        return self._device_info.get("fan_speed")

    @property
    def support_fan_speed(self) -> bool:
        """Return True if device can change wind speed."""
        return self.fan_speed is not None

    def update(self):
        """Update device state."""
        self._force_update("thermo")

    def zone_config(
        self,
        mode: int = None,
        temperature: float = None,
        season: str = None,
        fan_speed: int = None,
    ):
        """Change device's config."""
        if (
            mode is None
            and temperature is None
            and season is None
            and fan_speed is None
        ):
            raise ValueError("At least one parameter is required")

        self._check_act_id()

        cmd = {
            "cmd_name": "thermo_zone_config_req",
            "act_id": self.act_id,
            "mode": mode if mode is not None else self._device_info.get("mode"),
            "set_point": (
                int(temperature * 10)
                if temperature is not None
                else self._device_info.get("set_point")
            ),
            "extended_infos": 0,
        }
        if season is not None:
            cmd["extended_infos"] = 1
            cmd["season"] = season
        if fan_speed is not None:
            cmd["extended_infos"] = 1
            cmd["fan_speed"] = fan_speed

        self._manager.application_request(cmd)

        log = {}
        for k in ["mode", "set_point", "season", "fan_speed"]:
            if k in cmd:
                log[k] = cmd[k]

        if mode is not None:
            log["mode"] = int(cmd["mode"] != THERMO_MODE_OFF)

        _LOGGER.debug('Set new status for thermostat "%s": %s', self.name, log)

    @property
    def fan_mode(self) -> Optional[str]:
        """Return current fan mode as string (low/medium/high)."""
        speed = self.fan_speed
        if speed == THERMO_FAN_SPEED_SLOW:
            return "LOW"
        elif speed == THERMO_FAN_SPEED_MEDIUM:
            return "MEDIUM"
        elif speed == THERMO_FAN_SPEED_FAST:
            return "HIGH"
        elif (
            speed == THERMO_FAN_SPEED_AUTO or speed == THERMO_FAN_SPEED_OFF
        ):  # In modalità OFF, il ventilatore è spento ma l'app lo mostra comunque come AUTO
            return "AUTO"
        return "AUTO"  # fallback sicuro

    def set_target_temperature(self, temp: float) -> None:
        """Set the temperature we try to reach."""
        self.zone_config(temperature=temp)

    def set_fan_speed(self, speed: str) -> None:
        """Imposta la velocità della ventola del fan coil."""
        speed_map = {
            "LOW": THERMO_FAN_SPEED_SLOW,
            "MEDIUM": THERMO_FAN_SPEED_MEDIUM,
            "HIGH": THERMO_FAN_SPEED_FAST,
            "AUTO": THERMO_FAN_SPEED_AUTO,
        }
        if speed not in speed_map:
            _LOGGER.warning(
                "🚫 Velocità non valida per fan coil %s: %s", self.name, speed
            )
            return

        _LOGGER.info("🌀 Imposto velocità fan coil %s su %s", self.name, speed)
        try:
            self.zone_config(fan_speed=speed_map[speed])
        except Exception as e:
            _LOGGER.error(
                "⚠️ Errore durante l'impostazione della velocità fan coil %s: %s",
                self.name,
                e,
            )
          
    @property
    def t1(self) -> Optional[int]:
        return self._device_info.get("t1")

    @property
    def t2(self) -> Optional[int]:
        return self._device_info.get("t2")

    @property
    def t3(self) -> Optional[int]:
        return self._device_info.get("t3")

    @property
    def reason(self) -> Optional[int]:
        return self._device_info.get("reason")
        
    @property
    def floor_ind(self) -> Optional[int]:
        return self._device_info.get("floor_ind")

    @property
    def room_ind(self) -> Optional[int]:
        return self._device_info.get("room_ind")

    @property
    def temp_dec(self) -> Optional[int]:
        return self._device_info.get("temp_dec")

    @property
    def set_point(self) -> Optional[int]:
        return self._device_info.get("set_point")

    @property
    def antifreeze(self) -> Optional[int]:
        return self._device_info.get("antifreeze")

    @property
    def f3a(self) -> Optional[dict]:
        return self._device_info.get("f3a")

    @property
    def thermo_algo(self) -> Optional[dict]:
        return self._device_info.get("thermo_algo")
        
    @property
    def status(self) -> Optional[int]:
        return self._device_info.get("status")

    @property
    def antifreeze(self) -> Optional[int]:
        return self._device_info.get("antifreeze")        
        
    @property
    def fan_mode_ha(self) -> str:
        """Velocità nel linguaggio di HA (minuscolo)."""
        return self.fan_mode.lower()

    def set_fan_mode_ha(self, mode: str) -> None:
        """Accetta nomi HA (low/medium/high/auto) → chiama set_fan_speed."""
        self.set_fan_speed(mode.upper())    
        
