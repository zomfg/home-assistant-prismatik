"""Config flow for Prismatik integration."""
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_PROFILE_NAME
)
from homeassistant.core import callback

from .const import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_PROFILE_NAME,
    DOMAIN
)

from .light import PrismatikClient


async def validate_input(data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    client = PrismatikClient(
        data[CONF_HOST],
        data[CONF_PORT],
        data[CONF_API_KEY]
    )
    await client.is_on()
    if not client.is_reachable:
        raise CannotConnect
    if not client.is_connected:
        raise InvalidApiKey


class PrismatikFlow: # pylint: disable=too-few-public-methods
    """Prismatik Flow."""

    def __init__(self):
        """Init."""
        self._host = None
        self._port = DEFAULT_PORT
        self._name = DEFAULT_NAME
        self._profile_name = DEFAULT_PROFILE_NAME
        self._apikey = ""
        self._is_import = False

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            self._host = str(user_input[CONF_HOST])
            self._port = user_input[CONF_PORT]
            self._name = str(user_input[CONF_NAME])
            self._profile_name = str(user_input[CONF_PROFILE_NAME])
            self._apikey = str(user_input[CONF_API_KEY])
            try:
                await validate_input(user_input)

                # host = self._host.replace(".", "_")
                # await self.async_set_unique_id(f"{host}_{self._port}")
                # self._abort_if_unique_id_configured()

                return self._async_create_entry(title=self._name, data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidApiKey:
                errors["base"] = "invalid_api_key"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self._host): str,
                vol.Optional(CONF_PORT, default=self._port): int,
                vol.Optional(CONF_API_KEY, default=self._apikey): str,
                vol.Optional(CONF_NAME, default=self._name): str,
                vol.Optional(CONF_PROFILE_NAME, default=self._profile_name): str
            }
        )
        return self._async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    def _async_create_entry(self, title, data):
        pass

    def _async_show_form(self, step_id, data_schema, errors):
        pass


@config_entries.HANDLERS.register(DOMAIN)
class PrismatikConfigFlow(PrismatikFlow, config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Prismatik."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_import(self, user_input=None):
        """Handle configuration by yaml file."""
        self._is_import = True
        return await self.async_step_user(user_input)

    def _async_create_entry(self, title, data):
        return self.async_create_entry(title=title, data=data)

    def _async_show_form(self, step_id, data_schema, errors):
        return self.async_show_form(step_id=step_id, data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Options flow."""
        return PrismatikOptionsFlowHandler(config_entry)

class PrismatikOptionsFlowHandler(PrismatikFlow, config_entries.OptionsFlow):
    """Prismatik config flow options handler."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()
        self._host = config_entry.data[CONF_HOST] if CONF_HOST in config_entry.data else None
        self._port = config_entry.data[CONF_PORT] if CONF_PORT in config_entry.data else DEFAULT_PORT
        self._name = config_entry.data[CONF_NAME] if CONF_NAME in config_entry.data else DEFAULT_NAME
        self._profile_name = config_entry.data[CONF_PROFILE_NAME] if CONF_PROFILE_NAME in config_entry.data else DEFAULT_PROFILE_NAME
        self._apikey = config_entry.data[CONF_API_KEY] if CONF_API_KEY in config_entry.data else ""

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    def _async_create_entry(self, title, data):
        return self.async_create_entry(title=title, data=data)

    def _async_show_form(self, step_id, data_schema, errors):
        return self.async_show_form(step_id=step_id, data_schema=data_schema, errors=errors)


class CannotConnect(exceptions.HomeAssistantError): # pylint: disable=too-few-public-methods
    """Error to indicate we cannot connect."""


class InvalidApiKey(exceptions.HomeAssistantError): # pylint: disable=too-few-public-methods
    """Error to indicate there is invalid API Key."""
