"""Support for CAME scenarios."""

import asyncio
import logging
from datetime import datetime
from typing import List

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .pycame.came_manager import CameManager
from .const import DOMAIN, CONF_MANAGER

_LOGGER = logging.getLogger(__name__)

# Dizionario id scenario -> entità per tracciare entità già create


async def async_setup_entry(hass, config_entry, async_add_entities):
    global _existing_scenario_entities 
    manager = hass.data[DOMAIN][CONF_MANAGER]  # type: CameManager
    # Inizializza struttura per tracciare le entità scenario già create
    if "came_scenarios" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["came_scenarios"] = {}
    _existing_scenario_entities = hass.data[DOMAIN]["came_scenarios"]
    existing_entities = hass.data[DOMAIN]["came_scenarios"]

    def create_new_entities(scenarios):
        _LOGGER.debug("Entità già registrate: %s", list(_existing_scenario_entities.keys()))
        entities = []
        for scenario in scenarios:
            scenario["user_defined"] = scenario.get("user_defined", scenario.get("user-defined", 0))
            
            sid = scenario.get("id")
            if sid is None:
                _LOGGER.debug("create_new_entities: scenario senza id ignorato: %s", scenario)
                continue

            entity = _existing_scenario_entities.get(sid)

            # Se l'entità non è ancora registrata in Home Assistant, aggiungila
            if entity is None or entity.hass is None:
                if scenario.get("user_defined", 0) == 1:
                    _LOGGER.debug("create_new_entities: (ri)creo scenario user_defined id %s nome %s", sid, scenario.get("name"))
                else:
                    _LOGGER.debug("create_new_entities: (ri)creo scenario statico id %s nome %s", sid, scenario.get("name"))

                entity = CameScenarioEntity(scenario, manager)
                _existing_scenario_entities[sid] = entity
                entities.append(entity)
            else:
                _LOGGER.debug("Scenario id %s già presente, salto creazione", sid)
        return entities



    # Crea le entità iniziali
    scenarios = await hass.async_add_executor_job(manager.scenario_manager.get_scenarios)
    _LOGGER.debug("Setup iniziale scenari: caricati %d scenari", len(scenarios))
    entities = create_new_entities(scenarios)
    async_add_entities(entities)

    # Funzione che ascolta l'evento refresh per aggiungere nuove entità dinamicamente
    async def handle_refresh_scenarios():
        _LOGGER.debug("Ricevuto evento came_scenarios_refreshed, controllo nuovi scenari...")
        #_LOGGER.debug("Entità già registrate: %s", list(_existing_scenario_entities.keys()))

        scenarios = await hass.async_add_executor_job(manager.scenario_manager.get_scenarios)

        # Fai una copia degli id esistenti PRIMA di aggiungere nuovi
        existing_ids = set(_existing_scenario_entities.keys())
        current_ids = set(s["id"] for s in scenarios if s.get("id") is not None)


        # Rimuovi entità obsolete
        removed_ids = existing_ids - current_ids

        # Ottieni una sola volta il registry
        registry = async_get_entity_registry(hass)

        for rid in removed_ids:
            entity = _existing_scenario_entities.pop(rid, None)
            if entity is None:
                continue

            entity_id = entity.entity_id

            # Rimuovi l'entità dal runtime se è ancora attiva
            if entity.hass is not None:
                await entity.async_remove()
                _LOGGER.debug("Entità scenario id %s rimossa dal runtime", rid)

            # Rimuovi anche dal registry (in modo permanente)
            if registry.async_is_registered(entity_id):
                registry.async_remove(entity_id)
                _LOGGER.debug("Entità scenario id %s rimossa dal registry", rid)
                
                

        # Trova nuove entità da aggiungere
        new_entities = create_new_entities(scenarios)
        if new_entities:
            _LOGGER.debug("Aggiungo %d nuovi scenari", len(new_entities))
            async_add_entities(new_entities, update_before_add=True)
            # Le entità appena aggiunte non aggiornare subito (sono nuove)

        # Aggiorna solo le entità già esistenti prima del refresh
        for scenario in scenarios:
            sid = scenario.get("id")
            if sid in existing_ids:
                entity = _existing_scenario_entities[sid]
                old_name = entity._attr_name
                entity._scenario = scenario
                entity._attr_name = scenario.get("name", "Unknown Scenario")
                entity._attr_unique_id = f"came_scenario_{sid}"
                _LOGGER.debug("Aggiorno scenario id %s: nome da '%s' a '%s'", sid, old_name, entity._attr_name)
                if entity.hass is not None:
                    entity.async_write_ha_state()



    # Registra listener evento
    async def _dispatcher_handler():
        hass.async_create_task(handle_refresh_scenarios())

    async_dispatcher_connect(hass, "came_scenarios_refreshed", _dispatcher_handler)


