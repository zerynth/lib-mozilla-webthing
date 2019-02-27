#############################################
# Simple_Thing
# Created at 2018-12-01 23:59:48.293498
#############################################

import streams
import json
import requests
from espressif.esp32net import esp32wifi as wifi_driver  # Esp32 Wifi driver
from wireless import wifi
import mcu
import threading

# Mozilla WebThing library
from mozilla.webthing import webthing


# Wifi SSID and password
SSID = "YourSSID"
PASSWORD = "YourPassword"


def setup_wifi():
    '''
    Init wifi driver and connect to the network using ssid and password
    provided in the `config` module.
    '''
    wifi_driver.auto_init()
    print("Establishing link to %s" % SSID)
    try:
        wifi.link(SSID, wifi.WIFI_WPA2, PASSWORD)
    except Exception as e:
        print("Error connecting to Wi-Fi")
        print(e)
        sleep(5000)
        mcu.reset()  # reboot device so it can retry
    print("Connected")


def get_timestamp_from_the_web():
    '''
    Fetch and return current timestamp from a web service.
    '''
    try:
        time_data = requests.get('http://now.zerynth.com').json()
        return time_data['now']['iso8601']
    except Exception as e:
        print("Error while obtaining current time")
        print(e)


streams.serial()  # init serial connection for print
setup_wifi()      # connect to Wi-Fi

# Init a Thing
xinabox_thing = webthing.Thing(
    "xinabox",
    "Xinabox ESP32",
    description="My really cool Xinabox ESP32",
    timestamp_fn=get_timestamp_from_the_web
)

# Register available EVENTS
xinabox_thing.register_event("led_change", "LED changed status")

# Register available PROPERTIES
# for this example a LED can change its status (on or off)
pinMode(LED0, OUTPUT_PUSHPULL)
digitalWrite(LED0, HIGH)
_led_status = True                  # we'll remember the LED status here


def get_led(payload=None):
    '''
    Return a boolean indicating if the led is currently on or not.
    '''
    res = _led_status
    return res


def set_led(status):
    '''
    Set the LED to a new status indicated in payload["led"].
    '''
    global _led_status
    digitalWrite(LED0, HIGH if status else LOW)
    _led_status = status
    xinabox_thing.signal_event('led_change', inp_data={"new_status": status})
    return status


xinabox_thing.add_property(
    "led",
    "LED",
    "boolean",
    get_led,         # This function is called on GET requests
    setter=set_led,  # This function is called on PUT requests
    description="A LED which can be turned ON or OFF"
)

# Register available ACTIONS
xinabox_thing.add_action(
    "led",
    "LED",
    callback=get_led,
    description="A LED which can be turned ON or OFF"
)

# Start the webserver exposing this Thing via HTTP requests
webthing.run_server(xinabox_thing)
