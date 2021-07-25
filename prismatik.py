"""Prismatik API client"""

import asyncio
import logging
import re
from enum import Enum
from typing import Any, List, Optional, Tuple

from .const import CONNECTION_RETRY_ERRORS

_LOGGER = logging.getLogger(__name__)

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
        # pylint: disable=invalid-str-returned
        return self.value

    def __eq__(self, other: str) -> bool:
        # pylint: disable=comparison-with-callable
        return self.value == other


class PrismatikClient:
    """Prismatik Client interface"""

    def __init__(
        self,
        host: str,
        port: int,
        apikey: Optional[str],
    ) -> None:
        """Intialize."""
        self._host = host
        self._port = port
        self._apikey = apikey
        self._tcpreader = None
        self._tcpwriter = None
        self._retries = CONNECTION_RETRY_ERRORS
        self._api_connected = False

    def __del__(self) -> None:
        """Clean up."""
        self.disconnect()

    async def _connect(self) -> bool:
        """Connect to Prismatik server."""
        try:
            self._tcpreader, self._tcpwriter = await asyncio.open_connection(self._host, self._port)
        except (ConnectionRefusedError, TimeoutError, OSError):
            if self._retries > 0:
                self._retries -= 1
                _LOGGER.error("Could not connect to Prismatik at %s:%s", self._host, self._port)
            await self.disconnect()
        else:
            # check header
            data = await self._tcpreader.readline()
            header = data.decode().strip()
            _LOGGER.debug("GOT HEADER: %s", header)
            if not header.startswith(str(PrismatikAPI.AWR_HEADER)):
                _LOGGER.error("Bad API header")
                await self.disconnect()
        return self._tcpwriter is not None

    async def disconnect(self) -> None:
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

    async def _send(self, buffer: str) -> Optional[str]:
        """Send command to Prismatik server."""
        if self._tcpwriter is None and (await self._connect()) is False:
            return None

        _LOGGER.debug("SENDING: [%s]", buffer.strip())
        try:
            self._tcpwriter.write(buffer.encode())
            await self._tcpwriter.drain()
            await asyncio.sleep(0.01)
            data = await self._tcpreader.readline()
            answer = data.decode().strip()
        except OSError:
            if self._retries > 0:
                self._retries -= 1
                _LOGGER.error("Prismatik went away?")
            await self.disconnect()
            answer = None
        else:
            self._retries = CONNECTION_RETRY_ERRORS
            _LOGGER.debug("RECEIVED: [%s]", answer)
            if answer == PrismatikAPI.AWR_NOT_LOCKED:
                if await self._do_cmd(PrismatikAPI.CMD_LOCK):
                    return await self._send(buffer)
                _LOGGER.error("Could not lock Prismatik")
                answer = None
            if answer == PrismatikAPI.AWR_AUTH_REQ:
                if self._apikey and (await self._do_cmd(PrismatikAPI.CMD_APIKEY, self._apikey)):
                    self._api_connected = True
                    return await self._send(buffer)
                _LOGGER.error("Prismatik authentication failed, check API key")
                answer = None
            else:
                self._api_connected = True
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
                fr"^({PrismatikAPI.AWR_OK}|{cmd}:{PrismatikAPI.AWR_SUCCESS})$"
            ).match(answer or "")
            is not None
        )

    async def _set_rgb_color(self, rgb: Tuple[int,int,int]) -> bool:
        """Generate and execude setcolor command on Prismatik server."""
        leds = await self.leds()
        if leds == 0:
            return False
        rgb_color = ",".join(map(str, rgb))
        pixels = ";".join([f"{led}-{rgb_color}" for led in range(1, leds + 1)])
        return await self._set_cmd(PrismatikAPI.CMD_SET_COLOR, pixels)

    @property
    def is_reachable(self) -> bool:
        """network connection status"""
        return self._tcpwriter is not None

    @property
    def is_connected(self) -> bool:
        """network ok and API is talking successfully"""
        return self.is_reachable and self._api_connected

    @property
    def host(self) -> str:
        """Host"""
        return self._host

    @property
    def port(self) -> int:
        """Port"""
        return self._port

    async def leds(self) -> int:
        """Return the led count of the light."""
        countleds = await self._get_cmd(PrismatikAPI.CMD_GET_COUNTLEDS)
        return int(countleds) if countleds else 0

    async def is_on(self) -> bool:
        """ON/OFF Status."""
        return await self._get_cmd(PrismatikAPI.CMD_GET_STATUS) == PrismatikAPI.STS_ON

    async def turn_on(self) -> bool:
        """Turn ON."""
        return await self._set_cmd(PrismatikAPI.CMD_SET_STATUS, PrismatikAPI.STS_ON)

    async def turn_off(self) -> bool:
        """Turn OFF."""
        return await self._set_cmd(PrismatikAPI.CMD_SET_STATUS, PrismatikAPI.STS_OFF)

    async def set_brightness(self, brightness: int, profile: Optional[str]=None) -> bool:
        """Set brightness (0-100)."""
        if not await self._set_cmd(PrismatikAPI.CMD_SET_BRIGHTNESS, brightness):
            return False
        if not profile:
            return True
        on_unlock = PrismatikAPI.STS_OFF
        if (await self._get_cmd(PrismatikAPI.CMD_GET_PROFILE)) == profile:
            on_unlock = PrismatikAPI.STS_ON
        return await self._set_cmd(PrismatikAPI.CMD_SET_PERSIST_ON_UNLOCK, on_unlock)

    async def get_brightness(self) -> Optional[int]:
        """Get brightness (0-100)."""
        brightness = await self._get_cmd(PrismatikAPI.CMD_GET_BRIGHTNESS)
        return int(brightness) if brightness is not None else None

    async def set_color(self, rgb: Tuple[int, int, int], profile: Optional[str]=None) -> bool:
        """Set (R,G,B) to all LEDs"""
        if profile:
            if not await self._do_cmd(PrismatikAPI.CMD_NEW_PROFILE, profile):
                return False
            if not await self._set_cmd(PrismatikAPI.CMD_SET_PERSIST_ON_UNLOCK, PrismatikAPI.STS_ON):
                return False
        return await self._set_rgb_color(rgb)

    async def get_color(self) -> Optional[Tuple[int,int,int]]:
        """Get current (R,G,B) for the first LED"""
        pixels = await self._get_cmd(PrismatikAPI.CMD_GET_COLOR)
        rgb = re.match(r"^\d+-(\d+),(\d+),(\d+);", pixels or "")
        return (int(rgb.group(1)), int(rgb.group(2)), int(rgb.group(3))) if rgb else None

    async def unlock(self) -> bool:
        """Unlock API"""
        return await self._do_cmd(PrismatikAPI.CMD_UNLOCK)

    async def lock(self) -> bool:
        """Lock API"""
        return await self._do_cmd(PrismatikAPI.CMD_LOCK)

    async def get_profiles(self) -> Optional[List]:
        """Get profile list"""
        profiles = await self._get_cmd(PrismatikAPI.CMD_GET_PROFILES)
        return list(filter(None, profiles.split(";"))) if profiles else None

    async def get_profile(self) -> Optional[str]:
        """Get current profile name"""
        return await self._get_cmd(PrismatikAPI.CMD_GET_PROFILE)

    async def set_profile(self, profile: str) -> bool:
        """Set current profile name"""
        if not await self._set_cmd(PrismatikAPI.CMD_SET_PERSIST_ON_UNLOCK, PrismatikAPI.STS_OFF):
            return False
        return await self._set_cmd(PrismatikAPI.CMD_SET_PROFILE, profile)
