<img src="https://www.tomorrow.io/wp-content/uploads/2022/01/tomorrow-logo.svg" width="200">

# Tomorrow.io Weather Plugin for Indigo Domotics Home Automation
## tomorrowio-plugin for Python 3.11
This Indigo Plugin connects [Indigo Domotics](http://www.indigodomo.com) to the [Tomorrow.io Weather API](https://www.tomorrow.io), providing current conditions and daily forecast data for any location worldwide.

[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](http://mit-license.org)
[![Platform](https://img.shields.io/badge/Platform-Indigo-blueviolet)](https://www.indigodomo.com/)
[![Language](https://img.shields.io/badge/Language-python%203.11-orange)](https://www.python.org/)
[![Requirements](https://img.shields.io/badge/Requirements-Indigo%20v2022.1%2B-green)](https://www.indigodomo.com/downloads.html)
![Releases](https://img.shields.io/github/release-date/ryanbuckner/tomorrowio-plugin?color=red&label=latest%20release)

### The Plugin

Modeled after the built-in NOAA Weather plugin, this plugin supports current conditions and 6-day daily forecasts using the Tomorrow.io v4 Weather API. A free Tomorrow.io API key is required.

This plugin is not endorsed by or affiliated with Tomorrow.io.

Weather data powered by [Tomorrow.io](https://www.tomorrow.io).

---

#### Installation

Download the `Tomorrow.io Weather.indigoPlugin` file and double-click it to install.

---

#### Plugin Config

Configure the plugin by entering:

- Your Tomorrow.io API key (available free at [tomorrow.io](https://www.tomorrow.io))
- Preferred unit of measurement (Imperial or Metric)
- Logging level
- Debug logging toggle

---

#### Device Types

Create a new device of Type **Tomorrow.io Weather** and choose one of two models:

**Current Conditions**
Uses the Tomorrow.io Realtime API. Provides up-to-the-minute current weather including temperature, feels-like, humidity, dew point, wind speed and direction, pressure, visibility, cloud cover, UV index, and precipitation intensity. Updates every 30 minutes.

**Weather Forecast**
Uses the Tomorrow.io Forecast API. Provides daily forecast data for up to 6 days including high/low/avg temperature, precipitation probability, wind, humidity, UV index, cloud cover, visibility, and sunrise/sunset/moonrise/moonset times.

---

#### Location Configuration

Both device types support two location methods:

- **Lat/Long** -- enter latitude and longitude directly. When creating a new device, these are pre-populated from the Indigo server location settings.
- **Address or Place Name** -- enter a city, address, or zip code (e.g. `Herndon, VA` or `20170`). Tomorrow.io resolves the location on their end.

---

#### Device States

Current Conditions states include:

`weatherCode`, `weatherDescription`, `temperature`, `temperatureApparent`, `temperatureString`, `humidity`, `dewPoint`, `dewPointString`, `windSpeed`, `windGust`, `windDirection`, `windDegrees`, `windString`, `pressureSeaLevel`, `pressureSurfaceLevel`, `altimeterSetting`, `visibility`, `cloudBase`, `cloudCeiling`, `cloudCover`, `uvIndex`, `uvHealthConcern`, `precipitationProbability`, `rainIntensity`, `snowIntensity`, `sleetIntensity`, `freezingRainIntensity`, `latitude`, `longitude`, `units`

Forecast states are prefixed `day1_` through `day6_` and include:

`date`, `weatherCode`, `weatherDescription`, `temperatureMax`, `temperatureMin`, `temperatureAvg`, `precipitationProbabilityMax`, `windSpeedAvg`, `windGustMax`, `humidityAvg`, `uvIndexMax`, `sunriseTime`, `sunsetTime`, `moonriseTime`, `moonsetTime`, `cloudCoverAvg`, `visibilityAvg`
