**Prismatik**

uncheck `Listen only on local interface`

**HA server**
```
cd /hass/config/custom_components
git clone --branch master --depth 1 https://github.com/zomfg/home-assistant-prismatik.git prismatik
```
or manually download to `/hass/config/custom_components` and rename `home-assistant-prismatik` to `prismatik`

**HA config**
```yaml
light:
  - platform: prismatik
    host: 192.168.42.42

    # optional
    port: 3636

    # optional
    name: "Prismatik"

    # optional
    api_key: '{API_KEY}'

    # optional: profile name to use so other profiles don't get altered
    profile_name: hass
```

tested on HA 0.105.4 and Prismatik [5.2.11.21](https://github.com/psieg/Lightpack/releases/tag/5.11.2.21)
