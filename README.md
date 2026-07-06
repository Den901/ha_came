# CAME ETI/Domo 1.0.11

Release di consolidamento per portare l'integrazione CAME ETI/Domo a una versione pronta per HACS, con copertura molto piu' ampia delle API locali ETI/Domo e supporto nativo alle centrali sicurezza.

## In evidenza

- Pacchetto pronto per HACS come custom repository: `https://github.com/Den901/ha_came`.
- Versione integrazione allineata a `1.0.11` in manifest e costanti interne.
- Libreria `pycame` integrata nel componente, senza installazioni Python esterne.
- Token/keycode reso opzionale.
- Gestione host piu' flessibile: IP semplice, URL completo, `/domo/` e `/domo/test.html`.
- Errori di connessione piu' chiari: timeout, impossibile connettersi, credenziali non valide e rifiuto API non vengono piu' tutti scambiati per "password errata".
- Traduzioni russe obsolete rimosse.
- README e pagina informativa HACS riscritti in italiano.

## Funzioni gia' presenti e mantenute

- Luci: accensione, spegnimento e gestione dispositivi luce esposti da ETI/Domo.
- Aperture: tapparelle, tende, cancelli e automazioni di apertura come `cover`.
- Clima: termostati e zone termiche come `climate`.
- Rele' generici: gestione come `switch`.
- Ingressi digitali/allarmi tecnici come `binary_sensor`.
- Sensori analogici come `sensor`.
- Scenari ETI/Domo come `scene`.
- Servizi base `came.force_update` e `came.pull_devices`.
- Configurazione da UI Home Assistant e import da `configuration.yaml`.
- Aggiornamenti automatici tramite richiesta stato ETI/Domo.

## Nuove famiglie e copertura API completata

- Telecamere TVCC come piattaforma `camera`.
- Zone audio/sound room come `media_player`.
- Misuratori energia come sensori potenza e sensori energia kWh.
- Servizi energia: statistiche e reset storico misure.
- Timer settimanali come `switch`, con servizi per giorni e tabelle orarie.
- Irrigazione come `switch`, con servizio di abilitazione/disabilitazione.
- Controllo carichi: misuratori e rele'.
- Mappe ETI/Domo: conteggio e descrizione mappe tramite servizi.
- Data/ora e timezone ETI/Domo tramite servizi dedicati.
- Gestione avanzata scenari: creazione, cancellazione, refresh e attivazione per nome.

## Sicurezza / SICU

La centrale sicurezza non viene piu' esposta solo come sensore generico: dalla 1.0.11 e' disponibile anche come `alarm_control_panel` Home Assistant.

Supporto incluso:

- centrale sicurezza come pannello antifurto;
- stato `disarmed` quando tutte le aree sono disinserite;
- stato `armed_away` quando tutte le aree sono inserite;
- stato `armed_custom_bypass` quando solo alcune aree sono inserite;
- comando standard Home Assistant per disinserire tutte le aree;
- comando standard Home Assistant per inserire tutte le aree;
- aree sicurezza come sensori;
- ingressi sicurezza come `binary_sensor`;
- uscite sicurezza come `binary_sensor`;
- autenticazione centrale tramite servizio;
- inserimento aree con `status_vector`;
- inclusione/esclusione ingressi;
- gestione ingressi aperti per area;
- attivazione/disattivazione/toggle uscite sicurezza;
- esecuzione scenari sicurezza;
- reset stato allarme;
- lettura e cancellazione eventi sicurezza.

Il pannello Home Assistant usa il comportamento piu' sicuro e prevedibile: inserimento totale e disinserimento totale. Per inserimenti parziali resta disponibile il servizio avanzato `came.sicu_areas_set_status`.

## Servizi disponibili

Servizi generali:

- `came.force_update`
- `came.pull_devices`
- `came.create_scenario`
- `came.delete_scenario`
- `came.refresh_scenarios`
- `came.activate_scenario_by_name`
- `came.relay_activation_by_name`
- `came.relay_timed`
- `came.digitalin_ack`
- `came.get_datetime`
- `came.zoneinfo_list`
- `came.energy_stat`
- `came.energy_reset_store`
- `came.timer_enable_day`
- `came.timer_set`
- `came.irrigation_set_enabled`
- `came.map_count`
- `came.map_descr`

Servizi sicurezza:

- `came.sicu_auth`
- `came.sicu_areas_set_status`
- `came.sicu_input_set`
- `came.sicu_multi_input_areas_set`
- `came.sicu_output_set`
- `came.sicu_scenario_set`
- `came.sicu_reset`
- `came.sicu_events_list`
- `came.sicu_events_clear`

## Correzioni importanti

- Migliorata la diagnosi quando ETI/Domo non risponde: una porta 80 non raggiungibile non viene piu' presentata come credenziali errate.
- Invio header `Authorization` solo quando token/keycode e' configurato.
- Compatibilita' migliorata con impianti che espongono solo HTTP locale.
- Riconosciuti gli alias feature `timers`, `sicu`, `irrig`, `cameras` e `loadsctrl`, evitando warning "Unsupported feature type" dopo aggiornamento da HACS.
- Normalizzate le unita' misura temperatura ricevute con codifica errata, evitando errori HomeKit.
- Metadati repository aggiornati da sorgenti precedenti a `Den901/ha_came`.
- Pacchetto HACS ripulito da file non necessari e traduzioni obsolete.

## Pacchetto release

- Tag consigliato: `1.0.11`
- Asset da allegare alla release GitHub: `came.zip`
- Repository HACS custom: `https://github.com/Den901/ha_came`
- Tipo repository HACS: `Integration`

## Note operative

Dopo l'aggiornamento:

1. Riavvia Home Assistant.
2. Apri l'integrazione CAME ETI/Domo.
3. Se hai aggiornato anche ETI/Domo o hai ripristinato la configurazione, esegui `came.pull_devices`.
4. Se usi SICU, controlla il nuovo pannello `alarm_control_panel` e verifica il codice centrale prima di inserirlo in automazioni.
