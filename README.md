# CAME ETI/Domo per Home Assistant

![CAME ETI/Domo](Came.png)

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]
[![HACS][hacs-shield]][hacs]
[![Community Forum][forum-shield]][forum]

Integrazione custom per collegare Home Assistant agli impianti CAME/BPT ETI/Domo e MiniSER tramite API locale.

La libreria `pycame` e' inclusa nel componente: non serve installare pacchetti Python esterni. La comunicazione avviene in locale verso ETI/Domo, con aggiornamento push/long-polling dove disponibile e polling dedicato per i misuratori energia.

## Stato della release

Versione corrente: `1.0.8`

Questa release completa la copertura delle principali famiglie ETI/Domo e prepara il pacchetto per HACS:

- repository aggiornato a `Den901/ha_came`;
- metadati HACS e manifest allineati alla versione `1.0.8`;
- token/keycode opzionale;
- supporto migliorato per endpoint locali `http://IP/domo/` e `http://IP/domo/test.html`;
- traduzioni russe obsolete rimosse;
- nuovo supporto nativo per centrali sicurezza come `alarm_control_panel`.

## Piattaforme supportate

| Piattaforma Home Assistant | Dispositivi ETI/Domo |
| --- | --- |
| `light` | Luci, dimmer, RGB quando esposti dall'impianto |
| `cover` | Tapparelle, aperture, tende, cancelli e automazioni di apertura |
| `climate` | Zone termiche, termostati, modalita', setpoint, umidita'/pressione quando disponibili |
| `switch` | Rele' generici, timer, irrigazione, rele' controllo carichi |
| `sensor` | Sensori analogici, misuratori energia, aree sicurezza, contatori controllo carichi |
| `binary_sensor` | Ingressi digitali, allarmi tecnici, ingressi/uscite sicurezza |
| `scene` | Scenari ETI/Domo con attivazione da Home Assistant |
| `camera` | Telecamere TVCC pubblicate da ETI/Domo |
| `media_player` | Zone audio/sound room |
| `alarm_control_panel` | Centrali sicurezza SICU/antintrusione |

## Funzioni principali

- Configurazione da interfaccia Home Assistant o da `configuration.yaml`.
- Login locale con username/password ETI/Domo.
- Token/keycode opzionale per impianti che lo richiedono.
- Scoperta automatica di piani, stanze e dispositivi.
- Aggiornamenti automatici tramite `status_update_req`.
- Refresh manuale dispositivi e stati tramite servizi Home Assistant.
- Gestione scenari: attivazione, creazione, cancellazione e refresh.
- Energia: potenza istantanea, sensore kWh calcolato, statistiche e reset storico.
- Timer settimanali e abilitazione/disabilitazione giorni.
- Irrigazione e controllo carichi.
- TVCC e audio locale.
- SICU/sicurezza: centrale, aree, ingressi, uscite, scenari, eventi, reset e autenticazione.

## Dettaglio funzionalita'

### Luci

Le luci ETI/Domo vengono pubblicate come entita' `light`. L'integrazione gestisce accensione e spegnimento e, quando il dispositivo lo espone nelle API, anche regolazione intensita' e varianti dimmer/RGB.

### Tapparelle, aperture e cancelli

Le aperture vengono pubblicate come `cover`. Sono pensate per tapparelle, tende, serrande, cancelli e automazioni simili esposte da ETI/Domo. Home Assistant puo' quindi comandare apertura, chiusura e stop quando supportato dal dispositivo.

### Rele'

I rele' generici vengono pubblicati come `switch`. Oltre al comando standard on/off sono disponibili servizi dedicati per attivazione per nome e attivazione temporizzata.

### Ingressi digitali e allarmi tecnici

Gli ingressi digitali vengono pubblicati come `binary_sensor`. Sono utili per stati on/off, contatti, segnalazioni tecniche e allarmi tecnici. Il servizio `came.digitalin_ack` permette di confermare/azzerare un ingresso quando previsto dall'impianto.

### Clima e termoregolazione

Le zone termiche vengono pubblicate come `climate`. L'integrazione legge e aggiorna stato, temperatura, setpoint e modalita' disponibili. Quando ETI/Domo espone sensori collegati alla termoregolazione, vengono aggiunti anche sensori temperatura, umidita' o pressione.

