<img src="https://techjobsforgood-prod.s3.amazonaws.com/company_profile_photos/e8364d92-4faa-496e-a630-39bf3a751894-20220923-214424.jpg" >

# Tomorrow.io Plugin for Indigo Domotics Home Automation
## tomorrowio-indigo-plugin for Python3.11
This Indigo Plugin provides a way to connect Indigo to your Life360.com family tracking information. This plugin is only supported for [Indigo Domotics Software ](http://www.indigodomo.com)

[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](http://mit-license.org)
[![Platform](https://img.shields.io/badge/Platform-Indigo-blueviolet)](https://www.indigodomo.com/) 
[![Language](https://img.shields.io/badge/Language-python%203.10-orange)](https://www.python.org/)
[![Requirements](https://img.shields.io/badge/Requirements-Indigo%20v2022.1%2B-green)](https://www.indigodomo.com/downloads.html)
![Releases](https://img.shields.io/github/release-date/ryanbuckner/tomorrowio-plugin?color=red&label=latest%20release)

###### Current Weather
Circles allows users to create separate groups within the app, e.g. "caregivers," "extended family," and "John's baseball team." Users' location is only visible to those who are also in the circle, and members in "caregivers" cannot see the location of users in "extended family," unless they are also in that circle.

###### Forecast
Places are a great way to know when your loved ones are leaving work or just arrived at school. Places are areas you can define so you are alerted when a Circle member enters or leaves a location. Some Places you might want to set up are work, home, and school. Free plans can set up two Places. To set up more Places, upgrade to a Premium plan.

### The Plugin

The plugin is new and supports current and forecasted weather. It's modeled after the built in NOAA Weather plugin

This plugin is not endorsed or associated with Tomorrow.io 

#### Installation

Download the Tomorrowio.indigoPlugin file and double click it

###### Plugin Config 
- configure the Plugin by entering:
  - Your tomorrow.io API key. You can get this free on their website
  - Preferred unit of measurement

###### Device Config 
- create a new device of Type Tomorrow.io Weather
  - Choose from the dropdown if you want current weather or forecasted 
  - Set your location
    - Address or Place Name if you want to use your address or city
    - LatLong if you want to use your lat and long. The indigo server settings will be used by default 
  

