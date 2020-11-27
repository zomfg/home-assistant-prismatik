<p align="center">
  <img src="https://raw.githubusercontent.com/zomfg/Lightpack/749b592dd033cc96240a75f16d85f170640fab50/Software/res/icons/Prismatik.png" width="80" />
  &nbsp;
  &nbsp;
  &nbsp;
  <img src="https://raw.githubusercontent.com/home-assistant/assets/1e19f0dca208f0876b274c68345fcf989de7377a/logo/logo-pretty.svg" width="80" />
</p>

<p align="center">
  <img src="https://github.com/zomfg/home-assistant-prismatik/workflows/Latest%20HA/badge.svg?branch=master&event=schedule" />
  <a href="https://github.com/custom-components/hacs"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" /></a>
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

or add the repo to HACS and install from there

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

Initially tested on HA 0.105.4 and Prismatik [5.2.11.21](https://github.com/psieg/Lightpack/releases/tag/5.11.2.21)
