"""
The CAME Integration Component.

For more details about this platform, please refer to the documentation at
https://github.com/Den901/ha-came
"""


# Base component constants

# Base component constants
NAME = "CAME ETI/Domo"
DOMAIN = "came"
VERSION = "1.1 - beta"
ATTRIBUTION = "Data provided by CAME ETI/Domo"
ISSUE_URL = "https://github.com/Den901/ha-came/issues"
DATA_YAML = f"{DOMAIN}__yaml"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have ANY issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# Icons

# Device classes

# Signals
SIGNAL_DISCOVERY_NEW = DOMAIN + "_discovery_{}"
SIGNAL_DELETE_ENTITY = DOMAIN + "_delete"
SIGNAL_UPDATE_ENTITY = DOMAIN + "_update"

# Services
SERVICE_PULL_DEVICES = "pull_devices"
SERVICE_FORCE_UPDATE = "force_update"

# Configuration and options
CONF_MANAGER = "manager"
CONF_CAME_LISTENER = "came_listener"
CONF_ENTRY_IS_SETUP = "entry_is_setup"
CONF_PENDING = "pending"

# Defaults

# Attributes
