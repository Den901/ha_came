"""Support for CAME scenarios."""
import logging
from typing import List
from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pycame.came_manager import CameManager
from .const import DOMAIN, CONF_MANAGER

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Configura gli scenari CAME."""
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    scenarios = await hass.async_add_executor_job(manager.get_scenarios)
    entities = [CameScenarioEntity(scenario, manager) for scenario in scenarios]
    async_add_entities(entities)

class CameScenarioEntity(Scene):
    """Rappresentazione di uno scenario CAME."""

    def __init__(self, scenario, manager: CameManager):
        self._manager = manager
        self._scenario = scenario
        self._attr_name = scenario.get("name", "Unknown Scenario")
        self._attr_unique_id = f"came_scenario_{scenario['act_id']}"

    def activate(self, **kwargs):
        """Attiva lo scenario."""
        self._manager.activate_scenario(self._scenario["act_id"])

    @property
    def extra_state_attributes(self):
        """Attributi aggiuntivi per lo scenario."""
        return {
            "act_id": self._scenario["act_id"],
            "status": self._scenario.get("status", 0),
            "user_defined": self._scenario.get("user-defined", 0)
        }