### Sensori analogici

I sensori analogici vengono pubblicati come `sensor`, mantenendo unita' di misura e classe dispositivo quando riconoscibili. Coprono grandezze come temperatura, umidita', pressione o valori analogici personalizzati dell'impianto.

### Energia

I misuratori energia vengono pubblicati come sensori di potenza e come sensori energia in kWh calcolati da Home Assistant. Sono disponibili anche servizi per statistiche energia e reset dello storico misure ETI/Domo.

### Scenari

Gli scenari ETI/Domo vengono pubblicati come `scene`. Puoi attivarli da Home Assistant e usare i servizi per crearli, eliminarli, ricaricarli o attivarli per nome.

### Timer

I timer vengono pubblicati come `switch`. I servizi dedicati permettono di abilitare/disabilitare i giorni della settimana e sostituire la tabella oraria.

### Irrigazione

I settori o programmi irrigazione vengono pubblicati come `switch`, con servizio dedicato per abilitare o disabilitare la schedulazione.

### Controllo carichi

Il controllo carichi espone misuratori come `sensor` e rele' di carico come `switch`, cosi' puoi monitorare consumi e comandare le uscite gestite da ETI/Domo.

### Telecamere TVCC

Le telecamere TVCC configurate in ETI/Domo vengono pubblicate come `camera`, quando presenti nelle API del gateway.

### Audio

Le zone audio/sound room vengono pubblicate come `media_player`, con i controlli disponibili in base a quanto espone ETI/Domo.

## Sicurezza e antifurto

Le centrali sicurezza vengono ora esposte come entita' `alarm_control_panel`.

Dal pannello standard Home Assistant puoi:

- vedere lo stato generale della centrale;
- disinserire tutte le aree;
- inserire tutte le aree in modalita' `armed_away`;
- vedere `armed_custom_bypass` quando solo alcune aree risultano inserite.

Per inserimenti parziali o comandi specifici ETI/Domo usa il servizio avanzato:

```yaml
service: came.sicu_areas_set_status
data:
  central_id: 0
  status_vector: "1103"
  code: "1234"
```

Nel `status_vector` ogni carattere corrisponde a un'area:

- `0`: non inserire/disinserita;
- `1`: inserisci;
- `2`: inserisci forzata;
- `3`: lascia invariata.

Sono disponibili anche servizi per autenticazione centrale, inclusione/esclusione ingressi, uscite sicurezza, scenari sicurezza, lista eventi e reset allarme.

## Installazione da HACS

1. Installa HACS se non e' gia' presente.
2. In HACS aggiungi questo repository come custom repository:
   `https://github.com/Den901/ha_came`
3. Tipo repository: `Integration`.
4. Cerca `CAME ETI/Domo`.
5. Installa l'integrazione.
6. Riavvia Home Assistant.
7. Vai in **Impostazioni > Dispositivi e servizi > Aggiungi integrazione** e cerca `CAME`.

## Installazione manuale

1. Scarica `came.zip` dalla sezione [Release][releases-latest].
2. Estrai il contenuto nella cartella `custom_components/came` della configurazione Home Assistant.
3. Riavvia Home Assistant.
4. Aggiungi l'integrazione dalla UI oppure usa la configurazione YAML.

## Configurazione

Configurazione consigliata da UI:

- Host/IP: ad esempio `192.168.1.250` oppure `http://192.168.1.250`;
- Username: utente ETI/Domo;
- Password: password ETI/Domo;
- Token/keycode: lascia vuoto se l'impianto non lo richiede.

Configurazione YAML alternativa:

```yaml
came:
  host: 192.168.1.250
  username: admin
  password: admin
  token: ""
```

Nel campo `host` puoi usare anche un URL completo, ad esempio `http://192.168.1.250/domo/`, mantenendo le credenziali reali del tuo impianto.

## Servizi principali

