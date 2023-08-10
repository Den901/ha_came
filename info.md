*Please :star: this repo if you find it useful*

# Note: Alpha version installation

Due to the fact that the `pycame` library and this integration are not published, automatic component installation is not available. You will have to install them manually.

To do this, you first need to install the `pycame` library on the system where Home Assistant is installed (_if it is installed inside a docker container or inside a virtual machine, the library MUST also be installed there_):

```bash
pip install -e git+https://github.com/Den901/ha_came.git@main#egg=pycame #or the place when you have the pycame library... :)
```



> **Note:** To upgrade an already installed package add option `--upgrade`, ie. `pip install --upgrade -e ...`

After installing the library, copy _all_ files from directory `custom_components/came` in this repository to the same directory in your Home Assistant configs.
After that read below how to configure `came` component.

***

# CAME integration component


[![License][license-shield]][license]

[![hacs][hacs-shield]][hacs]

[![Community Forum][forum-shield]][forum]

_The `came` integration is the main integration to integrate CAME related platforms._



_Component to integrate with the pycame library._

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show sensors status`.
`climate` | Show and manage thermo zones.
`light` | show and manage the light entities.
`cover` | show and manage the covers.

![came-logo][came-logo]

## Features:

- Control lights, dimmer lights, RGB lights
- Manage analog sensors
- Manage climate entity
- manage openings

{% if not installed %}
## Installation

<strike>

### Install from HACS (recommended)

1. Have [HACS][hacs] installed, this will allow you to easily manage and track updates.
1. Search for "CAME".
1. Click Install below the found integration.
1. _If you want to configure component via Home Assistant UI..._\
    in the HA UI go to "Configuration" -> "Integrations" click "+" and search for "CAME".
1. _If you want to configure component via `configuration.yaml`..._\
    follow instructions below, then restart Home Assistant.
</strike>

### Manual installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `came`.
1. Download file `came.zip` from the [latest release section][releases-latest] in this repository.
1. Extract _all_ files from this archive you downloaded in the directory (folder) you created.
1. Restart Home Assistant
1. _If you want to configure component via Home Assistant UI..._\
    in the HA UI go to "Configuration" -> "Integrations" click "+" and search for "CAME".
1. _If you want to configure component via `configuration.yaml`..._\
    follow instructions below, then restart Home Assistant.

## Usage

To use this component in your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
came:
  host: YOUR_CAME_HOST
  username: YOUR_EMAIL
  password: YOUR_PASSWORD
  token: YOUR_TOKEN
```

<!---->

## Useful Links

- [Documentation][component]
- [Report a Bug][report_bug]
- [Suggest an idea][suggest_idea]



***

[component]: https://github.com/Den901/ha_came
[commits]: https://github.com/Den901/ha_came/commits/master
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=popout
[hacs]: https://hacs.xyz
[came-logo]: came-logo.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=popout
[forum]: https://community.home-assistant.io/
[license]: https://github.com/Den901/ha_came/LICENSE.md
[license-shield]: https://img.shields.io/badge/license-Creative_Commons_BY--NC--SA_License-lightgray.svg?style=popout
[user_profile]: https://github.com/Den901