class CameScenarioEntity(Scene):
    """Representation of a CAME scenario."""

    def __init__(self, scenario, manager: CameManager):
        self._manager = manager
        self._scenario = scenario
        self._attr_name = scenario.get("name", "Unknown Scenario")
        self._attr_unique_id = f"came_scenario_{scenario['id']}"
        self._unsub = None

    def activate(self, **kwargs):
        """Attiva lo scenario."""
        async def _activate():
            try:
                await self.hass.async_add_executor_job(
                    self._manager.scenario_manager.activate_scenario, self._scenario["id"]
                )
            except Exception as e:
                _LOGGER.error(f"Errore attivazione scenario {self._scenario['id']}: {e}", exc_info=True)
                raise                 
            self.async_write_ha_state()
            # Dopo 2 secondi, invia il segnale per rinfrescare gli scenari
            from homeassistant.helpers.dispatcher import async_dispatcher_send
            async_dispatcher_send(self.hass, "came_scenarios_refreshed")          
            
            

        asyncio.run_coroutine_threadsafe(_activate(), self.hass.loop)
 
  
       
    async def async_added_to_hass(self):
        """Collega l'entità agli aggiornamenti di stato."""
        from homeassistant.helpers.dispatcher import async_dispatcher_connect
        
        def handle_update(scenario_id: int, new_data: dict):
            if scenario_id == self._scenario["id"]:
                _LOGGER.debug("Ricevuto aggiornamento scenario %s: %s", scenario_id, new_data)
                asyncio.run_coroutine_threadsafe(
                    self.update_state(new_data), self.hass.loop
                )

        self._unsub = async_dispatcher_connect(self.hass, "came_scenario_update", handle_update)
        
    async def async_will_remove_from_hass(self):
        """Clean up dispatcher listener on removal."""
        if self._unsub:
            self._unsub()
            self._unsub = None
        
        
    async def update_state(self, new_data: dict):
        """Aggiorna lo stato dello scenario."""
        self._scenario.update(new_data)
        self.async_write_ha_state()
        
    @property
    def is_active(self):
        """Return True if scenario is active."""
        return self._scenario.get("scenario_status") == 2

    @property
    def available(self):
        """Return True if the scenario is available (even during transition)."""
        return self._scenario.get("scenario_status") is not None

    @property
    def state(self):
        """Return the current state of the scenario."""
        scenario_status = self._scenario.get("scenario_status")
        if scenario_status == 2:
            return STATE_ON
        elif scenario_status == 1:
            return "transition"
        elif scenario_status == 0:
            return STATE_OFF
        return STATE_UNAVAILABLE

    @property
    def extra_state_attributes(self):
        """Attributi aggiuntivi per lo scenario."""
        #_LOGGER.debug("Attributi scenario %s: %s", self._attr_name, self._scenario)
        return {
            "id": self._scenario["id"],
            "status": self._scenario.get("status", 0),
            "scenario_status": self._scenario.get("scenario_status", 0),
            "user_defined": self._scenario.get("user-defined", 0),
        }
