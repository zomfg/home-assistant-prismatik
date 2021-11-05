"""Prismatik light."""
from typing import Any, Callable, Dict, List, Optional, Set

import homeassistant.helpers.config_validation as cv
import homeassistant.util.color as color_util
import voluptuous as vol
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_HS_COLOR,
    COLOR_MODE_HS,
    PLATFORM_SCHEMA,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_EFFECT,
    LightEntity,
)
from homeassistant.const import (
    ATTR_STATE,
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_PROFILE_NAME,
)
from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_ICON_OFF,
    DEFAULT_ICON_ON,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_PROFILE_NAME,
)

from .prismatik import PrismatikClient

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
    client = PrismatikClient(
            config[CONF_HOST],
            config[CONF_PORT],
            config.get(CONF_API_KEY)
        )
    light = PrismatikLight(hass, config[CONF_NAME], client, config.get(CONF_PROFILE_NAME))
    await light.async_update()

    async_add_entities([light])


class PrismatikLight(LightEntity):
    """Representation of Prismatik."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        client: PrismatikClient,
        profile: Optional[str]
    ) -> None:
        """Intialize."""
        self._hass = hass
        self._name = name
        self._client = client
        self._profile = profile

        host = self._client.host.replace(".", "_")
        self._unique_id = f"{host}_{self._client.port}"

        self._state = {
            ATTR_STATE : False,
            ATTR_EFFECT : None,
            ATTR_EFFECT_LIST : None,
            ATTR_BRIGHTNESS : None,
            ATTR_HS_COLOR : None,
        }

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect from update signal."""
        await self._client.disconnect()

    @property
    def hs_color(self) -> Optional[List]:
        """Return the hue and saturation color value [float, float]."""
        return self._state[ATTR_HS_COLOR]

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return self._name

    @property
    def available(self) -> bool:
        """Return availability of the light."""
        return self._client.is_connected

    @property
    def is_on(self) -> bool:
        """Return light status."""
        return self._state[ATTR_STATE]

    @property
    def icon(self) -> str:
        """Light icon."""
        return DEFAULT_ICON_ON if self.available else DEFAULT_ICON_OFF

    @property
    def unique_id(self) -> str:
        """Unique ID."""
        return self._unique_id

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light between 0..255."""
        return self._state[ATTR_BRIGHTNESS]

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_EFFECT

    @property
    def color_mode(self) -> Optional[str]:
        """Color mode."""
        return COLOR_MODE_HS

    @property
    def supported_color_modes(self) -> Optional[Set]:
        """Supported color modes."""
        return {COLOR_MODE_HS}

    @property
    def effect_list(self) -> Optional[List]:
        """Return profile list."""
        return self._state[ATTR_EFFECT_LIST]

    @property
    def effect(self) -> Optional[str]:
        """Return current profile."""
        return self._state[ATTR_EFFECT]

    async def async_update(self) -> None:
        """Update light state."""
        self._state[ATTR_STATE] = await self._client.is_on()

        self._state[ATTR_EFFECT] = await self._client.get_profile()
        self._state[ATTR_EFFECT_LIST] = await self._client.get_profiles()

        brightness = await self._client.get_brightness()
        self._state[ATTR_BRIGHTNESS] = round(brightness * 2.55) if brightness else None

        rgb = await self._client.get_color()
        self._state[ATTR_HS_COLOR] = color_util.color_RGB_to_hs(*rgb) if rgb else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._client.turn_on()
        if ATTR_EFFECT in kwargs:
            await self._client.set_profile(kwargs[ATTR_EFFECT])
        elif ATTR_BRIGHTNESS in kwargs:
            await self._client.set_brightness(round(kwargs[ATTR_BRIGHTNESS] / 2.55), self._profile)
        elif ATTR_HS_COLOR in kwargs:
            rgb = color_util.color_hs_to_RGB(*kwargs[ATTR_HS_COLOR])
            await self._client.set_color(rgb, self._profile)
        await self._client.unlock()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # pylint: disable=unused-argument
        await self._client.turn_off()
