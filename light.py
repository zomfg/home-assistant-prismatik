"""Prismatik light."""
import asyncio
import logging
import re
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import homeassistant.helpers.config_validation as cv
import homeassistant.util.color as color_util
import voluptuous as vol
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    PLATFORM_SCHEMA,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_EFFECT,
    LightEntity,
)
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_PROFILE_NAME,
)
from homeassistant.core import HomeAssistant

from .const import (
    CONNECTION_RETRY_ERRORS,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_PROFILE_NAME,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_API_KEY): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PROFILE_NAME, default=DEFAULT_PROFILE_NAME): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: Dict,
    async_add_entities: Callable[[List[LightEntity], bool], None],
    discovery_info: Optional[Any] = None,
) -> None:
    """Set up the Awesome Light platform."""
    # pylint: disable=unused-argument
    # Assign configuration variables.
    # The configuration check takes care they are present.
    address = (config[CONF_HOST], config[CONF_PORT])
    name = config[CONF_NAME]
    apikey = config.get(CONF_API_KEY)
    profile = config.get(CONF_PROFILE_NAME)
    light = PrismatikLight(hass, name, address, profile, apikey)
    await light.async_update()

    async_add_entities([light])


class PrismatikAPI(Enum):
    """Prismatik API literals."""

    CMD_LOCK = "lock"
    CMD_UNLOCK = "unlock"

    CMD_GET_COLOR = "colors"
    CMD_SET_COLOR = "color"

    CMD_APIKEY = "apikey"

    CMD_GET_PROFILE = "profile"
    CMD_SET_PROFILE = CMD_GET_PROFILE
    CMD_GET_PROFILES = "profiles"
    CMD_NEW_PROFILE = "newprofile"

    CMD_GET_BRIGHTNESS = "brightness"
    CMD_SET_BRIGHTNESS = CMD_GET_BRIGHTNESS

    CMD_GET_STATUS = "status"
    CMD_SET_STATUS = CMD_GET_STATUS

    CMD_GET_COUNTLEDS = "countleds"

    CMD_SET_PERSIST_ON_UNLOCK = "persistonunlock"

    CMD_GET_MODE = "mode"
    CMD_SET_MODE = CMD_GET_MODE

    AWR_OK = "ok"
    AWR_SUCCESS = "success"
    AWR_NOT_LOCKED = "not locked"
    AWR_AUTH_REQ = "authorization required"
    AWR_HEADER = "Lightpack API"

    STS_ON = "on"
    STS_OFF = "off"

    MOD_MOODLIGHT = "moodlight"

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: str) -> bool:
        # pylint: disable=comparison-with-callable
        return self.value == other


