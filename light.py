"""Prismatik light."""
import logging
import re
import socket
import voluptuous as vol
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

    def __init__(self, hass, host, port, apikey):
        """Intialize."""
        self._hass = hass
        self._host = host
        self._port = port
        self._apikey = apikey
        self._color = None
        self._connected = False
        # self._connect()

    def _connect(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(1)
            self._sock.connect((self._host, self._port))
            # skip header
            header = self._sock.recv(512)
            # todo check header
            self._connected = True
            if self._apikey:
                self._do_cmd("apikey", self._apikey)
        except OSError:
            self._connected = False
            if self._sock:
                self._sock.close()
        return self._connected

    def _send(self, buffer):
        if self._connected is False:
            self._connect()
        if self._connected is False:
            return None

        _LOGGER.error("SENDING %s", buffer)
        try:
            self._sock.sendall(buffer.encode("ascii"))
            answer = self._sock.recv(4096).decode("ascii").strip()
        except OSError:
            _LOGGER.error("FAILED %s", buffer)
            self._sock.close()
            self._connected = False
            return None
        _LOGGER.error("RECEIVED %s", answer)
        return answer

    def _get_cmd(self, cmd):
        answer = self._send("get" + cmd + "\n")
        if answer is None:
            return None
        matches = re.compile(cmd + ":(\S+)").search(answer)
        if matches:
            return matches.group(1)
        return None

    def _set_cmd(self, cmd, value):
        answer = self._send("set" + cmd + ":" + str(value) + "\n")
        if answer is None:
            return False
        return True

    def _do_cmd(self, cmd, value=None):
        answer = self._send(cmd + (":" + str(value) if value else "") + "\n")
        if answer is None:
            return False
        return True

    def _set_rgb_color(self, rgb):
        leds = self.leds
        rgb_color = ','.join(map(lambda c: str(c), rgb))
        pixels = ';'.join(list(map(lambda led: str(led) + "-" + rgb_color, [i for i in range(1, leds + 1)])))
        self._set_cmd("color", pixels)

    @property
    def name(self):
        """Who me be."""
        return "ambilight"

    # @property
    # def unique_id(self):
    #     """ID me."""
    #     return "ambilight42"

    @property
    def is_on(self):
        """Is this thing on."""
        status = self._get_cmd("status")
        if status is not None:
            return (self._get_cmd("status") == "on")
        return None

    @property
    def leds(self):
        """Return leds of the light."""
        countleds = self._get_cmd("countleds")
        if countleds is not None:
            return int(countleds)
        return None

    @property
    def brightness(self):
        """Return brightness of the light."""
        brightness = self._get_cmd("brightness")
        if brightness is not None:
            return int(brightness) * 2.55
        return None

    @property
    def hs_color(self):
        """Return the color of the light."""
        return self._color

    @property
    def supported_features(self):
        """Flag supported features."""
        if self._connected:
            return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_EFFECT
        return 0

    @property
    def effect_list(self):
        """Profiles."""
        profiles = self._get_cmd("profiles")
        if profiles:
            return list(filter(None, profiles.split(';')))
        return None

    @property
    def effect(self):
        """Current profile."""
        profile = self._get_cmd("profile")
        if profile:
            return profile
        return None

    def turn_on(self, **kwargs):
        """Turn the light on."""
        if self._connected is False:
            if self._apikey is not None and self._do_cmd("apikey", self._apikey) is False:
                return
        if self._do_cmd("lock") is False:
            return
        self._set_cmd("mode", "moodlight")
        self._set_cmd("persistonunlock", "on")
        self._set_cmd("status", "on")
        _LOGGER.error("this bs OVER HERE %s", *kwargs)
        if ATTR_HS_COLOR in kwargs:
            # self._color = *kwargs[ATTR_HS_COLOR]
            rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            self._set_rgb_color(rgb)
        elif ATTR_BRIGHTNESS in kwargs:
            self._set_cmd("brightness", int(kwargs[ATTR_BRIGHTNESS] / 2.55))
        elif ATTR_EFFECT in kwargs:
            self._set_cmd("profile", kwargs[ATTR_EFFECT])

    def turn_off(self, **kwargs):
        """Turn the light off."""
        self._set_cmd("status", "off")
        self._do_cmd("unlock")
