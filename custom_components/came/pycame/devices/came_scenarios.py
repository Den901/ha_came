from .base import CameDevice
import logging
from ..exceptions import ETIDomoError

from homeassistant.helpers.dispatcher import async_dispatcher_send


_LOGGER = logging.getLogger(__name__)

class ScenarioDevice(CameDevice):
    """Rappresentazione logica degli scenari."""

    def __init__(self, manager):
        super().__init__(
            manager,
            device_info={"act_id": -1, "name": "Scenari"},
            type_id=4
        )
        self._name = "Scenari"
        #_LOGGER.debug("ScenarioDevice istanziato con type: %s", self.type)     
         

    @property
    def name(self):
        return self._name

    @property
    def device_type(self):
        return "scenarios"

    @property
    def available_scenarios(self):
        return self._manager.get_scenarios()

    def activate(self, scenario_id: int):
        self._manager.activate_scenario(scenario_id)

    def update(self, data: dict) -> bool:
        return False

class ScenarioManager:
    def __init__(self, manager):
        self._manager = manager


    def get_scenarios(self):
        """Recupera la lista degli scenari dal sistema CAME."""
        scenarios = self._manager.application_request(
            {"cmd_name": "scenarios_list_req"}, "scenarios_list_resp"
        ).get("array", [])

        _LOGGER.debug("ScenarioDevice._get_scenarios restituisce %d scenari", len(scenarios))
        return scenarios
    

    def activate_scenario(self, scenario_id: int):
        """Attiva uno scenario esistente."""
        try:
            self._manager.application_request(
                {"cmd_name": "scenario_activation_req", "id": scenario_id},
                resp_command=None
            )
        except ETIDomoError as e:
            if "Actual 'generic_reply'" in str(e):
                _LOGGER.warning("Attivazione scenario fallita: %s", str(e), exc_info=True)
            else:
                raise

    def create_scenario(self, name: str):
        """Inizia la registrazione di uno scenario."""
        self._manager.application_request(
            {"cmd_name": "scenario_registration_start", "name": name},
            resp_command="scenario_registration_start_ack"
        )

    def delete_scenario(self, scenario_id: int):
        """Elimina uno scenario."""
        self._manager.application_request(
            {"cmd_name": "scenario_delete_req", "id": scenario_id},
            resp_command="scenario_delete_resp"
        )
        
    def refresh_scenarios(self):
        """Recupera di nuovo la lista scenari dal server ETI/Domo."""
        #_LOGGER.debug("Aggiorno la lista degli scenari...")
        self._scenarios = self.get_scenarios()
        _LOGGER.debug("refresh_scenarios: lista scenari aggiornata, totale scenari: %d", len(self._scenarios))
        
    def handle_update(self, hass, device_info: dict):
        """Gestisce aggiornamenti relativi agli scenari."""
        cmd_name = device_info.get("cmd_name")

        if cmd_name == "scenario_status_ind":
            scenario_id = device_info.get("id")
            _LOGGER.debug("ScenarioManager: aggiornamento stato scenario %s: %s", scenario_id, device_info)
            hass.add_job(
                async_dispatcher_send,
                hass,
                "came_scenario_update",
                scenario_id,
                device_info,
            )

        elif cmd_name == "scenario_user_ind" and device_info.get("action") in ("add", "create"):
            _LOGGER.debug("ScenarioManager: nuovo scenario utente aggiunto: aggiorno lista e invio segnale")
            self.refresh_scenarios()
            hass.add_job(
                async_dispatcher_send,
                hass,
                "came_scenarios_refreshed"
            )

