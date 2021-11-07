"""
Prismatik integration.
https://github.com/psieg/Lightpack
"""
import asyncio
from homeassistant.config_entries import SOURCE_IMPORT
from .const import DOMAIN

async def async_setup(hass, config):
    """Set up the Prismatik integration."""
    conf = config.get(DOMAIN)
    if conf is not None:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
            )
        )

    return True



async def async_setup_entry(hass, entry):
    """Set up Prismatik platform."""
    config = {}
    for key, value in entry.data.items():
        config[key] = value
    for key, value in entry.options.items():
        config[key] = value
    if entry.options:
        hass.config_entries.async_update_entry(entry, data=config, options={})

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = config
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "light")
    )

    return True
