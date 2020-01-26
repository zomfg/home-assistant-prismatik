"""Prismatik light."""
import logging
import re
import socket
from typing import Optional
import voluptuous as vol
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    # ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    # ATTR_TRANSITION,
    # EFFECT_COLORLOOP,
    # EFFECT_RANDOM,
    PLATFORM_SCHEMA,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    # SUPPORT_COLOR_TEMP,
    SUPPORT_EFFECT,
    # SUPPORT_FLASH,
    # SUPPORT_TRANSITION,
    Light,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_API_KEY
import homeassistant.helpers.config_validation as cv
import homeassistant.util.color as color_util
from .const import DEFAULT_PORT

# from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_API_KEY): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Awesome Light platform."""
    # pylint: disable=unused-argument
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

    def _connect(self) -> bool:
        """Connect to Prismatik server."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(0.1)
            self._sock.connect((self._host, self._port))
            # check header
            header = self._sock.recv(512).decode("ascii").strip()
            if re.match(r"^Lightpack", header) is None:
                _LOGGER.error("Bad API header")
                raise OSError()
        except OSError:
            self._disconnect()
        return self._sock is not None

    def _disconnect(self) -> None:
        """Disconnect from Prismatik server."""
        if self._sock:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        self._sock = None

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect from update signal."""
        self._disconnect()

    def _send(self, buffer: str) -> Optional[str]:
        """Send command to Prismatik server."""
        if self._sock is None and self._connect() is False:
            return None

        # _LOGGER.error("SENDING %s", buffer)
        try:
            self._sock.sendall(buffer.encode("ascii"))
            answer = self._sock.recv(4096).decode("ascii").strip()
        except OSError:
            # _LOGGER.error("FAILED %s", buffer)
            self._disconnect()
            return None
        # _LOGGER.error("RECEIVED %s", answer)
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

    def _get_cmd(self, cmd: str) -> Optional[str]:
        """Execute get-command Prismatik server."""
        answer = self._send("get" + cmd + "\n")
        if answer is not None:
            matches = re.compile(cmd + r":(\S+)").match(answer)
            if matches:
                return matches.group(1)
        return None

    def _set_cmd(self, cmd: str, value: any) -> bool:
        """Execute set-command Prismatik server."""
        return self._send("set" + cmd + ":" + str(value) + "\n") == "ok"

    def _do_cmd(self, cmd: str, value: Optional[any] = None) -> bool:
        """Execute other command Prismatik server."""
        answer = self._send(cmd + (":" + str(value) if value else "") + "\n")
        return re.compile(r"^(ok|" + cmd + r":success)$").match(answer) is not None

    def _set_rgb_color(self, rgb: tuple) -> None:
        """Generate and execude setcolor command on Prismatik server."""
        leds = self.leds
        rgb_color = ",".join(map(str, rgb))
        pixels = ";".join(list([str(i) + "-" + rgb_color for i in range(1, leds + 1)]))
        self._set_cmd("color", pixels)

    @property
    def hs_color(self) -> Optional[list]:
        """Return first pixel color on Prismatik."""
        pixels = self._get_cmd("colors")
        if pixels is None:
            return None
        rgb = re.match(r"^\d+-(\d+),(\d+),(\d+);", pixels)
        if rgb is None:
            return None
        return color_util.color_RGB_to_hs(
            int(rgb.group(1)), int(rgb.group(2)), int(rgb.group(3))
        )

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return "Prismatik"

    @property
    def available(self) -> bool:
        """Return availability of the light."""
        return self._sock is not None

    @property
    def is_on(self) -> bool:
        """Is this thing on."""
        return self._get_cmd("status") == "on"

    @property
    def leds(self) -> int:
        """Return leds of the light."""
        countleds = self._get_cmd("countleds")
        return int(countleds) if countleds else 0

    @property
    def brightness(self) -> Optional[int]:
        """Return brightness of the light."""
        brightness = self._get_cmd("brightness")
        return int(brightness) * 2.55 if brightness else None

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_EFFECT

    @property
    def effect_list(self) -> Optional[list]:
        """Profiles."""
        profiles = self._get_cmd("profiles")
        return list(filter(None, profiles.split(";"))) if profiles else None

    @property
    def effect(self) -> Optional[str]:
        """Current profile."""
        return self._get_cmd("profile")

    def turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        self._set_cmd("mode", "moodlight")
        self._set_cmd("persistonunlock", "on")
        self._set_cmd("status", "on")
        # _LOGGER.error("TURNING ON WITH %s", *kwargs)
        if ATTR_HS_COLOR in kwargs:
            rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            self._set_rgb_color(rgb)
        elif ATTR_BRIGHTNESS in kwargs:
            self._set_cmd("brightness", int(kwargs[ATTR_BRIGHTNESS] / 2.55))
        elif ATTR_EFFECT in kwargs:
            self._set_cmd("profile", kwargs[ATTR_EFFECT])

    def turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        # pylint: disable=unused-argument
        # _LOGGER.error("TURNING OFF WITH %s", *kwargs)
        self._set_cmd("status", "off")
        self._do_cmd("unlock")