class PrismatikLight(LightEntity):
    """Representation of Prismatik."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        address: Tuple,
        profile: str,
        apikey: Optional[str],
    ) -> None:
        """Intialize."""
        self._hass = hass
        self._name = name
        self._address = address
        self._apikey = apikey
        self._tcpreader = None
        self._tcpwriter = None
        self._profile_name = profile
        self._retries = CONNECTION_RETRY_ERRORS

        self._state_is_on = False
        self._state_effect = None
        self._state_effect_list = None
        self._state_brightness = None
        self._state_hs_color = None

    def __del__(self) -> None:
        """Clean up."""
        self._disconnect()
        super()

    async def _connect(self) -> bool:
        """Connect to Prismatik server."""
        try:
            self._tcpreader, self._tcpwriter = await asyncio.open_connection(self._address[0], self._address[1])
        except (ConnectionRefusedError, TimeoutError):
        # except OSError:
            if self._retries > 0:
                self._retries -= 1
                _LOGGER.error("Could not connect to Prismatik")
            await self._disconnect()
        else:
            # check header
            data = await self._tcpreader.readline()
            header = data.decode("ascii").strip()
            _LOGGER.debug("GOT HEADER: %s", header)
            if re.match(fr"^{PrismatikAPI.AWR_HEADER}", header) is None:
                _LOGGER.error("Bad API header")
                await self._disconnect()
        return self._tcpwriter is not None

    async def _disconnect(self) -> None:
        """Disconnect from Prismatik server."""
        try:
            if self._tcpwriter:
                self._tcpwriter.close()
                await self._tcpwriter.wait_closed()
        except OSError:
            return
        finally:
            self._tcpreader = None
            self._tcpwriter = None

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect from update signal."""
        self._disconnect()

    async def _send(self, buffer: str) -> Optional[str]:
        """Send command to Prismatik server."""
        if self._tcpwriter is None and (await self._connect()) is False:
            return None

        _LOGGER.debug("SENDING: %s", buffer)
        try:
            self._tcpwriter.write(buffer.encode("ascii"))
            await self._tcpwriter.drain()
            await asyncio.sleep(0.01)
            data = await self._tcpreader.readline()
            answer = data.decode("ascii").strip()
        except OSError:
            if self._retries > 0:
                self._retries -= 1
                _LOGGER.error("Prismatik went away?")
            await self._disconnect()
            answer = None
        else:
            self._retries = CONNECTION_RETRY_ERRORS
            _LOGGER.debug("RECEIVED: %s", answer)
            if answer == PrismatikAPI.AWR_NOT_LOCKED:
                if await self._do_cmd(PrismatikAPI.CMD_LOCK):
                    return await self._send(buffer)
                _LOGGER.error("Could not lock Prismatik")
                answer = None
            if answer == PrismatikAPI.AWR_AUTH_REQ:
                if self._apikey and (await self._do_cmd(PrismatikAPI.CMD_APIKEY, self._apikey)):
                    return await self._send(buffer)
                _LOGGER.error("Prismatik authentication failed")
                answer = None
        return answer

    async def _get_cmd(self, cmd: PrismatikAPI) -> Optional[str]:
        """Execute get-command Prismatik server."""
        answer = await self._send(f"get{cmd}\n")
        matches = re.compile(fr"{cmd}:(.+)").match(answer or "")
        return matches.group(1) if matches else None

    async def _set_cmd(self, cmd: PrismatikAPI, value: Any) -> bool:
        """Execute set-command Prismatik server."""
        return await self._send(f"set{cmd}:{value}\n") == PrismatikAPI.AWR_OK

    async def _do_cmd(self, cmd: PrismatikAPI, value: Optional[Any] = None) -> bool:
        """Execute other command Prismatik server."""
        value = f":{value}" if value else ""
        answer = await self._send(f"{cmd}{value}\n")
        return (
            re.compile(
                fr"^(PrismatikAPI.AWR_OK|{cmd}:{PrismatikAPI.AWR_SUCCESS})$"
            ).match(answer or "")
            is not None
        )

    async def _set_rgb_color(self, rgb: Tuple) -> None:
        """Generate and execude setcolor command on Prismatik server."""
        leds = await self.leds
        rgb_color = ",".join(map(str, rgb))
        pixels = ";".join([f"{led}-{rgb_color}" for led in range(1, leds + 1)])
        await self._set_cmd(PrismatikAPI.CMD_SET_COLOR, pixels)

    @property
    def hs_color(self) -> Optional[List]:
        """Return the hue and saturation color value [float, float]."""
        return self._state_hs_color

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self._name

    @property
    def available(self) -> bool:
        """Return availability of the light."""
        return self._tcpwriter is not None

    @property
    def is_on(self) -> bool:
        """Return light status."""
        return self._state_is_on

    @property
    async def leds(self) -> int:
        """Return the led count of the light."""
        countleds = await self._get_cmd(PrismatikAPI.CMD_GET_COUNTLEDS)
        return int(countleds) if countleds else 0

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light between 0..255."""
        return self._state_brightness

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_EFFECT

    @property
    def effect_list(self) -> Optional[List]:
        """Return profile list."""
        return self._state_effect_list

    @property
    def effect(self) -> Optional[str]:
        """Return current profile."""
        return self._state_effect

    async def async_update(self) -> None:
        """Update light state."""
        self._state_is_on = (await self._get_cmd(PrismatikAPI.CMD_GET_STATUS)) == PrismatikAPI.STS_ON

        self._state_effect = await self._get_cmd(PrismatikAPI.CMD_GET_PROFILE)

        profiles = await self._get_cmd(PrismatikAPI.CMD_GET_PROFILES)
        self._state_effect_list = list(filter(None, profiles.split(";"))) if profiles else None

        brightness = await self._get_cmd(PrismatikAPI.CMD_GET_BRIGHTNESS)
        self._state_brightness = round(int(brightness) * 2.55) if brightness else None

        pixels = await self._get_cmd(PrismatikAPI.CMD_GET_COLOR)
        rgb = re.match(r"^\d+-(\d+),(\d+),(\d+);", pixels or "")
        if rgb is None:
            self._state_hs_color = None
        else:
            self._state_hs_color = color_util.color_RGB_to_hs(
                int(rgb.group(1)), int(rgb.group(2)), int(rgb.group(3))
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._set_cmd(PrismatikAPI.CMD_SET_STATUS, PrismatikAPI.STS_ON)
        if ATTR_EFFECT in kwargs:
            await self._set_cmd(PrismatikAPI.CMD_SET_PERSIST_ON_UNLOCK, PrismatikAPI.STS_OFF)
            await self._set_cmd(PrismatikAPI.CMD_SET_PROFILE, kwargs[ATTR_EFFECT])
        elif ATTR_BRIGHTNESS in kwargs:
            await self._set_cmd(
                PrismatikAPI.CMD_SET_BRIGHTNESS, round(kwargs[ATTR_BRIGHTNESS] / 2.55)
            )
            on_unlock = PrismatikAPI.STS_OFF
            if (await self._get_cmd(PrismatikAPI.CMD_GET_PROFILE)) == self._profile_name:
                on_unlock = PrismatikAPI.STS_ON
            await self._set_cmd(PrismatikAPI.CMD_SET_PERSIST_ON_UNLOCK, on_unlock)
        elif ATTR_HS_COLOR in kwargs:
            rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            await self._do_cmd(PrismatikAPI.CMD_NEW_PROFILE, self._profile_name)
            await self._set_cmd(PrismatikAPI.CMD_SET_PERSIST_ON_UNLOCK, PrismatikAPI.STS_ON)
            await self._set_rgb_color(rgb)
        await self._do_cmd(PrismatikAPI.CMD_UNLOCK)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # pylint: disable=unused-argument
        await self._set_cmd(PrismatikAPI.CMD_SET_STATUS, PrismatikAPI.STS_OFF)