| Servizio | Uso |
| --- | --- |
| `came.force_update` | forza l'aggiornamento degli stati |
| `came.pull_devices` | rilegge la lista dispositivi da ETI/Domo |
| `came.create_scenario` | crea uno scenario utente |
| `came.delete_scenario` | elimina uno scenario |
| `came.refresh_scenarios` | ricarica gli scenari |
| `came.activate_scenario_by_name` | attiva uno scenario per nome |
| `came.relay_activation_by_name` | accende/spegne un rele' per nome |
| `came.relay_timed` | attiva un rele' temporizzato |
| `came.digitalin_ack` | conferma un ingresso digitale/allarme tecnico |
| `came.get_datetime` | legge data/ora ETI/Domo e pubblica evento |
| `came.zoneinfo_list` | legge le timezone disponibili |
| `came.energy_stat` | richiede statistiche energia |
| `came.energy_reset_store` | resetta lo storico energia ETI/Domo |
| `came.timer_enable_day` | abilita/disabilita un giorno timer |
| `came.timer_set` | sostituisce la tabella oraria timer |
| `came.irrigation_set_enabled` | abilita/disabilita irrigazione |
| `came.map_count` | legge il numero mappe |
| `came.map_descr` | legge la descrizione di una mappa |

Servizi sicurezza:

| Servizio | Uso |
| --- | --- |
| `came.sicu_auth` | autentica una centrale sicurezza |
| `came.sicu_areas_set_status` | imposta il vettore di inserimento aree |
| `came.sicu_input_set` | include/esclude uno o piu' ingressi |
| `came.sicu_multi_input_areas_set` | include/esclude ingressi aperti per aree |
| `came.sicu_output_set` | attiva/disattiva/toggle uscita sicurezza |
| `came.sicu_scenario_set` | esegue uno scenario sicurezza |
| `came.sicu_reset` | resetta lo stato allarme |
| `came.sicu_events_list` | legge eventi sicurezza e pubblica evento |
| `came.sicu_events_clear` | cancella eventi sicurezza |

## Eventi pubblicati

Alcuni servizi restituiscono la risposta ETI/Domo come evento Home Assistant:

- `came_datetime_response`
- `came_zoneinfo_response`
- `came_energy_stat_response`
- `came_sicu_auth_response`
- `came_sicu_areas_set_status_response`
- `came_sicu_input_set_response`
- `came_sicu_multi_input_areas_set_response`
- `came_sicu_output_set_response`
- `came_sicu_scenario_set_response`
- `came_sicu_reset_response`
- `came_sicu_events_response`
- `came_map_count_response`
- `came_map_descr_response`

## Risoluzione problemi

Abilita i log debug:

```yaml
logger:
  default: info
  logs:
    custom_components.came: debug
```

Suggerimenti rapidi:

- Se Home Assistant dice password errata ma la password e' corretta, controlla che ETI/Domo risponda su HTTP/porta 80.
- Se il token/keycode non e' richiesto dal tuo impianto, lascialo vuoto.
- Se usi un URL completo, prova sia `http://IP/domo/` sia `http://IP/domo/test.html`.
- Dopo un aggiornamento firmware ETI/Domo, riavvia Home Assistant e usa `came.pull_devices`.

## Contribuire

Segnala bug o richieste nella pagina [Issues][report_bug].

## Licenza

Vedi [LICENSE.md](LICENSE.md).

## Supporto

Se il progetto ti e' utile puoi offrire una birra via PayPal:

[![Donate](https://www.paypalobjects.com/en_US/IT/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/donate?business=GTYL35E47Y2AN&amount=5&currency_code=EUR)

[component]: https://github.com/Den901/ha_came
[commits-shield]: https://img.shields.io/github/commit-activity/y/Den901/ha_came.svg?style=popout
[commits]: https://github.com/Den901/ha_came/commits/main
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=popout
[hacs]: https://hacs.xyz
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=popout
[forum]: https://community.home-assistant.io/
[license]: https://github.com/Den901/ha_came/blob/main/LICENSE.md
[license-shield]: https://img.shields.io/badge/license-Creative_Commons_BY--NC--SA-lightgray.svg?style=popout
[releases-shield]: https://img.shields.io/github/release/Den901/ha_came.svg?style=popout
[releases]: https://github.com/Den901/ha_came/releases
[releases-latest]: https://github.com/Den901/ha_came/releases/latest
[report_bug]: https://github.com/Den901/ha_came/issues
