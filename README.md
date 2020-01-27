**Prismatik**
uncheck `Listen only on local interface`

**HA server**
```
cd /hass/config/custom_components
git clone https://github.com/zomfg/home-assistant-prismatik.git prismatik
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

    # optional, tell Prismatik to keep colors until reset via restart/mode change...
    persist_on_unlock: false
```
