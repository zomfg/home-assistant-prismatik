"""The Prismatik integration."""
# import asyncio
# import logging
# import voluptuous as vol

# from homeassistant.config_entries import ConfigEntry
# from homeassistant.core import HomeAssistant
# #from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
# from homeassistant.const import (
#     CONF_HOST,
#     CONF_PORT,
# #    CONF_TOKEN,
# )
# import homeassistant.helpers.config_validation as cv
# from .const import DEFAULT_PORT
# from .const import DOMAIN

# _LOGGER = logging.getLogger(__name__)

# CONFIG_SCHEMA = vol.Schema(
#     {
#         DOMAIN: vol.Schema(
#             {
#                 vol.Required(CONF_HOST): cv.string,
#                 vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
# #                vol.Optional(CONF_TOKEN, default=""): cv.string,
#             }
#         )
#     },
#     extra=vol.ALLOW_EXTRA
# )

# # TODO List the platforms that you want to support.
# # For your initial PR, limit it to 1 platform.
# PLATFORMS = ["light"]


# async def async_setup(hass: HomeAssistant, config: dict):
#     """Set up the Prismatik component."""
#     conf = config[DOMAIN]
#     prismatik = hass.data[DOMAIN] = PrismatikLight(
#         hass,
#         conf[CONF_HOST],
#         conf[CONF_PORT],
# #        None,
# #       conf[CONF_TOKEN],
#     )
#     return True


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
#     """Set up Prismatik from a config entry."""
#     # TODO Store an API object for your platforms to access
#     # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

#     for component in PLATFORMS:
#         hass.async_create_task(
#             hass.config_entries.async_forward_entry_setup(entry, component)
#         )

#     return True


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
#     """Unload a config entry."""
#     unload_ok = all(
#         await asyncio.gather(
#             *[
#                 hass.config_entries.async_forward_entry_unload(entry, component)
#                 for component in PLATFORMS
#             ]
#         )
#     )
#     if unload_ok:
#         hass.data[DOMAIN].pop(entry.entry_id)

#     return unload_ok

# class PrismatikLight:
#     """Define a light."""

#     def __init__(self, hass, host, port):
#         """Intialize."""
#         _LOGGER.debug("this bs %s:%s", host, port)
#         self._hass = hass
#         self._host = host
#         self._port = port
#         # self._sock = socket.socket(socket.)
# #        self._token = token
