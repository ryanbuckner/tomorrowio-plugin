"""
Tomorrow.io Weather Plugin for Indigo Domotics
https://www.tomorrow.io

Author: Ryan Buckner
Date: 4/7/2026

Provides current conditions and daily forecast data using the Tomorrow.io
v4 Weather API. Requires a free Tomorrow.io API key.

Attribution: Weather data and icons provided by Tomorrow.io.
If you display Tomorrow.io weather icons in a control page, you must include
a "Powered by Tomorrow.io" attribution per their terms of service.
See: https://www.tomorrow.io/weather-api/
"""

################################################################################
# Imports
################################################################################
import datetime as dt
import json
import logging
import sys
import indigo
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
import pytz
from timezonefinder import TimezoneFinder
import ephem

try:
    import indigo
    import requests
    from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
    import pytz
    from timezonefinder import TimezoneFinder
    import ephem
except ImportError:
    indigo.server.log("There are required libraries than were not installed")
    pass

################################################################################
# Globals
################################################################################
REALTIME_URL = "https://api.tomorrow.io/v4/weather/realtime"
FORECAST_URL = "https://api.tomorrow.io/v4/weather/forecast"

# Mapping of tomorrow.io weatherCode values to human-readable descriptions.
# Source: https://docs.tomorrow.io/reference/weather-data-layers (Weather Codes)
WEATHER_CODES = {
    1000: "Clear",
    1001: "Cloudy",
    1100: "Mostly Clear",
    1101: "Partly Cloudy",
    1102: "Mostly Cloudy",
    2000: "Fog",
    2100: "Light Fog",
    3000: "Light Wind",
    3001: "Wind",
    3002: "Strong Wind",
    4000: "Drizzle",
    4001: "Rain",
    4200: "Light Rain",
    4201: "Heavy Rain",
    5000: "Snow",
    5001: "Flurries",
    5100: "Light Snow",
    5101: "Heavy Snow",
    6000: "Freezing Drizzle",
    6001: "Freezing Rain",
    6200: "Light Freezing Rain",
    6201: "Heavy Freezing Rain",
    7000: "Ice Pellets",
    7101: "Heavy Ice Pellets",
    7102: "Light Ice Pellets",
    8000: "Thunderstorm",
}

# Unit labels per API units setting
UNIT_LABELS = {
    "imperial": {
        "temperature": "F",
        "wind":        "mph",
        "pressure":    "inHg",
        "visibility":  "mi",
        "cloudBase":   "mi",
        "precip":      "in/hr",
    },
    "metric": {
        "temperature": "C",
        "wind":        "m/s",
        "pressure":    "hPa",
        "visibility":  "km",
        "cloudBase":   "km",
        "precip":      "mm/hr",
    }
}

TZ_FULL_NAMES = {
    "EDT": "Eastern Daylight Time",
    "EST": "Eastern Standard Time",
    "CDT": "Central Daylight Time",
    "CST": "Central Standard Time",
    "MDT": "Mountain Daylight Time",
    "MST": "Mountain Standard Time",
    "PDT": "Pacific Daylight Time",
    "PST": "Pacific Standard Time",
    "AKDT": "Alaska Daylight Time",
    "AKST": "Alaska Standard Time",
    "HST": "Hawaii Standard Time",
    "UTC": "Coordinated Universal Time",
}

