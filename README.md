*Please :star: this repo if you find it useful*

# Note: Beta version installation

<s>
Due to the fact that the `pycame` library and this integration are not published, automatic component installation is not available. You will have to install them manually.

To do this, you first need to install the `pycame` library on the system where Home Assistant is installed (_if it is installed inside a docker container or inside a virtual machine, the library MUST also be installed there_):

```bash
pip install -e git+https://github.com/Den901/ha_came.git@main#egg=pycame #or the place when you have the pycame library... :)
```



> **Note:** To upgrade an already installed package add option `--upgrade`, ie. `pip install --upgrade -e ...`

After installing the library, copy _all_ files from directory `custom_components/came` in this repository to the same directory in your Home Assistant configs.
After that read below how to configure `came` component.
</s>
***

# CAME integration component

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacs-shield]][hacs]

[![Community Forum][forum-shield]][forum]

_The `came` integration is the main integration to integrate CAME related platforms._



## Installation



### Install from HACS (recommended)

1. Have [HACS][hacs] installed, this will allow you to easily manage and track updates.
1. Search for "CAME".
1. Click Install below the found integration.
1. _If you want to configure component via Home Assistant UI..._\
    in the HA UI go to "Configuration" -> "Integrations" click "+" and search for "CAME".
1. _If you want to configure component via `configuration.yaml`..._\
    follow instructions below, then restart Home Assistant.
>

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
  token: RANDOM_STRING
```

## Configuration variables

**host**:\
  _(string) (Required)_\
  The hostname of your ETI/Domo server.

**username**:\
  _(string) (Required)_\
  The username for accessing your account.

**password**:\
  _(string) (Required)_\
  The password for accessing your account.

**token**:\
  _(string) (Required)_\
  The special token to access to API.

## Service

These services are available for the `came` component:

- force_update
- pull_devices

Devices state data and new devices will refresh automatically. If you want to refresh all devices information or get new devices related to your account manually, you can call the `force_update` or `pull_devices` service.

## Track updates

You can automatically track new versions of this component and update it by [HACS][hacs].

## Troubleshooting

To enable debug logs use this configuration:
```yaml
# Example configuration.yaml entry
logger:
  default: info
  logs:
    custom_components.came: debug
```
... then restart HA.

## Contributions are welcome!

This is an active open-source project. We are always open to people who want to
use the code or contribute to it.

We have set up a separate document containing our
[contribution guidelines](CONTRIBUTING.md).

Thank you for being involved! :heart_eyes:

## Authors & contributors

For a full list of all authors and contributors, check [the contributor's page][contributors].

## License

See separate [license file](LICENSE.md) for full text.

***

[component]: https://github.com/lrzdeveloper/ha-came
[commits-shield]: https://img.shields.io/github/commit-activity/y/lrzdeveloper/ha-came.svg?style=popout
[commits]: https://github.com/lrzdeveloper/ha-came/commits/master
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=popout
[hacs]: https://hacs.xyz
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=popout
[forum]: https://community.home-assistant.io/
[license]: https://github.com/lrzdeveloper/ha-came/blob/main/LICENSE.md
[license-shield]: https://img.shields.io/badge/license-Creative_Commons_BY--NC--SA_License-lightgray.svg?style=popout
[releases-shield]: https://img.shields.io/github/release/lrzdeveloper/ha-came.svg?style=popout
[releases]: https://github.com/lrzdeveloper/ha-came/releases
[releases-latest]: https://github.com/lrzdeveloper/ha-came/releases/latest
[report_bug]: https://github.com/lrzdeveloper/ha-came/issues/new?template=bug_report.md
[suggest_idea]: https://github.com/lrzdeveloper/ha-came/issues/new?template=feature_request.md
[contributors]: https://github.com/lrzdeveloper/ha-came/graphs/contributors
