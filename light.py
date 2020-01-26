"""Prismatik light."""
import logging
import re
import socket
import voluptuous as vol
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    #ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    #ATTR_TRANSITION,
    #EFFECT_COLORLOOP,
    #EFFECT_RANDOM,
    PLATFORM_SCHEMA,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    #SUPPORT_COLOR_TEMP,
    SUPPORT_EFFECT,
    #SUPPORT_FLASH,
    #SUPPORT_TRANSITION,
    Light,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_API_KEY
import homeassistant.helpers.config_validation as cv
import homeassistant.util.color as color_util
from .const import DEFAULT_PORT
#from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_API_KEY): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Awesome Light platform."""
    #pylint: disable=unused-argument
    # Assign configuration variables.
    # The configuration check takes care they are present.
    host = config[CONF_HOST]
    port = config[CONF_PORT]
    apikey = config.get(CONF_API_KEY)

    add_entities([PrismatikLight(hass, host, port, apikey)])

class PrismatikLight(Light):
    """Define a light."""

    def __init__(self, hass, host, port, apikey):
        """Intialize."""
        self._hass = hass
        self._host = host
        self._port = port
        self._apikey = apikey
        self._sock = None

    def _connect(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(1)
            self._sock.connect((self._host, self._port))
            # check header
            header = self._sock.recv(512).decode("ascii").strip()
            if re.match(r'^Lightpack', header) is None:
                _LOGGER.error("Bad API header")
                raise OSError()
        except OSError:
            if self._sock:
                self._sock.close()
            self._sock = None
        return self._sock is not None

    def _send(self, buffer):
        if self._sock is None and self._connect() is False:
            return None

        _LOGGER.error("SENDING %s", buffer)
        try:
            self._sock.sendall(buffer.encode("ascii"))
            answer = self._sock.recv(4096).decode("ascii").strip()
        except OSError:
            _LOGGER.error("FAILED %s", buffer)
            self._sock.close()
            self._sock = None
            return None
        _LOGGER.error("RECEIVED %s", answer)
        if answer == "not locked":
            if self._do_cmd("lock"):
                return self._send(buffer)
            _LOGGER.error("Could not lock Prismatik")
            answer = None
        if answer == "authorization required":
            if self._apikey and self._do_cmd("apikey", self._apikey):
                return self._send(buffer)
            _LOGGER.error("Could not lock Prismatik")
            answer = None
        return answer

    def _get_cmd(self, cmd):
        answer = self._send("get" + cmd + "\n")
        if answer is not None:
            matches = re.compile(cmd + r":(\S+)").match(answer)
            if matches:
                return matches.group(1)
        return None

    def _set_cmd(self, cmd, value):
        answer = self._send("set" + cmd + ":" + str(value) + "\n")
        return answer == "ok"

    def _do_cmd(self, cmd, value=None):
        answer = self._send(cmd + (":" + str(value) if value else "") + "\n")
        return re.compile(r"^(ok|" + cmd + r":success)$").match(answer) is not None

    def _set_rgb_color(self, rgb):
        leds = self.leds
        rgb_color = ','.join(map(str, rgb))
        pixels = ';'.join(list([str(i) + "-" + rgb_color for i in range(1, leds + 1)]))
        self._set_cmd("color", pixels)

    @property
    def name(self):
        """Return the name of the light."""
        return "Prismatik"

    @property
    def available(self):
        """Return availability of the light."""
        return self._sock is not None

    @property
    def is_on(self):
        """Is this thing on."""
        status = self._get_cmd("status")
        return status == "on" if status else None

    @property
    def leds(self):
        """Return leds of the light."""
        countleds = self._get_cmd("countleds")
        return int(countleds) if countleds else 0

    @property
    def brightness(self):
        """Return brightness of the light."""
        brightness = self._get_cmd("brightness")
        return int(brightness) * 2.55 if brightness else None

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_EFFECT

    @property
    def effect_list(self):
        """Profiles."""
        profiles = self._get_cmd("profiles")
        return list(filter(None, profiles.split(';'))) if profiles else None

    @property
    def effect(self):
        """Current profile."""
        return self._get_cmd("profile")

    def turn_on(self, **kwargs):
        """Turn the light on."""
        self._set_cmd("mode", "moodlight")
        self._set_cmd("persistonunlock", "on")
        self._set_cmd("status", "on")
        _LOGGER.error("TURNING ON WITH %s", *kwargs)
        if ATTR_HS_COLOR in kwargs:
            rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            self._set_rgb_color(rgb)
        elif ATTR_BRIGHTNESS in kwargs:
            self._set_cmd("brightness", int(kwargs[ATTR_BRIGHTNESS] / 2.55))
        elif ATTR_EFFECT in kwargs:
            self._set_cmd("profile", kwargs[ATTR_EFFECT])

    def turn_off(self, **kwargs):
        """Turn the light off."""
        #pylint: disable=unused-argument
        _LOGGER.error("TURNING OFF WITH %s", *kwargs)
        self._set_cmd("status", "off")
        self._do_cmd("unlock")