################################################################################
class Plugin(indigo.PluginBase):
    """Tomorrow.io Weather Plugin"""

    ########################################
    def __init__(self, plugin_id, plugin_display_name, plugin_version, plugin_prefs):
        super().__init__(plugin_id, plugin_display_name, plugin_version, plugin_prefs)

        log_format = '%(asctime)s.%(msecs)03d\t%(levelname)-10s\t%(name)s.%(funcName)-28s %(message)s'
        self.plugin_file_handler.setFormatter(logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S'))
        self.debug = plugin_prefs.get("showDebugInfo", False)
        self.hide_msgs = plugin_prefs.get("hideLogMessages", False)
        self.device_list = []
        self.changing_managed_devices = False
        self.update_interval = int(plugin_prefs.get("updateInterval", 30))

        self.logger.info(u"")
        self.logger.info(u"{0:=^130}".format("Starting Tomorrow.io Plugin Engine"))
        self.logger.info(u"{0:<30} {1}".format("Plugin name:", plugin_display_name))
        self.logger.info(u"{0:<30} {1}".format("Plugin version:", plugin_version))
        self.logger.info(u"{0:<30} {1}".format("Plugin ID:", plugin_id))
        self.logger.info(u"{0:<30} {1}".format("Refresh Frequency:", str(self.update_interval) + " minutes"))
        self.logger.info(u"{0:<30} {1}".format("Indigo version:", indigo.server.version))
        self.logger.info(u"{0:<30} {1}".format("Python version:", sys.version.replace('\n', '')))
        self.logger.info(u"{0:=^130}".format(""))

    ########################################
    def closed_prefs_config_ui(self, values_dict=None, user_cancelled=False):
        if not user_cancelled:
            if values_dict.get('showDebugInfo') != self.debug:
                self.logger.info(f"Setting debug level to {values_dict['showDebugInfo']}")
                self.debug = values_dict.get("showDebugInfo", False)

            if values_dict.get('hideLogMessages') != self.hide_msgs:
                self.hide_msgs = values_dict['hideLogMessages']

            if values_dict.get('updateInterval') != str(self.update_interval):
                self.update_interval = int(values_dict.get('updateInterval', 30))    

            for dev in indigo.devices.iter("self"):
                old_props = dev.pluginProps
                old_props.update({key: values_dict[key] for key in values_dict})
                dev.replacePluginPropsOnServer(old_props)
                if dev.enabled:
                    self.update(dev, force_update=True)

            self.logger.info(u"Plugin references have been updated")

    ########################################
    def device_start_comm(self, device):
        try:
            self.logger.debug(f"Starting device: {device.name}")
            device.stateListOrDisplayStateIdChanged()
            device.updateStateImageOnServer(indigo.kStateImageSel.NoImage)

            if device.id not in self.device_list:
                self.logger.debug(f"Adding device to device list: {device.name}")
                self.update(device, force_update=False)
                self.device_list.append(device.id)

                if device.deviceTypeId == 'current' or device.deviceTypeId == "forecast":
                    device.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)

        except requests.exceptions.ConnectionError:
            self.logger.warning(f"{device.name}: Unable to connect to Tomorrow.io. Will continue to try.")

    ########################################
    def device_stop_comm(self, device):
        self.logger.debug(f"Stopping device: {device.name}")
        if device.id in self.device_list:
            self.changing_managed_devices = True
            self.device_list.remove(device.id)
            self.changing_managed_devices = False

    ########################################
    @staticmethod
    def get_device_config_ui_values(plugin_props, type_id, dev_id):
        dev = indigo.devices[dev_id]
        if not dev.configured and type_id in ('current', 'forecast'):
            lat_long = indigo.server.getLatitudeAndLongitude()
            plugin_props['latitude'] = lat_long[0]
            plugin_props['longitude'] = lat_long[1]
        return plugin_props

    ########################################
    def validate_device_config_ui(self, values_dict, type_id, dev_id):
        error_msg_dict = indigo.Dict()

        if values_dict.get('locationType', 'latlong') == 'latlong':
            for item in ('latitude', 'longitude'):
                value = values_dict.get(item)

                if value is None or not str(value).strip():
                    error_msg_dict[item] = f"The {item} value cannot be empty."
        else:
            value = values_dict.get('address')

            if value is None or not str(value).strip():
                error_msg_dict['address'] = "Address cannot be empty."

        if len(error_msg_dict) > 0:
            return False, values_dict, error_msg_dict

        # Test the API key and location by making a quick realtime request
        api_key = self.plugin_prefs.get('apiKey', '').strip()
        if not api_key:
            error_msg_dict['address'] = "No API key configured. Set your Tomorrow.io API key in plugin config."
            return False, values_dict, error_msg_dict

        location = self._get_location_string(values_dict)
        units = self.plugin_prefs.get('units', 'imperial')
        url = REALTIME_URL
        params = {'location': location, 'apikey': api_key, 'units': units}

        try:
            reply = requests.get(url, params=params, timeout=10)
            if reply.status_code not in range(200, 300):
                self.logger.error(f"Tomorrow.io API test failed: {reply.status_code} - {reply.text}")
                error_msg_dict['address'] = f"Could not connect to Tomorrow.io ({reply.status_code}). Check location and API key."
                return False, values_dict, error_msg_dict
        except Timeout:
            error_msg_dict['address'] = "Tomorrow.io did not respond in time. Try again."
            return False, values_dict, error_msg_dict
        except Exception as err:
            self.logger.error(f"Validation error: {err}")
            error_msg_dict['address'] = "Unknown error validating location. Check plugin log."
            return False, values_dict, error_msg_dict

        return True, values_dict

    ########################################
    def run_concurrent_thread(self):
        self.logger.debug("Starting concurrent thread")
        try:
            while True:
                # Sleep first -- devices are updated on start via device_start_comm
                self.sleep(self.update_interval * 60)
                self.logger.debug("Starting device update cycle...")
                while self.changing_managed_devices:
                    self.sleep(2)
                for device_id in self.device_list:
                    self.update(indigo.devices[device_id], force_update=False)
        except self.StopThread:
            pass

    ########################################
    # UI / Config helpers
    ########################################
    def validate_prefs_config_ui(self, values_dict):
        error_msg_dict = indigo.Dict()
        if not values_dict.get('apiKey', '').strip():
            error_msg_dict['apiKey'] = "API key is required."
        try:
            interval = int(values_dict.get('updateInterval', 30))
            if interval < 5 or interval > 1440:
                error_msg_dict['updateInterval'] = "Update interval must be between 5 and 1440 minutes."
        except (TypeError, ValueError):
            error_msg_dict['updateInterval'] = "Update interval must be a whole number."

        if len(error_msg_dict) > 0:
            return False, values_dict, error_msg_dict

        return True, values_dict

    ########################################
    # Core update dispatcher
    ########################################
    def update(self, device, force_update=False):
        self.logger.debug(f"Update device type: {device.deviceTypeId}")
        match device.deviceTypeId:
            case 'current':
                self.update_current_device(device, force_update)
            case 'forecast':
                self.update_forecast_device(device, force_update)
            case _:
                self.logger.debug("Attempt to update an unknown device type.")

    ########################################
    # Current Conditions
    ########################################
    def update_current_device(self, device, force_update=False):
        self.logger.debug(f"Updating current conditions device: {device.name}")
        api_key = self.plugin_prefs.get('apiKey', '').strip()
        units = self.plugin_prefs.get('units', 'imperial')

        if not api_key:
            self.logger.error(f"{device.name}: No API key configured.")
            return

        location = self._get_location_string(device.pluginProps)
        params = {'location': location, 'apikey': api_key, 'units': units}

        try:
            reply = requests.get(REALTIME_URL, params=params, timeout=10)
            if reply.status_code not in range(200, 300):
                self.logger.warning(
                    f"{device.name}: Tomorrow.io returned status {reply.status_code}. Will retry on next cycle."
                )
                self.logger.debug(f"Response body: {reply.text}")
                return

            data = reply.json()
            self.logger.debug(f"Realtime API response: {data}")

            values = data['data']['values']
            obs_time_raw = data['data']['time']
            lat = data['location']['lat']
            lon = data['location']['lon']
            tz_name, tz_abbrev = self.get_timezone_info(lat, lon)
            season = self.get_season(lat)

            obs_time = self._parse_iso_time(obs_time_raw)

            if obs_time == device.states.get('observationTime') and not force_update:
                self.logger.debug(f"{device.name}: No new data since {obs_time}, skipping.")
                return

            self._log_data_change(device.name, obs_time)

            weather_code = values.get('weatherCode', 0)
            weather_desc = WEATHER_CODES.get(weather_code, f"Code {weather_code}")
            unit_labels = UNIT_LABELS[units]
            temp = values.get('temperature')
            temp_apparent = values.get('temperatureApparent')
            temp_unit = unit_labels['temperature']

            # Build temperature display string
            if temp is not None:
                temp_str = f"{round(temp, 1)} {temp_unit}"
            else:
                temp_str = "- data unavailable -"

            wind_speed = values.get('windSpeed')
            wind_gust = values.get('windGust')
            wind_deg = values.get('windDirection')
            wind_dir_str = self.wind_dir_string(wind_deg) if wind_deg is not None else "- data unavailable -"
            wind_unit = unit_labels['wind']


            if wind_speed is not None and wind_dir_str != "- data unavailable -":
                wind_str = f"{wind_dir_str} at {round(wind_speed, 1)} {wind_unit}"
                if wind_gust is not None:
                    wind_str += f" (gusts {round(wind_gust, 1)} {wind_unit})"
            else:
                wind_str = "- data unavailable -"

            dew_point = values.get('dewPoint')
            if dew_point is not None:
                dew_str = f"{round(dew_point, 1)} {temp_unit}"
            else:
                dew_str = "- data unavailable -"

            key_value_list = [
                {'key': 'observationTime',         'value': obs_time},
                {'key': 'weatherCode',             'value': weather_code},
                {'key': 'weatherDescription',      'value': weather_desc},
                {'key': 'temperature',             'value': self._safe_round(temp, 1),          'decimalPlaces': 1},
                {'key': 'temperatureApparent',     'value': self._safe_round(temp_apparent, 1), 'decimalPlaces': 1},
                {'key': 'temperatureString',       'value': temp_str},
                {'key': 'humidity',                'value': self._safe_int(values.get('humidity'))},
                {'key': 'dewPoint',                'value': self._safe_round(dew_point, 1),      'decimalPlaces': 1},
                {'key': 'dewPointString',          'value': dew_str},
                {'key': 'windSpeed',               'value': self._safe_round(wind_speed, 1), 'decimalPlaces': 1},
                {'key': 'windGust',                'value': self._safe_round(wind_gust, 1),  'decimalPlaces': 1},
                {'key': 'windDirection',           'value': wind_dir_str},
                {'key': 'windDegrees',             'value': self._safe_round(wind_deg, 1)},
                {'key': 'windString',              'value': wind_str},
                {'key': 'pressureSeaLevel',        'value': self._safe_round(values.get('pressureSeaLevel'), 2)},
                {'key': 'pressureSurfaceLevel',    'value': self._safe_round(values.get('pressureSurfaceLevel'), 2)},
                {'key': 'altimeterSetting',        'value': self._safe_round(values.get('altimeterSetting'), 2)},
                {'key': 'visibility',              'value': self._safe_round(values.get('visibility'), 1), 'decimalPlaces': 1},
                {'key': 'cloudBase',               'value': self._safe_round(values.get('cloudBase'), 2),    'decimalPlaces': 2},
                {'key': 'cloudCeiling',            'value': self._safe_round(values.get('cloudCeiling'), 2), 'decimalPlaces': 2},
                {'key': 'cloudCover',              'value': self._safe_round(values.get('cloudCover'), 1)},
                {'key': 'uvIndex',                 'value': self._safe_int(values.get('uvIndex'))},
                {'key': 'uvHealthConcern',         'value': self._safe_int(values.get('uvHealthConcern'))},
                {'key': 'precipitationProbability','value': self._safe_int(values.get('precipitationProbability'))},
                {'key': 'rainIntensity',           'value': self._safe_round(values.get('rainIntensity'), 3)},
                {'key': 'snowIntensity',           'value': self._safe_round(values.get('snowIntensity'), 3)},
                {'key': 'sleetIntensity',          'value': self._safe_round(values.get('sleetIntensity'), 3)},
                {'key': 'freezingRainIntensity',   'value': self._safe_round(values.get('freezingRainIntensity'), 3)},
                {'key': 'latitude',                'value': round(float(lat), 4)},
                {'key': 'longitude',               'value': round(float(lon), 4)},
                {'key': 'units',                   'value': units},
                {'key': 'timeZoneName',            'value': tz_name},
                {'key': 'timeZone',                'value': tz_abbrev},
                {'key': 'season',                  'value': season},
            ]

            device.updateStatesOnServer(key_value_list)

            # Update address field to show resolved location
            new_props = device.pluginProps
            new_props['address'] = location
            device.replacePluginPropsOnServer(new_props)

        except Timeout:
            self.logger.warning(f"{device.name}: Tomorrow.io did not respond in time. Will retry on next cycle.")
        except ConnectionError:
            self.logger.warning(f"{device.name}: Unable to connect to Tomorrow.io. Will retry on next cycle.")
        except (KeyError, ValueError, json.JSONDecodeError) as err:
            self.logger.error(f"{device.name}: Error parsing API response: {err}")
            self.logger.debug("Exception detail:", exc_info=True)
        except Exception:
            self.logger.error(f"{device.name}: Unexpected error. Check plugin log.")
            self.logger.debug("Exception detail:", exc_info=True)

    ########################################
    # Forecast
    ########################################
    def update_forecast_device(self, device, force_update=False):
        self.logger.debug(f"Updating forecast device: {device.name}")
        api_key = self.plugin_prefs.get('apiKey', '').strip()
        units = self.plugin_prefs.get('units', 'imperial')

        if not api_key:
            self.logger.error(f"{device.name}: No API key configured.")
            return

        location = self._get_location_string(device.pluginProps)
        params = {'location': location, 'apikey': api_key, 'units': units}

        try:
            reply = requests.get(FORECAST_URL, params=params, timeout=10)
            if reply.status_code not in range(200, 300):
                self.logger.warning(
                    f"{device.name}: Tomorrow.io returned status {reply.status_code}. Will retry on next cycle."
                )
                self.logger.debug(f"Response body: {reply.text}")
                return

            data = reply.json()
            self.logger.debug(f"Forecast API response keys: {list(data.get('timelines', {}).keys())}")

            daily_list = data['timelines']['daily']
            state_list = []

            now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            state_list.append({'key': 'observationTime', 'value': now_str})

            # tomorrow.io returns up to 6 daily periods
            for idx in range(1, 7):
                day_num = idx
                day_key = f"day{day_num}"
                try:
                    day = daily_list[idx - 1]
                except IndexError:
                    # Fewer days available than expected -- clear remaining states
                    for field in ('date', 'weatherCode', 'weatherDescription', 'temperatureMax', 'temperatureMin',
                                  'temperatureAvg', 'precipitationProbabilityMax', 'windSpeedAvg', 'windGustMax',
                                  'humidityAvg', 'uvIndexMax', 'sunriseTime', 'sunsetTime', 'moonriseTime',
                                  'moonsetTime', 'cloudCoverAvg', 'visibilityAvg'):
                        state_list.append({'key': f"{day_key}_{field}", 'value': ""})
                    continue

                v = day['values']
                day_date = self._parse_iso_date(day['time'])
                weather_code = v.get('weatherCodeMax', 0) or v.get('weatherCodeAvg', 0)
                weather_desc = WEATHER_CODES.get(weather_code, f"Code {weather_code}")


                state_list.extend([
                    {'key': f"{day_key}_date",                        'value': day_date},
                    {'key': f"{day_key}_weatherCode",                 'value': self._safe_int(weather_code)},
                    {'key': f"{day_key}_weatherDescription",          'value': weather_desc},
                    {'key': f"{day_key}_temperatureMax",              'value': self._safe_round(v.get('temperatureMax'), 1), 'decimalPlaces': 1},
                    {'key': f"{day_key}_temperatureMin",              'value': self._safe_round(v.get('temperatureMin'), 1), 'decimalPlaces': 1},
                    {'key': f"{day_key}_temperatureAvg",              'value': self._safe_round(v.get('temperatureAvg'), 1), 'decimalPlaces': 1},
                    {'key': f"{day_key}_precipitationProbabilityMax", 'value': self._safe_int(v.get('precipitationProbabilityMax'))},
                    {'key': f"{day_key}_windSpeedAvg",                'value': self._safe_round(v.get('windSpeedAvg'), 1), 'decimalPlaces': 1},
                    {'key': f"{day_key}_windGustMax",                 'value': self._safe_round(v.get('windGustMax'), 1),  'decimalPlaces': 1},
                    {'key': f"{day_key}_humidityAvg",                 'value': self._safe_int(v.get('humidityAvg'))},
                    {'key': f"{day_key}_uvIndexMax",                  'value': self._safe_int(v.get('uvIndexMax'))},
                    {'key': f"{day_key}_sunriseTime",                 'value': self._parse_iso_time(v.get('sunriseTime', ''))},
                    {'key': f"{day_key}_sunsetTime",                  'value': self._parse_iso_time(v.get('sunsetTime', ''))},
                    {'key': f"{day_key}_moonriseTime",                'value': self._parse_iso_time(v.get('moonriseTime', ''))},
                    {'key': f"{day_key}_moonsetTime",                 'value': self._parse_iso_time(v.get('moonsetTime', ''))},
                    {'key': f"{day_key}_cloudCoverAvg",               'value': self._safe_round(v.get('cloudCoverAvg'), 1)},
                    {'key': f"{day_key}_visibilityAvg",               'value': self._safe_round(v.get('visibilityAvg'), 1), 'decimalPlaces': 1},
                ])

            device.updateStatesOnServer(state_list)
            self._log_data_change(device.name, now_str)

            new_props = device.pluginProps
            new_props['address'] = location
            device.replacePluginPropsOnServer(new_props)

        except Timeout:
            self.logger.warning(f"{device.name}: Tomorrow.io did not respond in time. Will retry on next cycle.")
        except ConnectionError:
            self.logger.warning(f"{device.name}: Unable to connect to Tomorrow.io. Will retry on next cycle.")
        except (KeyError, ValueError, json.JSONDecodeError) as err:
            self.logger.error(f"{device.name}: Error parsing API response: {err}")
            self.logger.debug("Exception detail:", exc_info=True)
        except Exception:
            self.logger.error(f"{device.name}: Unexpected error. Check plugin log.")
            self.logger.debug("Exception detail:", exc_info=True)

    ########################################
    # Helpers
    ########################################
    @staticmethod
    def get_season(lat, d=None):
        """Return astronomical season name based on equinox/solstice dates."""
        if d is None:
            d = dt.date.today()
        year = d.year
        spring = ephem.next_vernal_equinox(str(year)).datetime().date()
        summer = ephem.next_summer_solstice(str(year)).datetime().date()
        fall   = ephem.next_autumnal_equinox(str(year)).datetime().date()
        winter = ephem.next_winter_solstice(str(year)).datetime().date()

        if d < spring:     nh = "Winter"
        elif d < summer:   nh = "Spring"
        elif d < fall:     nh = "Summer"
        elif d < winter:   nh = "Fall"
        else:              nh = "Winter"

        if float(lat) < 0:
            nh = {"Winter": "Summer", "Summer": "Winter", "Spring": "Fall", "Fall": "Spring"}[nh]
        return nh

    @staticmethod
    def get_timezone_info(lat, lon):
        try:
            tf = TimezoneFinder()
            tz_str = tf.timezone_at(lat=float(lat), lng=float(lon))
            if not tz_str:
                return "- data unavailable -", "- data unavailable -"
            tz = pytz.timezone(tz_str)
            now = dt.datetime.now(tz)
            tz_abbrev = now.strftime("%Z")
            tz_name = TZ_FULL_NAMES.get(tz_abbrev, tz_abbrev)
            return tz_name, tz_abbrev
        except Exception:
            return "- data unavailable -", "- data unavailable -"

    @staticmethod
    def _get_location_string(props):
        """Return a location string suitable for the tomorrow.io API from device props."""
        loc_type = props.get('locationType', 'latlong')
        if loc_type == 'address':
            return props.get('address', '').strip()
        else:
            lat = str(props.get('latitude', '')).strip()
            lon = str(props.get('longitude', '')).strip()
            return f"{lat},{lon}"

    @staticmethod
    def _parse_iso_time(iso_str):
        """Convert ISO 8601 UTC timestamp to local time string YYYY-MM-DD HH:MM:SS."""
        if not iso_str:
            return ""
        try:
            # Handle both Z suffix and +00:00 suffix
            iso_str = iso_str.replace('Z', '+00:00')
            utc = dt.datetime.fromisoformat(iso_str)
            local = utc.replace(tzinfo=dt.timezone.utc).astimezone(tz=None)
            return dt.datetime.strftime(local, "%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            return iso_str

    @staticmethod
    def _parse_iso_date(iso_str):
        """Return just the date portion YYYY-MM-DD from an ISO timestamp."""
        if not iso_str:
            return ""
        try:
            iso_str = iso_str.replace('Z', '+00:00')
            utc = dt.datetime.fromisoformat(iso_str)
            local = utc.replace(tzinfo=dt.timezone.utc).astimezone(tz=None)
            return dt.datetime.strftime(local, "%Y-%m-%d")
        except (ValueError, AttributeError):
            return iso_str[:10] if len(iso_str) >= 10 else iso_str

    @staticmethod
    def _safe_round(value, decimals=1):
        """Round a value safely, returning '- data unavailable -' for None."""
        if value is None:
            return "- data unavailable -"
        try:
            return round(float(value), decimals)
        except (TypeError, ValueError):
            return "- data unavailable -"

    @staticmethod
    def _safe_int(value):
        """Convert a value to int safely, returning '- data unavailable -' for None."""
        if value is None:
            return "- data unavailable -"
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return "- data unavailable -"

    @staticmethod
    def wind_dir_string(degrees):
        """Convert wind direction degrees to a cardinal direction string."""
        if degrees is None:
            return "- data unavailable -"
        try:
            degrees = float(degrees)
        except (TypeError, ValueError):
            return "- data unavailable -"

        directions = [
            ("North",     (337.5, 360)),
            ("North",     (0,     22.5)),
            ("Northeast", (22.5,  67.5)),
            ("East",      (67.5,  112.5)),
            ("Southeast", (112.5, 157.5)),
            ("South",     (157.5, 202.5)),
            ("Southwest", (202.5, 247.5)),
            ("West",      (247.5, 292.5)),
            ("Northwest", (292.5, 337.5)),
        ]
        for name, (low, high) in directions:
            if low <= degrees < high:
                return name
        return "North"

    def _log_data_change(self, dev_name, obs_time):
        if not self.hide_msgs:
            self.logger.info(f"Received '{dev_name}' data updated at {obs_time}.")
        else:
            self.logger.debug(f"Received '{dev_name}' data updated at {obs_time}.")

    ########################################
    # Menu Methods
    ########################################
    def toggle_debugging(self):
        self.logger.info(f"Turning {'off' if self.debug else 'on'} debug logging")
        self.debug = not self.debug
        self.plugin_prefs['showDebugInfo'] = self.debug

    def refresh_data(self):
        for dev_id in self.device_list:
            self.update(indigo.devices[dev_id], force_update=True)
