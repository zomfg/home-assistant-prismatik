"""Prismatik light."""
import logging
import re
import socket
import voluptuous as vol
from pprint import pprint
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_LIGHT,
    BinarySensorDevice,
)

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
#    ATTR_COLOR_TEMP,
   ATTR_EFFECT,
   ATTR_HS_COLOR,
#    ATTR_TRANSITION,
#    EFFECT_COLORLOOP,
#    EFFECT_RANDOM,
    PLATFORM_SCHEMA,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
#    SUPPORT_COLOR_TEMP,
   SUPPORT_EFFECT,
#    SUPPORT_FLASH,
#    SUPPORT_TRANSITION,
    Light,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_API_KEY
import homeassistant.helpers.config_validation as cv
from .const import DEFAULT_PORT
from .const import DOMAIN
import homeassistant.util.color as color_util

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_API_KEY): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Awesome Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    apikey = config.get(CONF_API_KEY)

    add_entities([PrismatikLight(hass, host, port, apikey)])
    # Setup connection with devices/cloud
    # hub = awesomelights.Hub(host, username, password)

    # Verify that passed in configuration works
    # if not hub.is_valid_login():
    #     _LOGGER.error("Could not connect to AwesomeLight hub")
    #     return

    # Add devices
    # add_entities(AwesomeLight(light) for light in hub.lights())

class PrismatikLight(Light):
    """Define a light."""
    # TODO: LED range as light
    def __init__(self, hass, host, port, apikey):
        """Intialize."""
        _LOGGER.error("this bs %s:%s", host, port)
        self._hass = hass
        self._host = host
        self._port = port
        self._color = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(1)
        self._sock.connect((self._host, self._port))
        # skip header
        header = self._sock.recv(1024)
        # todo check header
        # self._sock.send(b"getcountleds\n")

#        self._token = token

        # getcountleds
        # leds = int(self._get_someshit("countleds"))

        self._do_someshit("lock")
        self._set_someshit("mode", "moodlight")
        self._set_someshit("persistonunlock", "on")
        # # setcolor
        # color = '255,0,0'
        # pixels = ';'.join(list(map(lambda led: str(led) + "-" + color, [i for i in range(1, leds + 1)])))
        # self._set_someshit("color", pixels)

        # # setbrightness
        # bri = int(150 * 100 / 255)
        # self._set_someshit("brightness", bri)

        # self._do_someshit("unlock")

    def _get_someshit(self, someshit):
        cmd = "get" + someshit + "\n"
        _LOGGER.error("GETTING SHIT %s", cmd)
        self._sock.send(cmd.encode())
        answer = self._sock.recv(1024).decode("ascii").strip()
        _LOGGER.error("GOT SHIT %s", answer)
        matches = re.compile(someshit+":(\S+)").search(answer)
        return matches.group(1)

    def _set_someshit(self, someshit, value):
        cmd = "set" + someshit + ":" + str(value) + "\n"
        _LOGGER.error("SETTING SHIT %s", cmd)
        self._sock.send(cmd.encode("ascii"))
        answer = self._sock.recv(1024).decode("ascii").strip()
        return True

    def _do_someshit(self, someshit):
        cmd = someshit + "\n"
        _LOGGER.error("DOING SHIT %s", cmd)
        self._sock.send(cmd.encode("ascii"))
        answer = self._sock.recv(1024).decode("ascii")
        return True

    @property
    def name(self):
        """Who me be."""
        return "ambilight"

    # @property
    # def unique_id(self):
    #     """ID me."""
    #     return "ambilight42"

    # @property
    # def entity_id(self):
    #     """ID but entity"""
    #     return f"light.{self.name}"
    
    # @entity_id.setter
    # def entity_id(self, eid):
    #     """Set some id"""
    #     self._entity_id
    # @property
    # def should_poll(self):
    #     """We can read the device state, so poll."""
    #     return True
    @property
    def is_on(self):
        """Is this thing on."""
        return (self._get_someshit("status") == "on")

    @property
    def leds(self):
        """Return leds of the light."""
        return int(self._get_someshit("countleds"))

    @property
    def brightness(self):
        """Return brightness of the light."""
        return int(self._get_someshit("brightness")) * 2.55

    @property
    def hs_color(self):
        """Return the color of the light."""
        return self._color

    @property
    def supported_features(self):
        """Flag supported features."""
        # if self._color:
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_EFFECT
        # return SUPPORT_BRIGHTNESS

    @property
    def effect_list(self):
        """Profiles."""
        profiles = self._get_someshit("profiles")
        return list(filter(None, profiles.split(';')))

    @property
    def effect(self):
        """Current profile."""
        return self._get_someshit("profile")

    # @property
    # def capability_attributes(self):
    #     """Return capability attributes."""
    #     data = {}
        # supported_features = self.supported_features

        # if supported_features & SUPPORT_COLOR_TEMP:
        #     data[ATTR_MIN_MIREDS] = self.min_mireds
        #     data[ATTR_MAX_MIREDS] = self.max_mireds

        # if supported_features & SUPPORT_EFFECT:
        #     data[ATTR_EFFECT_LIST] = self.effect_list

        # return data

    # @property
    # def device_class(self):
    #     return DEVICE_CLASS_LIGHT

    # @property
    # def device_info(self):
    #     """Return a device description for device registry."""
    #     return {
    #         "identifiers": {(DOMAIN, self.unique_id)},
    #         "manufacturer": "1337h4x0r",
    #         "model": "prismatik",
    #         "name": self.name,
    #     }

    # @property
    # def entity_registry_enabled_default(self):
    #     """Disable Button LEDs by default."""
    #     # if self._module.light_is_buttonled(self._channel):
    #     #     return False
    #     return True

    # @property
    # def unit_of_measurement(self):
    #     return None

    def _set_rgb_color(self, rgb):
        leds = self.leds
        rgb_color = ','.join(map(lambda c: str(c), rgb))
        pixels = ';'.join(list(map(lambda led: str(led) + "-" + rgb_color, [i for i in range(1, leds + 1)])))
        _LOGGER.error("this bs OVER HERE %s", pixels)
        self._set_someshit("color", pixels)

    def turn_on(self, **kwargs):
        """Turn the light on."""
        self._do_someshit("lock")
        self._set_someshit("status", "on")
        _LOGGER.error("this bs OVER HERE %s", *kwargs)
        # pprint(vars(*kwargs))
        if ATTR_HS_COLOR in kwargs:
        # and self._color:
            rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            self._set_rgb_color(rgb)
        elif ATTR_BRIGHTNESS in kwargs:
            self._set_someshit("brightness", int(kwargs[ATTR_BRIGHTNESS] / 2.55))
        elif ATTR_EFFECT in kwargs:
            self._set_someshit("profile", kwargs[ATTR_EFFECT])
        # else:
            #self._do_someshit("unlock")

    def turn_off(self, **kwargs):
        """Turn the light off."""
        # self._set_rgb_color((0,0,0))
        self._set_someshit("status", "off")
        self._do_someshit("unlock")

    def update(self):
        """Update teh light."""