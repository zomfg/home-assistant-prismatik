<p align="center">
  <img src="https://github.com/zomfg/Lightpack/blob/master/Software/res/icons/Prismatik.png" width="80" />
  &nbsp;
  &nbsp;
  &nbsp;
  <img src="https://github.com/home-assistant/assets/blob/master/logo-pretty.png" width="80" />
</p>


**Prismatik**

uncheck `Listen only on local interface`

**HA server**
```sh
cd /hass/config/custom_components

# for the latest version
git clone --branch master --depth 1 https://github.com/zomfg/home-assistant-prismatik.git prismatik

# or for a specific HA version, see https://github.com/zomfg/home-assistant-prismatik/tags for available versions
git clone --branch ha-0.110 --depth 1 https://github.com/zomfg/home-assistant-prismatik.git prismatik
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
